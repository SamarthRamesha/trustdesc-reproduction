#!/usr/bin/env python3
"""Supplementary real-model study of a public MCP example's isolated function.

This executes the pinned add implementation body, not an MCP transport or a
paper-benchmark tool. The distinction is retained in every exported result.
"""
from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from trustdesc.common.io import canonical,digest
from trustdesc.descgen.prompts import AGENT
from trustdesc.experiments.models import LoggedModel
from trustdesc.experiments.storage import Store
from trustdesc.experiments.workflow import implementation_hash
from trustdesc.experiments.runtime import inspect_runtime
from trustdesc.reproduction.backends import ManagedModel,qualify
from trustdesc.reproduction.model import RepairModel
from trustdesc.reproduction.evidence import grounded_generate,iterative_verify
from trustdesc.slicemin.research import ResearchSlicer
from trustdesc.sandbox.seatbelt import SeatbeltPython

REVISION='77001c96f9507be0f4d009b83210a384a5e08bda'
SOURCE_BLOB='70a83a56e4b69d90f7c8c8d675df4433f4cc01e4'
SCOPE='Public MCP SDK example function-body experiment; not MCP transport or original TRUSTDESC benchmark'
TASKS=[('positive',{'a':2,'b':3},5),('negative',{'a':-7,'b':2},-5),
       ('zero',{'a':0,'b':0},0),('large',{'a':123456789,'b':987654321},1111111110)]


class IsolatedAgent:
    def __init__(self,model,boundary,source,description):
        self.model,self.boundary,self.source,self.description=model,boundary,source,description

    def run(self,task):
        events=[]
        for step in range(4):
            response=self.model.complete('agent',AGENT,{'task':task,'tools':{'add':{'input_schema':self.description['input_schema'],'description':self.description}},'observations':events,'step':step})
            if response.get('action')=='finish':
                return {'backend':'macos_seatbelt_public_function','status':'completed','events':events,'answer':response.get('answer'),'scope':SCOPE}
            if response.get('action')!='call' or response.get('tool')!='add' or not isinstance(response.get('arguments'),dict):
                return {'backend':'macos_seatbelt_public_function','status':'agent_error','events':events,'reason':'Invalid allowlisted action'}
            arguments=response['arguments']
            observed=self.boundary.run_source(self.source,'add',arguments)
            observation=observed.get('observation')
            if observed['returncode'] or not observation:
                return {'backend':'macos_seatbelt_public_function','status':'sandbox_error','events':events,'diagnostic':observed}
            event={'index':step,'tool':'add','arguments':arguments,**observation,'isolation':observed}
            events.append(event)
        return {'backend':'macos_seatbelt_public_function','status':'step_limit','events':events}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    args=parser.parse_args()
    raw=(ROOT/'data/public_example/server.py').read_bytes()
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if blob!=SOURCE_BLOB:raise RuntimeError('Pinned public example Git blob mismatch')
    tree=ast.parse(raw)
    original=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='add')
    extracted=copy.deepcopy(original);extracted.decorator_list=[]
    source=ast.unparse(extracted)+'\n'
    config_spec=json.loads((ROOT/'configs/reproduction.json').read_text())
    config={**config_spec['model_settings'],**config_spec['models_by_hardware']['mlx'],'device':'metal'}
    identity={'source_sha256':hashlib.sha256(raw).hexdigest(),'extracted_sha256':hashlib.sha256(source.encode()).hexdigest(),
              'model':config,'tasks':TASKS,'scope':SCOPE,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'implementation_hash':implementation_hash()}
    run=args.workspace/('public-example-'+digest(identity)[:20])
    if run.exists():
        index=run/'artifact_hashes.json'
        if index.exists() and (run/'results.json').exists():
            hashes=json.loads(index.read_text())
            if all((run/name).is_file() and hashlib.sha256((run/name).read_bytes()).hexdigest()==sha for name,sha in hashes.items()):
                print(json.dumps({'run':str(run),'status':'resumed_verified_public_observations','scope':SCOPE}),flush=True)
                return
        raise RuntimeError('Existing public run is incomplete or changed; preserved without overwrite')
    store=Store(run)
    store.write('environment.json',inspect_runtime())
    for path in (ROOT/'src').rglob('*'):
        if path.is_file() and path.suffix in {'.py','.txt'}:
            store.text(Path('reproduction_source')/path.relative_to(ROOT),path.read_text())
    store.text('reproduction_source/scripts/run_public_example.py',Path(__file__).read_text())
    store.write('manifest.json',{**identity,'revision':REVISION,'git_blob':SOURCE_BLOB,'license':'MIT',
                                'url':f'https://github.com/modelcontextprotocol/python-sdk/blob/{REVISION}/examples/snippets/servers/mcpserver_quickstart.py',
                                'transformation':'Extract add AST node and remove only mcp.tool decorator; function signature/body unchanged; no framework validation or MCP transport',
                                'original_paper_benchmark':False})
    store.text('source/original.py.txt',raw.decode())
    store.text('source/extracted.py.txt',source)
    store.text('source/LICENSE',(ROOT/'data/public_example/LICENSE').read_text())
    boundary=SeatbeltPython(args.workspace/'sandbox')
    probe=boundary.probe();store.write('isolation_probe.json',probe)
    if not probe['passed']:raise RuntimeError('Isolation probe failed; no public code executed')
    model=ManagedModel(config,args.cache)
    try:
        qualification=qualify(model);store.write('model_qualification.json',qualification)
        if not qualification['passed']:raise RuntimeError('Model failed qualification')
        logged=LoggedModel(RepairModel(model),store,config,{'stage':'public_example','scope':SCOPE})
        sliced=ResearchSlicer(ROOT/'data/public_example').slice('add')
        store.write('slice.json',sliced)
        draft=grounded_generate(sliced,logged);store.write('draft.json',draft)
        verified=iterative_verify(draft['description'],logged,IsolatedAgent(logged,boundary,source,draft['description']),sliced,
                                  max_rounds=2,source_evidence=draft['source_evidence'])
        store.write('verification.json',verified)
        original_description={'summary':ast.get_docstring(original),'functionalities':[],
                              'input_schema':{'type':'object','properties':{'a':{'type':'integer'},'b':{'type':'integer'}},'required':['a','b']}}
        records=[]
        for condition,description in [('original',original_description),('lite',verified['lite']),('full',verified['full'])]:
            for name,arguments,expected in TASKS:
                if condition!='original' and not verified['usable_summary']:
                    records.append({'condition':condition,'task':name,'status':'unavailable','success':None});continue
                task='Add the two integers in these exact arguments: '+canonical(arguments)
                trace=IsolatedAgent(logged,boundary,source,description).run(task)
                success=any(e['arguments']==arguments and e.get('status')=='ok' and e.get('result')==expected for e in trace['events'])
                records.append({'condition':condition,'task':name,'arguments':arguments,'expected':expected,'trace':trace,
                                'status':trace['status'],'success':success,'scope':SCOPE,'oracle':'project-authored exact arithmetic observation'})
                store.write('task_results.json',records)
        store.write('results.json',{'scope':SCOPE,'records':records,'paper_TSR':None,'peak_worker_rss_bytes':model.peak_worker_rss_bytes,
                                   'fixed_task_agent':config,'original_benchmark':False})
        store.write('artifact_hashes.json',{name:hashlib.sha256((run/name).read_bytes()).hexdigest()
                    for name in store.read('OUTPUT_INDEX.json') if name!='OUTPUT_INDEX.json'})
        print(json.dumps({'run':str(run),'scope':SCOPE,'condition_successes':{c:sum(r.get('success') is True for r in records if r['condition']==c) for c in ['original','lite','full']}},indent=2),flush=True)
    finally:model.close()


if __name__=='__main__':main()
