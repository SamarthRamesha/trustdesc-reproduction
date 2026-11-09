"""Native Apple inference and bounded worker lifecycle. Workers are NOT sandboxes.

Only our trusted model adapters run here. External tool code never enters them.
The parent enforces wall deadlines even if a native GPU call hangs.
"""
from __future__ import annotations
import gc
import multiprocessing as mp
from pathlib import Path
import re
import time
import traceback
from trustdesc.common.io import canonical, digest
from trustdesc.common.models import ModelError
from .model import json_object, model_file_manifest, check_asset, MODEL_FILE_PATTERNS


class MLXModel:
    mode = 'real_local_mlx_inference'

    def __init__(self, config, cache):
        import mlx.core as mx
        import mlx_lm
        from mlx_lm import load
        from huggingface_hub import snapshot_download, hf_hub_download
        from importlib.metadata import version
        if not re.fullmatch('[0-9a-f]{40}', config['revision']):
            raise ModelError('Full immutable model revision required')
        if not mx.metal.is_available():
            raise ModelError('MLX Metal unavailable; choose a validated CPU configuration')
        self.cfg, self.mx = config, mx
        self.model_id, self.audit = config['model_id'], []
        expected = model_file_manifest(self.model_id, config['revision'], cache)
        snapshot = Path(snapshot_download(self.model_id, revision=config['revision'], cache_dir=str(cache),
                        token=False, allow_patterns=MODEL_FILE_PATTERNS))
        assets = {}
        for path in sorted(snapshot.rglob('*')):
            if path.is_file():
                relative = path.relative_to(snapshot).as_posix()
                if relative not in expected:
                    raise ModelError('Unexpected model asset: '+relative)
                try:
                    assets[relative] = check_asset(path, expected[relative])
                except ModelError:
                    repaired = hf_hub_download(self.model_id, relative, revision=config['revision'],
                                              cache_dir=str(cache), token=False, force_download=True)
                    assets[relative] = check_asset(repaired, expected[relative])
                    assets[relative]['cache_repaired'] = True
        self.model, self.tokenizer = load(str(snapshot), tokenizer_config={'trust_remote_code':False})
        self.runtime = {'model_id':self.model_id,'revision':config['revision'],'device':'metal',
                        'backend':'mlx','mlx':version('mlx'),'mlx_lm':version('mlx-lm'),
                        'precision':'4-bit quantized weights; native activation dtype',
                        'quantization':self.model.args.quantization if hasattr(self.model.args,'quantization') else
                            __import__('json').loads((snapshot/'config.json').read_text()).get('quantization'),
                        'assets':assets,'paper_equivalence':False,'api_cost_usd':0.0,'compute_cost_usd':None}

    def complete(self, stage, system, payload):
        from mlx_lm import stream_generate
        from mlx_lm.sample_utils import make_sampler
        messages = [{'role':'system','content':system},{'role':'user','content':canonical(payload)}]
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        count = len(self.tokenizer.encode(prompt, add_special_tokens=False))
        record = {'stage':stage,'messages':messages,'request_hash':digest(messages),
                  'model':self.model_id,'revision':self.cfg['revision'],'input_tokens':count,
                  'cost_usd':0.0,'compute_cost_usd':None,'status':'started','backend':'mlx',
                  'temperature':self.cfg.get('temperature',0.0)}
        self.audit.append(record)
        start = time.perf_counter()
        chunks = []
        try:
            if count > self.cfg.get('max_input_tokens',8192):
                raise ModelError(f'Input has {count} tokens beyond configured cap; no truncation')
            seed = (self.cfg.get('seed',42)+int(digest(messages)[:8],16)) % (2**31)
            self.mx.random.seed(seed)
            record['seed'] = seed
            limit = self.cfg.get('max_new_tokens',2048)
            response = None
            stream = stream_generate(self.model,self.tokenizer,prompt=prompt,max_tokens=limit,
                                     sampler=make_sampler(temp=self.cfg.get('temperature',0.0)))
            try:
                for response in stream:
                    chunks.append(response.text)
                    if time.perf_counter()-start > self.cfg.get('max_generation_seconds',180):
                        raise ModelError('Generation deadline reached; partial response rejected')
            finally:
                stream.close()
            raw = ''.join(chunks)
            record.update(raw_content=raw,output_tokens=response.generation_tokens if response else 0)
            if response and response.finish_reason == 'length':
                raise ModelError('Output token limit reached; partial response rejected')
            result = json_object(raw)
            record.update(status='completed',response=result,peak_memory_bytes=self.mx.get_peak_memory())
            return result
        except Exception as exc:
            record.update(status='failed',raw_content=''.join(chunks),error_type=type(exc).__name__,
                          error=str(exc),traceback=traceback.format_exc())
            raise
        finally:
            record['seconds'] = time.perf_counter()-start
            self.mx.clear_cache()

    def close(self):
        self.model = self.tokenizer = None
        gc.collect()
        self.mx.clear_cache()


def _worker(pipe, config, cache):
    model = None
    try:
        if config.get('backend') == 'mlx':
            model = MLXModel(config, cache)
        else:
            from .model import LocalModel
            model = LocalModel(config, cache)
        pipe.send({'status':'ready','runtime':model.runtime,'mode':model.mode})
        while True:
            request = pipe.recv()
            if request is None:
                break
            before = len(model.audit)
            try:
                result = model.complete(*request)
                pipe.send({'status':'completed','response':result,'audit':model.audit[before:]})
            except Exception as exc:
                pipe.send({'status':'failed','error':str(exc),'error_type':type(exc).__name__,
                           'traceback':traceback.format_exc(),'audit':model.audit[before:]})
                if getattr(model,'fatal_error',False):
                    break
    except BaseException as exc:
        try:
            pipe.send({'status':'failed','error':str(exc),'error_type':type(exc).__name__,
                       'traceback':traceback.format_exc(),'audit':[]})
        except (BrokenPipeError, EOFError, OSError):
            pass
    finally:
        if model is not None:
            model.close()
        pipe.close()


class ManagedModel:
    """One resident model, hard deadlines, explicit shutdown, no semantic fallback."""
    def __init__(self, config, cache):
        from .startup import startup_smoke, launch_environment
        self.startup = startup_smoke(repeats=3,env=launch_environment())
        if not self.startup['passed']:
            raise ModelError('Basic Python startup failed; model worker launch blocked; no automatic retry')
        self.cfg, self.model_id, self.audit = config, config['model_id'], []
        self.peak_worker_rss_bytes=0
        ctx = mp.get_context('spawn')
        self.pipe, child = ctx.Pipe()
        self.process = ctx.Process(target=_worker,args=(child,config,str(cache)),daemon=True)
        self.process.start()
        child.close()
        try:
            result = self._receive(config.get('load_timeout_seconds',1200))
            self.runtime, self.mode = result['runtime'], result['mode']
        except BaseException:
            self.close()
            raise

    def _receive(self, timeout):
        import psutil
        deadline=time.monotonic()+timeout
        while not self.pipe.poll(.1):
            try:
                rss=psutil.Process(self.process.pid).memory_info().rss
                self.peak_worker_rss_bytes=max(self.peak_worker_rss_bytes,rss)
            except psutil.NoSuchProcess:
                rss=0
            if rss>self.cfg.get('max_worker_rss_bytes',5*1024**3):
                self.close()
                raise ModelError('Native inference RSS limit exceeded; worker terminated')
            if time.monotonic()>=deadline:
                self.close()
                raise ModelError('Native inference worker deadline exceeded; worker terminated')
        try:
            result = self.pipe.recv()
        except (EOFError, OSError) as exc:
            raise ModelError('Native worker exited; inspect process diagnostics') from exc
        self.audit.extend(result.get('audit',[]))
        for record in result.get('audit',[]):
            record['worker_peak_rss_bytes']=self.peak_worker_rss_bytes
        if result['status'] == 'failed':
            self.last_error = result
            raise ModelError(result.get('error_type','')+': '+result['error']+'\n'+result.get('traceback',''))
        return result

    def complete(self, stage, system, payload):
        if not self.process.is_alive():
            raise ModelError('Inference worker unavailable; restart model initialization')
        start = time.perf_counter()
        try:
            self.pipe.send((stage,system,payload))
            return self._receive(self.cfg.get('max_generation_seconds',180)+15)['response']
        except (BrokenPipeError, EOFError, OSError) as exc:
            raise ModelError('Inference worker communication failed') from exc
        except ModelError:
            if not self.process.is_alive():
                self.audit.append({'stage':stage,'status':'failed','seconds':time.perf_counter()-start,
                                   'error':'worker terminated','messages':[system,payload]})
            raise

    def close(self):
        if getattr(self,'process',None):
            if self.process.is_alive():
                try:self.pipe.send(None)
                except (BrokenPipeError, OSError):pass
                self.process.join(2)
                if self.process.is_alive():
                    self.process.terminate()
                    self.process.join(3)
                if self.process.is_alive():
                    self.process.kill()
                    self.process.join(3)
            self.pipe.close()


def qualify(model):
    """Real inference, JSON structure and action checks before experiments."""
    checks = []
    cases = [
        ('inference','Return only a JSON object matching the requested response_schema. Compute the requested arithmetic task.',
         {'task':'Compute 6 * 7.','response_schema':{'type':'object','properties':{'value':{'type':'integer'}},'required':['value'],'additionalProperties':False}},
         lambda r: type(r.get('value')) is int and r['value']==42),
        ('structured','Describe the supplied function. Return only one JSON object with exactly these keys: "summary" (string), "input_schema" (JSON Schema object), "functionalities" (list of strings). No explanation or code outside the JSON object.',
         {'code':'def normalize(name: str):\n    return name.strip().lower()'},
         lambda r: set(r)=={'summary','input_schema','functionalities'} and isinstance(r['summary'],str)
            and isinstance(r['input_schema'],dict) and isinstance(r['functionalities'],list)),
        ('action','Choose the tool and arguments to satisfy the task. Return only a JSON action with keys action, tool and arguments. Call the function with the supplied input, preserving its whitespace. Do not compute or pass the expected output.',
         {'task':'Call normalize_name with the supplied input. Do not normalize the arguments yourself.',
          'input':{'name':' Alice '},'response_schema':{'action':'call','tool':'normalize_name','arguments':{'name':'copy the input name verbatim'}},
          'tools':{'normalize_name':{'type':'object','properties':{'name':{'type':'string'}},'required':['name']}}},
         lambda r:r=={'action':'call','tool':'normalize_name','arguments':{'name':' Alice '}}),
    ]
    for name,system,payload,predicate in cases:
        try:
            response = model.complete('qualification_'+name,system,payload)
            ok = bool(predicate(response))
            checks.append({'name':name,'passed':ok,'response':response})
        except Exception as exc:
            checks.append({'name':name,'passed':False,'error':str(exc),'traceback':traceback.format_exc()})
    return {'passed':all(c['passed'] for c in checks),'checks':checks,'qualification_version':2,
            'scope':'small real model qualification; does not establish research accuracy',
            'calls':list(model.audit),'runtime':model.runtime}
