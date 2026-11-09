from __future__ import annotations
import copy
import gc
import time
import uuid
import traceback
from pathlib import Path

from trustdesc.common.io import digest, ValidationError
from trustdesc.common.models import ReplayModel, HTTPModel, ModelError
from trustdesc.common.transformers_model import TransformersModel
from trustdesc.fixtures import replay, record
from .storage import now


class Unavailable(ModelError):
    experiment_status='unavailable'


def fixture_description(name):
    if name=='apply_formula':return copy.deepcopy(replay()[1]['response'])
    values=[('summary','Returns a normalized name.',['summary']),
            ('normalize','Trims surrounding whitespace and lowercases the text.',['functionalities',0]),
            ('input','Text to normalize.',['input_schema','properties','name','description'])]
    return {'summary':values[0][1],'functionalities':[values[1][1]],
            'input_schema':{'type':'object','properties':{'name':{'type':'string','description':values[2][1]}},'required':['name']},
            'claims':[{'id':i,'text':t,'target':p} for i,t,p in values]}


def replay_for(stage,tool,task=None):
    name=tool['name']
    if tool['backend']!='controlled_fixture':raise Unavailable('No synthetic semantic replay exists for external source')
    if stage=='descgen':return replay()[:2] if name=='apply_formula' else [record('identifier_filter',{'renames':{}}),record('description',fixture_description(name))]
    if stage=='dynver':
        if name=='apply_formula':return replay()[2:]
        desc=fixture_description(name)
        tasks=[{'claim_id':c['id'],'verifiable':True,'task':'Normalize the text " Alice ".','reason':'Observe text normalization on a controlled case.'} for c in desc['claims']]
        result=[record('verification_plan',{'tasks':tasks})]
        for c in desc['claims']:
            result += [record('agent',{'action':'call','tool':name,'arguments':{'name':' Alice '}}),record('agent',{'action':'finish','answer':'Observed the fixture output.'}),record('judge',{'verdict':'supported','reason':'Scripted engineering expectation for the observed fixture case, not actual LLM judging.'})]
        return result
    if stage=='benchmark':return [record('agent',{'action':'call','tool':name,'arguments':task['fixture_arguments']}),record('agent',{'action':'finish','answer':'Recorded the controlled fixture observation; human objective review required.'})]
    raise Unavailable('Replay is not LLM-guided debloating or task reconstruction')


class LoggedModel:
    def __init__(self,model,store,cfg,context):
        self.model,self.store,self.cfg,self.context=model,store,cfg,context
        self.model_id,self.mode=model.model_id,model.mode

    def complete(self,stage,system,payload):
        folder=Path('calls')/digest(self.cfg)[:16]
        paths=list((self.store.root/folder).glob('*.json')) if (self.store.root/folder).exists() else []
        if len(paths)>=self.cfg.get('max_calls',200):raise ModelError('Persistent per-run model request cap reached')
        name=folder/(uuid.uuid4().hex+'.json')
        value={'stage':stage,'context':self.context,'model':self.cfg,'mode':self.mode,
               'request_hash':digest({'system':system,'payload':payload}),'system':system,'payload':payload,
               'status':'started','started_at':now(),'input_tokens':None,'output_tokens':None,'cost_usd':0.0 if self.mode=='synthetic_replay' else None}
        self.store.write(name,value);start=time.perf_counter();before=len(getattr(self.model,'audit',[]))
        try:
            result=self.model.complete(stage,system,payload)
            value.update(status='completed',response=result)
            return result
        except Exception as exc:
            value.update(status='failed',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
            raise
        finally:
            audits=getattr(self.model,'audit',[])[before:]
            value.update(seconds=time.perf_counter()-start,finished_at=now(),provider_audit=audits)
            if audits:
                a=audits[-1];usage=a.get('usage') or {}
                value['input_tokens']=a.get('input_tokens',usage.get('prompt_tokens'))
                value['output_tokens']=a.get('output_tokens',usage.get('completion_tokens'))
                actual=usage.get('cost',a.get('cost_usd'))
                if type(actual) in {float,int} and actual>=0:value['cost_usd']=actual
            self.store.write(name,value)


class ModelPool:
    def __init__(self,store,runtime,*,credentials=None,approved_http=(),allow_download=False):
        self.store,self.runtime=store,runtime
        self.credentials=credentials or {};self.approved=set(approved_http);self.allow_download=allow_download
        self.cache_key=None;self.cached=None
        self.store.secrets.extend(v for v in self.credentials.values() if v)

    def get(self,cfg,stage,tool,task=None,context=None):
        provider=cfg['provider']
        if provider=='replay':model=ReplayModel(replay_for(stage,tool,task))
        elif provider=='http':
            if not cfg.get('model_id') or not cfg.get('endpoint'):raise Unavailable('Provider model ID/endpoint is unavailable; paper display name is not an endpoint ID')
            if digest(cfg) not in self.approved:raise Unavailable('Paid/remote execution not explicitly confirmed for this exact configuration')
            key=self.credentials.get(cfg.get('credential_name','TRUSTDESC_API_KEY'))
            if not key:raise Unavailable('Required provider credential not supplied')
            model=HTTPModel(cfg['endpoint'],cfg['model_id'],api_key=key,allow_remote=True,allow_paid=True,
                            timeout=cfg.get('timeout',60),temperature=cfg.get('temperature',.2),max_tokens=cfg.get('max_new_tokens',2048))
        elif provider=='transformers':
            gpus=self.runtime.get('gpus',[])
            if not gpus or gpus[0]['free_bytes']<cfg.get('minimum_gpu_bytes',8*1024**3):raise Unavailable('Selected local model exceeds inspected GPU capacity or no CUDA GPU exists')
            ram=self.runtime.get('ram_available_bytes')
            if cfg.get('minimum_ram_bytes') and (ram is None or ram<cfg['minimum_ram_bytes']):raise Unavailable('Selected local model exceeds inspected available host RAM; choose a high-RAM runtime or another explicit configuration')
            if not self.allow_download:raise Unavailable('Public model download was not explicitly opted in')
            if self.cache_key!=digest(cfg) or self.cached is None:
                self.cached=None;gc.collect()
                try:
                    import torch
                    torch.cuda.empty_cache()
                except ImportError:pass
                self.cached=TransformersModel(allow_download=True,model_id=cfg['model_id'],revision=cfg['revision'],
                      seed=cfg.get('seed',42),temperature=cfg.get('temperature',.2),
                      max_input_tokens=cfg.get('max_input_tokens',4096),max_new_tokens=cfg.get('max_new_tokens',2048))
                self.cache_key=digest(cfg)
            model=self.cached
        else:raise ModelError('Unknown provider')
        return LoggedModel(model,self.store,cfg,context or {'stage':stage,'tool':tool['id']})


def cost_preview(cfg,*,assumed_input_tokens=2500):
    rates=cfg.get('price_per_million',{})
    estimate=None
    if all(type(rates.get(k)) in {int,float} and rates[k]>=0 for k in ['input','output']):
        estimate=cfg.get('max_calls',200)*(assumed_input_tokens*rates['input']+cfg.get('max_new_tokens',2048)*rates['output'])/1_000_000
    return {'model_id':cfg.get('model_id'),'paper_name':cfg.get('paper_name'),'provider':cfg['provider'],
            'endpoint':cfg.get('endpoint'),'max_requests':cfg.get('max_calls',200),
            'planning_estimate_usd':estimate,'estimate_assumptions':f'{assumed_input_tokens} input tokens and maximum configured output per request; not a billing cap; rates must be supplied/verified',
            'transmitted_data':'Selected tool source slices, reconstructed prompts, descriptions, tasks and execution traces. No API credentials are placed in prompts.',
            'confirmation_hash':digest(cfg),'paid_automatic':False}
