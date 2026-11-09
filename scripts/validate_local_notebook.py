#!/usr/bin/env python3
"""Execute the primary local notebook in order, with optional startup-only QA."""
from pathlib import Path
import argparse
import contextlib
import io
import json
import traceback

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--environment-only',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    notebook=json.loads((ROOT/'TRUSTDESC_REPRODUCTION.ipynb').read_text())
    codes=[c for c in notebook['cells'] if c['cell_type']=='code']
    for c in codes:compile(''.join(c['source']),c['id'],'exec')
    scope={'_TRUSTDESC_LOCAL_WORKSPACE':str(args.workspace.resolve())}
    result={'compiled_cells':len(codes),'executed_cells':[],
            'scope':'environment-only; no model' if args.environment_only else 'real local notebook execution'}
    with (args.output/'execution.txt').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        try:
            for c in codes:
                if args.environment_only and c['id'] not in {'bootstrap','environment'}:continue
                exec(compile(''.join(c['source']),c['id'],'exec'),scope)
                result['executed_cells'].append(c['id'])
            result['passed']=True
            if 'LATEST' in scope:result['run']=scope['LATEST']
        except BaseException:
            result.update(passed=False,traceback=traceback.format_exc())
            log.write(result['traceback'])
        finally:
            (args.output/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
