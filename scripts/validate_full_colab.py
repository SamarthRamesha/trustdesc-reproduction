#!/usr/bin/env python3
"""Compile the primary notebook and execute CPU cells in a disposable source copy.

No Colab GUI, credentials, paid model, weights or external server execution.
"""
from pathlib import Path
import argparse
import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import traceback

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--execute-cpu',action='store_true');p.add_argument('--output',type=Path)
    a=p.parse_args()
    nb=json.loads((ROOT/'notebooks/colab/TRUSTDESC_FULL_REPRODUCTION.ipynb').read_text())
    assert nb['nbformat']==4 and nb['nbformat_minor']>=5
    ids=[c['id'] for c in nb['cells']];assert len(ids)==len(set(ids))
    codes=[c for c in nb['cells'] if c['cell_type']=='code']
    for c in codes:
        assert c['execution_count'] is None and c['outputs']==[]
        compile(''.join(c['source']),c['id'],'exec')
    result={'compiled_python_cells':len(codes),'executed_cpu_cells':0,'actual_colab_session':False,
            'gpu_inference':False,'paid_calls':False,'credentials_used':False,'external_source_execution':False}
    log=io.StringIO()
    with tempfile.TemporaryDirectory(prefix='trustdesc-full-colab-validation-') as tmp:
        temp=Path(tmp)
        if a.execute_cpu:
            project=temp/'project'
            shutil.copytree(ROOT,project,ignore=shutil.ignore_patterns('.git','.venv*','__pycache__','raw','interim','processed','runs','*.egg-info','build','dist'))
            scope={'ROOT':project,'VALIDATION_OPTIONS':{'run_directory':str(temp/'validation-run'),'acquire_public':False,
                    'install_dependencies':False,'skip_review_ui':True,'skip_plot_display':True,'download_results':False}}
            try:
                with contextlib.redirect_stdout(log):
                    for c in codes:
                        if 'cpu' in c.get('metadata',{}).get('tags',[]):
                            exec(compile(''.join(c['source']),c['id'],'exec'),scope)
                            result['executed_cpu_cells']+=1
                run=scope['RUN_ROOT'];results=json.loads((run/'EXPERIMENT_RESULTS.json').read_text())
                required=['COLAB_EXPERIMENT_REPORT.md','EXPERIMENT_RESULTS.json','EXPERIMENT_MANIFEST.json',
                          'TASK_RESULTS.csv','TOOL_RESULTS.csv','METRICS_SUMMARY.csv','FAILURE_ANALYSIS.json']
                assert all((run/f).is_file() for f in required)
                assert len(results['predictions'])==24
                assert all(r['TSR_percent'] is None for r in results['conditions'])
                export=scope['EXPORT']
                assert hashlib.sha256(Path(export['archive']).read_bytes()).hexdigest()==export['sha256']
                result.update(task_records=24,tools=2,conditions=3,human_reviews=0,TSR_withheld_correctly=True,
                              export_integrity=True,registered_export_files=export['files'],
                              plot_status=json.loads((run/'plot_inventory.json').read_text()))
                if a.output:
                    evidence=a.output.parent/'cpu_example';evidence.mkdir(parents=True,exist_ok=True)
                    for f in required+['plot_inventory.json','REVIEW_TEMPLATE.csv']:
                        shutil.copy2(run/f,evidence/f)
                    if (run/'plots').exists():shutil.copytree(run/'plots',evidence/'plots',dirs_exist_ok=True)
            except Exception:
                log.write(traceback.format_exc())
                if a.output:
                    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.with_suffix('.txt').write_text(log.getvalue())
                raise
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
        a.output.with_suffix('.txt').write_text(log.getvalue())
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
