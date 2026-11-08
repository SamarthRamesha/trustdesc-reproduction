#!/usr/bin/env python3
"""CPU/replay entry point for the same modules used by the primary notebook."""
from pathlib import Path
import argparse
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from trustdesc.experiments.runtime import inspect_runtime
from trustdesc.experiments.setup import prepare_inputs
from trustdesc.experiments.workflow import Workflow
from trustdesc.experiments.report import analyze
from trustdesc.experiments.export import export_results

def main():
    p=argparse.ArgumentParser(description='Complete controlled CPU experiment; no credentials/inference')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--resume',action='store_true')
    p.add_argument('--retry-failed',action='store_true');p.add_argument('--acquire-public',action='store_true')
    p.add_argument('--public-archive',type=Path);p.add_argument('--resource-bundle',type=Path)
    a=p.parse_args()
    base=json.loads((ROOT/'configs/colab_experiment.json').read_text())
    models=json.loads((ROOT/'configs/colab_models.json').read_text())['models'][:1]
    cfg={'profile':'A','models':models,'agent_max_steps':base['agent_max_steps'],'generate_reconstructed_tasks':False}
    bundle,roots,acquisition=prepare_inputs(ROOT,a.output.parent/('inputs-'+a.output.name),acquire_public=a.acquire_public,
                                            public_archive=a.public_archive,resource_bundle=a.resource_bundle)
    w=Workflow(ROOT,a.output,cfg,bundle,roots,inspect_runtime(),resume=a.resume,retry_failed=a.retry_failed)
    w.store.write('ACQUISITION_REPORT.json',acquisition)
    w.benchmark();r=analyze(w.root);export=export_results(w.root)
    print(json.dumps({'run':str(w.root),'task_records':len(r['predictions']),'reviewed_results':r['reviewed_results'],
                      'TSR':'requires human review; no automatic success labels','export':export},indent=2))

if __name__=='__main__':main()
