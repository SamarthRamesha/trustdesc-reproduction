#!/usr/bin/env python3
"""Mac/CPU notebook entry point, with no model imports during startup smoke."""
from pathlib import Path
import argparse
import json
import sys
import traceback
import os
import platform
import subprocess
import shutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--preflight-only',action='store_true')
    args=parser.parse_args()
    args.workspace.mkdir(parents=True,exist_ok=True)
    from trustdesc.reproduction.startup import startup_smoke, launch_environment
    startup=startup_smoke(repeats=3,env=launch_environment())
    (args.workspace/'python_startup.json').write_text(json.dumps(startup,indent=2)+'\n')
    if not startup['passed']:
        raise RuntimeError('Python startup failed; inference is blocked. Inspect python_startup.json.')
    if args.preflight_only:
        print('Python-only startup: passed; no inference libraries imported.',flush=True)
        return 0
    from trustdesc.reproduction.session import Session
    session=Session(ROOT,args.workspace/'experiment')
    try:
        for label,operation in [('acquisition',session.acquire),('model qualification',session.initialize_model),
                                ('SliceMin',session.workflow.static),('DescGen',session.workflow.descriptions),
                                ('DynVer',session.workflow.verification),('matched evaluation',session.workflow.benchmark)]:
            print('Starting '+label,flush=True)
            operation()
            print('Recorded '+label+'; inspect saved stage status for success/failure.',flush=True)
        test_log=args.workspace/'software-tests.txt'
        with test_log.open('w') as stream:
            tested=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-t','.'],cwd=ROOT,
                                  env={**os.environ,'PYTHONPATH':str(ROOT/'src')},stdout=stream,stderr=subprocess.STDOUT)
        session.store.text('software_tests.txt',test_log.read_text())
        session.store.write('software_test_status.json',{'returncode':tested.returncode,'scope':'software tests, not research labels'})
        if tested.returncode:
            session.failures.append({'component':'software_tests','status':'failed','reason':'See software_tests.txt'})
        exported=session.finish()
        # The public study reloads the SAME model only after the main worker
        # exits. It is a separate dataset/scope and never enters fixture metrics.
        session.close()
        public_status={'status':'not_run','reason':'macOS Seatbelt unavailable or public source absent'}
        if platform.system()=='Darwin' and (ROOT/'data/public_example/server.py').exists():
            public_log=args.workspace/'public-example.txt'
            with public_log.open('w') as stream:
                public=subprocess.run([sys.executable,'-u',str(ROOT/'scripts/run_public_example.py'),
                                       '--workspace',str(args.workspace/'public-example'),
                                       '--cache',str(session.workspace/'cache/models')],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            session.store.text('supplementary/public-example-log.txt',public_log.read_text())
            public_status={'status':'experiment_finished' if public.returncode==0 else 'failed','returncode':public.returncode,
                           'scope':'public SDK function body; separate from authored benchmark and original MCP transport'}
            for run in sorted((args.workspace/'public-example').glob('public-example-*')):
                results_file=run/'results.json'
                if results_file.exists():public_status['conditions']=json.loads(results_file.read_text()).get('conditions')
                index=run/'OUTPUT_INDEX.json'
                if index.exists():
                    for name in json.loads(index.read_text()):
                        path=run/name
                        if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(run.resolve()):
                            session.store.text(Path('supplementary')/run.name/name,path.read_text())
        session.store.write('supplementary_public_example_status.json',public_status)
        final_report=session.run_root/'FINAL_PROJECT_COMPLETION_REPORT.md'
        session.store.text(final_report.name,final_report.read_text()+'\n## Supplementary public study\n\n'+json.dumps(public_status,indent=2)+'\n')
        # Preserve the initial fixture-only export before adding the supplement.
        shutil.copy2(exported['archive'],Path(exported['archive']).with_name('fixture_only_handover.zip'))
        from trustdesc.reproduction.report import validate_and_package
        exported=validate_and_package(session.workflow,Path(exported['archive']).parent)
        result={'run_root':str(session.run_root),'archive':exported['archive'],
                'checksum_file':exported['checksum_file'],'phase2_scientific_complete':False,'public_example':public_status}
        (args.workspace/'latest_run.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2),flush=True)
        return 0
    except BaseException:
        (args.workspace/'pipeline_traceback.txt').write_text(traceback.format_exc())
        raise
    finally:
        session.close()


if __name__=='__main__':
    raise SystemExit(main())
