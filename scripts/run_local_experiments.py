#!/usr/bin/env python3
"""Our engineering measurements. No paper TSR, models, paid calls or remote code."""
from pathlib import Path
from datetime import datetime, timezone
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from trustdesc.common.io import digest, dump, load
from trustdesc.common.models import ReplayModel
from trustdesc.fixtures import DESCRIPTION, replay
from trustdesc.pipeline import run_pipeline
from trustdesc.sandbox import ControlledAgent
from trustdesc.slicemin import PythonSlicer

def main():
    cfg=load(ROOT/'configs/experiments.json');runs=[]
    batch=ROOT/'experiments/runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    version=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip() or None
    dirty=bool(subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,text=True).stdout.strip())
    # Hash actual executable project sources/configs independently of Git state.
    inputs={p.relative_to(ROOT).as_posix():p.read_text() for folder in ['src','configs','tests/fixtures'] for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and p.suffix in {'.py','.json'}}
    for i in range(cfg['local_repetitions']):
        model=ReplayModel(replay());tracemalloc.start();start=time.perf_counter()
        r=run_pipeline(ROOT/'tests/fixtures','apply_formula',model,ControlledAgent(model),batch/f'local-{i:03d}')
        seconds=time.perf_counter()-start
        _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        decisions={d['claim_id']:d['verdict'] for d in r['decisions']}
        if decisions.get('auto_prefix')!='refuted' or decisions.get('internal')!='not_runtime_verifiable':
            raise RuntimeError('Synthetic expected behavior changed; inspect before reporting')
        runs.append({'index':i,'seconds':seconds,'peak_python_bytes':peak,'decisions':decisions,
                     'model_inference':False,'api_calls':0,'cost_usd_actual':0.0,
                     'verified_trace_count':len(r['traces'])})
    # Copy one complete trace set to a small, versioned report; repetitive raw runs remain ignored.
    for p in sorted((batch/'local-000').glob('*.json')):
        dump(ROOT/'reports/local_example'/p.name,load(p))
    dump(ROOT/'reports/local_experiments.json',{
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),'raw_run_directory':str(batch.relative_to(ROOT)),'experiment_type':'synthetic_engineering_only',
        'config':cfg,'config_hash':digest(cfg),'source_content_hash':digest(inputs),'git_commit':version,'working_tree_dirty_at_run':dirty,
        'python':platform.python_version(),'platform':platform.platform(),'seed':cfg['seed'],
        'measurement':'wall time incl. JSON persistence under tracemalloc; Python allocation peak, not process RSS/GPU memory',
        'runs':runs,'summary':{'repetitions':len(runs),'median_seconds':statistics.median(x['seconds'] for x in runs),
                            'min_seconds':min(x['seconds'] for x in runs),'max_seconds':max(x['seconds'] for x in runs),
                            'max_peak_python_bytes':max(x['peak_python_bytes'] for x in runs),'remote_calls':0,'paid_cost_usd':0},
        'paper_metrics':None,'comparison_to_paper':'Not comparable: replay responses, synthetic tasks/tools, no LangChain/MCP or LLM inference.'})
    print('Saved local evidence; synthetic engineering experiment, not paper reproduction.')

if __name__=='__main__':main()
