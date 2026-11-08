from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import time
import subprocess

from trustdesc.common.io import digest, ValidationError
from trustdesc.descgen import generate
from trustdesc.descgen import prompts
from trustdesc.dynver import verify
from trustdesc.sandbox import ControlledAgent, DisabledRunner
from trustdesc.slicemin import PythonSlicer
from .data import source_hashes
from .models import ModelPool
from .storage import Store, now

RECONSTRUCT=prompts.BOUNDARY+'''Generate four diverse user tasks without mentioning the tool name.
Two must derive from the supplied original metadata, two from the generated description.
Return {"original":["task","task"],"generated":["task","task"]}.
These are reconstructed research tasks, never original author benchmark records.'''


def implementation_hash():
    root=Path(__file__).resolve().parents[1]
    return digest({p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(root.rglob('*')) if p.is_file() and p.suffix in {'.py','.txt'}})


class Workflow:
    """Resumable orchestration calling the existing slicer/generator/verifier/agent.

    Does not implement new slicing semantics or an arbitrary execution backend.
    All output is under one run root, with hash-bound stage/task checkpoints.
    """
    def __init__(self,project,run_root,config,bundle,roots,runtime,*,resume=False,retry_failed=False,
                 credentials=None,approved_http=(),allow_download=False,pool=None):
        self.project=Path(project);self.root=Path(run_root);self.config=copy.deepcopy(config)
        self.bundle=copy.deepcopy(bundle);self.tools={t['id']:t for t in self.bundle['tools']}
        if len(self.tools)!=len(self.bundle['tools']):raise ValidationError('Duplicate tool IDs')
        self.tasks=copy.deepcopy(bundle['tasks']);self.roots=roots;self.runtime=runtime;self.retry=retry_failed
        if len({t['id'] for t in self.tasks})!=len(self.tasks):raise ValidationError('Duplicate task IDs')
        if not self.config.get('models') or len({m['id'] for m in self.config['models']})!=len(self.config['models']):raise ValidationError('Select unique model configurations')
        if any(k.lower() in {'api_key','password','access_token','authorization'} for m in self.config['models'] for k in m):raise ValidationError('Credentials must be supplied in memory, never configuration')
        for m in self.config['models']:
            if m.get('reasoning','provider_default')!='provider_default':raise ValidationError('This adapter preserves provider-default reasoning only; no silent setting translation')
        self.sources=source_hashes(roots)
        binding={'config':self.config,'dataset':self.bundle,'sources':self.sources,'implementation':implementation_hash(),
            'runtime_identity':{'python':runtime.get('python'),'machine':runtime.get('machine'),'packages':runtime.get('packages'),
                                     'gpus':[(g['name'],g['total_bytes']) for g in runtime.get('gpus',[])]},
                 'prompt_hashes':{k:digest(getattr(prompts,k)) for k in ['DEBLOAT','IDENTIFIERS','GENERATE','PLAN','AGENT','JUDGE']}}
        self.fingerprint=digest(binding)
        existing=self.root/'EXPERIMENT_MANIFEST.json'
        if existing.exists():
            old=json.loads(existing.read_text())
            if not resume:raise ValidationError('Run exists: explicitly choose resume or a fresh run directory')
            if old['run_id']!=self.root.name:raise ValidationError('Resume must preserve the original run directory name')
            if old['fingerprint']!=self.fingerprint:raise ValidationError('Resume configuration/dataset/source/model/code/runtime mismatch; use a new run')
        elif self.root.exists() and any(self.root.iterdir()):raise ValidationError('Nonempty directory is not a valid experiment run')
        self.store=Store(self.root,secrets=(credentials or {}).values())
        self.pool=pool or ModelPool(self.store,runtime,credentials=credentials,approved_http=approved_http,allow_download=allow_download)
        self.manifest=old if existing.exists() else {'schema_version':1,'run_id':self.root.name,'created_at':now(),
             'fingerprint':self.fingerprint,'binding':binding,'dataset_hash':digest(self.bundle),
             'source_hash':digest(self.sources),'implementation_hash':binding['implementation'],
             'origin':bundle['origin'],'full_scientific_reproduction':False,'status':'prepared'}
        if not existing.exists():
            portable=self.project/'PORTABLE_MANIFEST.json'
            if portable.exists():
                self.manifest['project_commit']=json.loads(portable.read_text()).get('git_commit')
            else:
                p=subprocess.run(['git','rev-parse','HEAD'],cwd=self.project,capture_output=True,text=True)
                self.manifest['project_commit']=p.stdout.strip() if p.returncode==0 else None
        self.store.write('EXPERIMENT_MANIFEST.json',self.manifest)
        self.store.write('config.json',self.config);self.store.write('dataset.json',self.bundle)
        self.store.write('source_hashes.json',self.sources);self.store.write('environment.json',runtime)
        self.store.write('prompt_versions.json',{**{k:getattr(prompts,k) for k in ['DEBLOAT','IDENTIFIERS','GENERATE','PLAN','AGENT','JUDGE']},'RECONSTRUCT':RECONSTRUCT})
        if bundle.get('public_license_text'):
            self.store.write('source_notices.json',{'arxiv_source_license':bundle['public_license_text'],'provenance':bundle['public_source']})

    def key(self,stage,**parts):return {'run_fingerprint':self.fingerprint,'stage':stage,**parts}
    def job(self,stage,operation,**parts):return self.store.job(self.key(stage,**parts),operation,retry_failed=self.retry)

    def static(self):
        results={}
        for tid,t in self.tools.items():
            def analyze(t=t):
                if t.get('language')!='python':return {'status':'unavailable','reason':'TypeScript has not been validated; not substituted with Python'}
                r=PythonSlicer(self.roots[t['source_ref']]).slice(t['name'],explicit_entry=t.get('entry'))
                return {'status':'completed','slice':r}
            results[tid]=self.job('static',analyze,tool=tid)
        self.store.write('static_results.json',results);return results

    def descriptions(self):
        static=self.static();results={}
        for cfg in self.config['models']:
            results[cfg['id']]={}
            for tid,t in self.tools.items():
                def describe(cfg=cfg,t=t,tid=tid):
                    if static[tid]['status']!='completed':return {'status':'blocked','reason':'Static analysis unavailable'}
                    sliced=static[tid]['slice']
                    if cfg.get('debloat',False):
                        m=self.pool.get(cfg,'debloat',t)
                        sliced=PythonSlicer(self.roots[t['source_ref']]).slice(t['name'],explicit_entry=t.get('entry'),model=m,max_passes=cfg.get('max_debloat_passes',3))
                    model=self.pool.get(cfg,'descgen',t)
                    draft=generate(sliced,model)
                    return {'status':'completed','slice':sliced,'draft':draft}
                results[cfg['id']][tid]=self.job('descgen',describe,model=cfg['id'],tool=tid)
        self.store.write('description_results.json',results);return results

    def verification(self):
        descriptions=self.descriptions();results={}
        for cfg in self.config['models']:
            results[cfg['id']]={}
            for tid,t in self.tools.items():
                def perform(cfg=cfg,t=t,tid=tid):
                    d=descriptions[cfg['id']][tid]
                    if d['status']!='completed':return {'status':'blocked','reason':'Description generation not completed'}
                    model=self.pool.get(cfg,'dynver',t)
                    runner=ControlledAgent(model,max_steps=self.config.get('agent_max_steps',6)) if t['backend']=='controlled_fixture' else DisabledRunner()
                    v=verify(d['draft']['description'],model,runner)
                    return {'status':'completed','verification':v,'execution_backend':t['backend'],
                            'limitation':'Controlled fixtures only; external claims without execution are inconclusive.'}
                results[cfg['id']][tid]=self.job('dynver',perform,model=cfg['id'],tool=tid)
        self.store.write('verification_results.json',results);return results

    def reconstruct_tasks(self):
        derived=[]
        if self.config.get('generate_reconstructed_tasks',False):
            descriptions=self.descriptions()
            for cfg in self.config['models']:
                if cfg['provider']=='replay':continue
                for tid,t in self.tools.items():
                    if t['backend']=='controlled_fixture':continue
                    def create(cfg=cfg,t=t,tid=tid):
                        draft=descriptions[cfg['id']][tid]
                        if draft['status']!='completed':return {'status':'blocked','reason':'A real generated description is required for reconstructed tasks'}
                        m=self.pool.get(cfg,'task_reconstruction',t)
                        result=m.complete('task_reconstruction',RECONSTRUCT,{'tool_name':t['name'],'original':t['original_description'],'generated':draft['draft']['description']})
                        if set(result)!={'original','generated'} or any(not isinstance(result[k],list) or len(result[k])!=2 for k in result):raise ValidationError('Reconstruction requires two tasks per description source')
                        rows=[]
                        for source in ['original','generated']:
                            for i,text in enumerate(result[source]):
                                if not isinstance(text,str) or not text.strip() or t['name'].casefold() in text.casefold():raise ValidationError('Generated task is empty or mentions target tool name')
                                rows.append({'id':'reconstructed-'+digest([tid,cfg['id'],source,i])[:16],'tool_id':tid,'tool':t['name'],'task':text,
                                             'origin':'reconstructed','source_description':source,'generator':cfg['id'],
                                             'provenance':t.get('source_provenance'),'label':None,'review_criterion':'Human judgment required; arbitrary external execution unavailable.'})
                        return {'status':'completed','tasks':rows}
                    r=self.job('reconstruct_tasks',create,model=cfg['id'],tool=tid)
                    if r['status']=='completed':derived.extend(r['tasks'])
        known={r['id'] for r in self.tasks}
        self.tasks.extend(t for t in derived if t['id'] not in known)
        self.store.write('derived_tasks.json',{'origin':'reconstructed','tasks':derived,'sha256':digest(derived),'not_original_208':True})
        return derived

    def benchmark(self):
        verified=self.verification();self.reconstruct_tasks();records=[]
        for cfg in self.config['models']:
            for variant in ['original','lite','full']:
                descriptions={}
                for tid,t in self.tools.items():
                    if t['backend']!='controlled_fixture':continue
                    v=verified[cfg['id']][tid]
                    if variant=='original':descriptions[t['name']]=t['original_description']
                    elif v['status']=='completed' and v['verification']['usable_summary']:
                        descriptions[t['name']]=v['verification'][variant]
                for task in self.tasks:
                    t=self.tools[task['tool_id']]
                    result_id=digest([self.fingerprint,cfg['id'],variant,task])
                    def execute(cfg=cfg,variant=variant,task=task,t=t,result_id=result_id,descriptions=descriptions):
                        if t['backend']!='controlled_fixture':return {'status':'blocked','reason':'No validated isolated MCP backend; Colab host execution forbidden'}
                        if t['name'] not in descriptions:return {'status':'unavailable','reason':'Refined description unavailable/unusable; condition not silently replaced'}
                        before={p.name for p in (self.root/'calls').rglob('*.json')} if (self.root/'calls').exists() else set()
                        model=self.pool.get(cfg,'benchmark',t,task,context={'result_id':result_id,'condition':variant,'task':task['id']})
                        start=time.perf_counter()
                        trace=ControlledAgent(model,max_steps=self.config.get('agent_max_steps',6),tool_descriptions=descriptions).run(task['task'])
                        seconds=time.perf_counter()-start
                        calls=[json.loads(p.read_text()) for p in (self.root/'calls').rglob('*.json') if p.name not in before]
                        def total(k):
                            values=[c.get(k) for c in calls]
                            return sum(values) if values and all(type(v) in {int,float} for v in values) else None
                        return {'status':'completed' if trace['status']=='completed' else 'failed','trace':trace,
                                'observed_target_invoked':any(e['tool']==t['name'] for e in trace['events']),
                                'latency_seconds':seconds,'input_tokens':total('input_tokens'),'output_tokens':total('output_tokens'),
                                'cost_usd':total('cost_usd'),'tool_calls':len(trace['events']),
                                'call_record_ids':[c['request_hash'] for c in calls],
                                'condition_descriptions_hash':digest(descriptions),'model_mode':model.mode,
                                'objective_achieved':None,'reviewed':False}
                    r=self.job('benchmark',execute,model=cfg['id'],variant=variant,task=task['id'],task_hash=digest(task))
                    record={**r,'result_id':result_id,'task_id':task['id'],'tool_id':t['id'],'tool_name':t['name'],
                            'model':cfg['id'],'variant':variant,'task':task['task'],'dataset_origin':task.get('origin',self.bundle['origin']),
                            'backend':t['backend'],'run_id':self.root.name,'run_fingerprint':self.fingerprint}
                    record['evidence_hash']=digest(record)
                    records.append(record)
        self.store.write('task_predictions.json',records)
        from .review import review_template
        review_template(self.root)
        self.manifest.update(status='execution_finished_requires_human_review',updated_at=now(),
                             effective_tasks=len(self.tasks),task_attempts=len(records),
                             incomplete=sum(r['status']!='completed' for r in records))
        self.store.write('EXPERIMENT_MANIFEST.json',self.manifest)
        return records
