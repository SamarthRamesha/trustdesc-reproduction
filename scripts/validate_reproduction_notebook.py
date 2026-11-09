#!/usr/bin/env python3
"""Validate the preserved historical automatic Colab notebook with software fixtures.

Fixture injection is test-only. It never claims a Colab/T4/model experiment.
"""
from pathlib import Path
import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
import traceback
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--execute-fixture',action='store_true')
    parser.add_argument('--execute-missing-model',action='store_true')
    parser.add_argument('--remote-bootstrap',action='store_true',help='Fetch/verify pinned source in a fresh directory before importing project modules')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    nb=json.loads((ROOT/'notebooks/colab/TRUSTDESC_AUTOMATIC_COLAB.ipynb').read_text())
    ids=[c['id'] for c in nb['cells']]
    assert len(ids)==len(set(ids))
    codes=[c for c in nb['cells'] if c['cell_type']=='code']
    for cell in codes:
        assert cell['execution_count'] is None and cell['outputs']==[]
        compile(''.join(cell['source']),cell['id'],'exec')
    result={'compiled_cells':len(codes),'executed_cells':0,'actual_colab_session':False,'actual_T4_inference':False,
            'actual_external_MCP_execution':False,'model_inference':False,'validation_kind':'software_fixture_or_missing_model_only'}
    stream=io.StringIO()
    if args.execute_fixture or args.execute_missing_model:
        with tempfile.TemporaryDirectory(prefix='trustdesc-notebook-') as tmp:
            options={'project':ROOT,'workspace':str(Path(tmp)/'workspace'),'skip_install':True,'offline':True,'skip_tests':True}
            if args.remote_bootstrap:options.pop('project')
            if not args.execute_fixture:options['model_error']='Explicit missing-model recovery validation'
            scope={'_TRUSTDESC_VALIDATION':options}
            try:
                with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
                    for cell in codes:
                        exec(compile(''.join(cell['source']),cell['id'],'exec'),scope)
                        if cell['id']=='bootstrap' and args.execute_fixture:
                            sys.path.insert(0,str(scope['PROJECT']))
                            from tests.unit.test_reproduction import SoftwareValidationModel
                            options['model']=SoftwareValidationModel()
                        result['executed_cells']+=1
                session=scope['SESSION'];export=scope['EXPORT']
                assert session.results['phase2_complete'] is False
                assert len(session.results['task_results'])==24
                with zipfile.ZipFile(export['archive']) as z:
                    assert z.testzip() is None
                    assert 'run/PHASE2_COMPLETION_REPORT.md' in z.namelist()
                for name in ['PHASE2_COMPLETION_REPORT.md','PHASE3_HANDOVER.md','results.json','validation_report.json','acquisition_report.json','model_manifest.json','environment.json','EXPERIMENT_RESULTS.md']:
                    shutil.copy2(session.run_root/name,args.output/name)
                shutil.copy2(export['archive'],args.output/'phase3_handover.zip')
                shutil.copy2(export['checksum_file'],args.output/'phase3_handover.zip.sha256')
                result.update(task_records=24,zip_valid=True,model_mode=session.model_manifest.get('mode'),
                              remote_bootstrap=args.remote_bootstrap,source_revision=scope['SOURCE_REVISION'],
                              success_rates=[r['fixture_oracle_success_rate_percent'] for r in session.results['conditions'] if r['tool']=='ALL'])
            except BaseException:
                stream.write(traceback.format_exc())
                (args.output/'notebook_execution.txt').write_text(stream.getvalue())
                raise
    (args.output/'notebook_execution.txt').write_text(stream.getvalue())
    (args.output/'notebook_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
