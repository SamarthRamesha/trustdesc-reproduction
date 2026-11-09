"""Free local inference. Safetensors only; no remote code or paid endpoints."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import time
import gc
import traceback
from trustdesc.common.io import canonical, digest
from trustdesc.common.models import ModelError

# Modern tokenizers can store the model's chat protocol outside JSON.
# Download it as data and verify its publisher hash; never fetch remote Python.
MODEL_FILE_PATTERNS = ['*.json','*.safetensors','*.txt','*.model','*.tiktoken','*.jinja']


def json_object(text):
    text = text.strip()
    if text.startswith('```') and text.endswith('```'):
        text = re.sub(r'^```(?:json)?\s*', '', text)[:-3].strip()
    try:
        value = json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON constant')))
    except ValueError as exc:
        raise ModelError('Invalid JSON; raw output saved in call record') from exc
    if not isinstance(value, dict):
        raise ModelError('Expected a JSON object')
    return value


def check_asset(path, expected):
    """HF LFS SHA-256 or Git blob SHA-1, bound to the pinned commit metadata."""
    path = Path(path)
    sha = hashlib.sha256()
    blob = hashlib.sha1(b'blob ' + str(path.stat().st_size).encode() + b'\x00')
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4*1024*1024), b''):
            sha.update(block)
            blob.update(block)
    expected_hash = expected.get('sha256') or expected.get('blob_id')
    actual = sha.hexdigest() if expected.get('sha256') else blob.hexdigest()
    if not expected_hash or actual != expected_hash:
        raise ModelError('Pinned model asset checksum mismatch: ' + path.name)
    return {'sha256': sha.hexdigest(), 'bytes': path.stat().st_size, 'publisher_hash_verified': True}


def model_file_manifest(model_id, revision, cache):
    cache = Path(cache)
    metadata = cache / ('manifest-' + digest([model_id,revision]) + '.json')
    if metadata.exists():
        value = json.loads(metadata.read_text())
        if value.get('model_id') != model_id or value.get('revision') != revision:
            raise ModelError('Model metadata cache identity mismatch')
        return value['files']
    from huggingface_hub import HfApi
    info = HfApi().model_info(model_id, revision=revision, files_metadata=True, token=False)
    if info.sha != revision:
        raise ModelError('Resolved model commit differs from pinned commit')
    result = {}
    for file in info.siblings:
        lfs = file.lfs
        expected_sha = getattr(lfs,'sha256',None) if lfs is not None else None
        if isinstance(lfs,dict):expected_sha=lfs.get('sha256')
        result[file.rfilename] = {'sha256':expected_sha, 'blob_id':file.blob_id}
    metadata.parent.mkdir(parents=True,exist_ok=True)
    temp = metadata.with_suffix('.part')
    temp.write_text(json.dumps({'model_id':model_id,'revision':revision,'files':result},indent=2)+'\n')
    temp.replace(metadata)
    return result


class LocalModel:
    mode = 'real_local_transformers_inference'

    def __init__(self, config, cache):
        import torch
        import transformers
        from huggingface_hub import snapshot_download, hf_hub_download
        from transformers import AutoModelForCausalLM, AutoTokenizer
        if not re.fullmatch('[0-9a-f]{40}', config['revision']):
            raise ModelError('Full immutable model revision required')
        self.cfg = config
        self.model_id = config['model_id']
        self.audit = []
        self.torch = torch
        self.device = config.get('device', 'cpu')
        if self.device not in {'cpu', 'cuda', 'mps'}:
            raise ModelError('Unsupported explicit inference device')
        if self.device == 'cuda' and not torch.cuda.is_available():
            raise ModelError('CUDA selected but PyTorch cannot use it; no silent CPU execution of the larger model')
        if self.device == 'cpu':
            torch.set_num_threads(min(4, torch.get_num_threads()))
        if self.device == 'mps' and not torch.backends.mps.is_available():
            raise ModelError('MPS selected but unavailable; no silent device substitution')
        self.fatal_error = False
        expected_assets = model_file_manifest(self.model_id, config['revision'], cache)
        snapshot = Path(snapshot_download(self.model_id, revision=config['revision'], cache_dir=str(cache),
                        token=False, allow_patterns=MODEL_FILE_PATTERNS))
        assets = {}
        for path in sorted(snapshot.rglob('*')):
            if path.is_file():
                relative = path.relative_to(snapshot).as_posix()
                if relative not in expected_assets:
                    raise ModelError('Unexpected file in pinned model snapshot: ' + relative)
                try:
                    assets[relative] = check_asset(path, expected_assets[relative])
                except ModelError:
                    # Repair a corrupt cached asset once, then validate again.
                    repaired = hf_hub_download(self.model_id, relative, revision=config['revision'], cache_dir=str(cache),
                                               token=False, force_download=True)
                    assets[relative] = check_asset(repaired, expected_assets[relative])
                    assets[relative]['cache_repaired'] = True
        self.tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False)
        precision = config.get('precision','float16' if self.device in {'cuda','mps'} else 'float32')
        self.model = AutoModelForCausalLM.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False,
                    use_safetensors=True, torch_dtype=getattr(torch,precision),
                    attn_implementation='eager').to(self.device).eval()
        self.runtime = {'model_id': self.model_id, 'revision': config['revision'], 'device': self.device,
                        'torch': torch.__version__, 'transformers': transformers.__version__, 'assets': assets,
                        'precision': precision,
                        'integrity': 'immutable HF commit metadata over TLS; LFS SHA-256 or Git blob SHA-1 verified before loading; metadata cached locally; no separate signed publisher manifest',
                        'paper_equivalence': False, 'api_cost_usd': 0.0, 'compute_cost_usd': None}

    def complete(self, stage, system, payload):
        if self.fatal_error:
            raise ModelError('Accelerator context failed; restart model worker before further inference')
        messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': canonical(payload)}]
        inputs = self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                    return_dict=True, return_tensors='pt')
        count = inputs['input_ids'].shape[-1]
        record = {'stage': stage, 'messages': messages, 'request_hash': digest(messages),
                  'input_tokens': count, 'output_tokens': None, 'model': self.model_id,
                  'revision': self.cfg['revision'], 'cost_usd': 0.0, 'compute_cost_usd': None,
                  'status': 'started', 'temperature': self.cfg.get('temperature', .2),
                  'max_generation_seconds': self.cfg.get('max_generation_seconds',90)}
        self.audit.append(record)
        ids = inputs['input_ids']
        low,high = int(ids.min()),int(ids.max())
        vocab = self.model.get_input_embeddings().num_embeddings
        record['token_bounds']={'min':low,'max':high,'embedding_rows':vocab}
        if low < 0 or high >= vocab:
            record.update(status='failed',error='Input token outside embedding vocabulary')
            raise ModelError('Input token outside embedding vocabulary; prevented device assertion')
        if count > self.cfg.get('max_input_tokens', 4096):
            record['status'] = 'context_limit'
            raise ModelError(f'Input has {count} tokens, beyond context cap; no truncation')
        seed = (self.cfg.get('seed', 42) + int(digest(messages)[:8], 16)) % (2**31)
        self.torch.manual_seed(seed)
        start = time.perf_counter()
        try:
            inputs = inputs.to(self.device)
            if self.device == 'cuda':
                self.torch.cuda.synchronize()
            with self.torch.inference_mode():
                from transformers import LogitsProcessor, LogitsProcessorList
                class FiniteLogits(LogitsProcessor):
                    def __call__(processor, input_ids, scores):
                        if self.torch.isnan(scores).any().item() or self.torch.isposinf(scores).any().item() or self.torch.isneginf(scores).all(dim=-1).any().item():
                            raise ModelError('Non-finite logits detected before sampling; no fabricated recovery')
                        return scores
                temperature=self.cfg.get('temperature', .2)
                output = self.model.generate(**inputs, do_sample=temperature>0,
                    **({'temperature':temperature} if temperature>0 else {}),
                    logits_processor=LogitsProcessorList([FiniteLogits()]),
                    max_new_tokens=self.cfg.get('max_new_tokens', 1600), max_time=self.cfg.get('max_generation_seconds',90),
                    pad_token_id=self.tokenizer.eos_token_id)
            if self.device == 'cuda':
                self.torch.cuda.synchronize()
            tokens = output[0][count:]
            text = self.tokenizer.decode(tokens, skip_special_tokens=True)
            record.update(raw_content=text, output_tokens=len(tokens), seed=seed)
            if not len(tokens):
                raise ModelError('Model generated no output tokens')
            if time.perf_counter()-start >= self.cfg.get('max_generation_seconds',90) and int(tokens[-1]) != self.tokenizer.eos_token_id:
                raise ModelError('Generation deadline reached; partial response not accepted')
            if len(tokens) >= self.cfg.get('max_new_tokens', 1600) and int(tokens[-1]) != self.tokenizer.eos_token_id:
                raise ModelError('Output token limit reached; partial JSON not accepted')
            result = json_object(text)
            record.update(status='completed', response=result)
            return result
        except Exception as exc:
            self.fatal_error = 'device-side assert' in str(exc).lower()
            record.update(status='failed', error_type=type(exc).__name__, error=str(exc),traceback=traceback.format_exc(),fatal_accelerator_error=self.fatal_error)
            raise
        finally:
            record['seconds'] = time.perf_counter() - start

    def close(self):
        self.model = self.tokenizer = None
        gc.collect()
        if self.device == 'mps': self.torch.mps.empty_cache()
        if self.device == 'cuda' and not self.fatal_error: self.torch.cuda.empty_cache()


class RepairModel:
    """One format-repair retry. Never supplies a scripted semantic response."""
    def __init__(self, model):
        self.model = model
        self.model_id, self.mode = model.model_id, model.mode

    @property
    def audit(self):
        return self.model.audit

    def complete(self, stage, system, payload):
        try:
            return self.model.complete(stage, system, payload)
        except ModelError as exc:
            if 'JSON' not in str(exc):
                raise
            raw = self.model.audit[-1].get('raw_content', '')
            # Some models emit the requested records as a bare JSON array.
            # Restore only the container key: never invent/change a record,
            # claim, reference, rationale, task or verdict. Downstream validators
            # still require exact claim coverage and real source references.
            key={'source_grounding':'evidence','verification_plan':'tasks'}.get(stage)
            if key:
                try:
                    array=json.loads(raw,parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON')))
                except ValueError:
                    array=None
                if isinstance(array,list) and all(isinstance(row,dict) for row in array):
                    value={key:array}
                    self.model.audit[-1]['format_normalization']={'kind':'bare_array_container','key':key,
                        'semantic_content_changed':False,'downstream_validation_required':True}
                    self.model.audit[-1]['normalized_response']=value
                    return value
            return self.model.complete(stage, system + '\nThe previous response was invalid JSON. Return ONLY the specified JSON object.',
                         {'original_request': payload, 'invalid_response': raw, 'error': str(exc)})

    def close(self):
        self.model.close()
