#!/usr/bin/env python3
"""Validate notebook structure/compile cells, optionally execute portable cells.

Never execute upload/download/GPU/export cells during local validation.
"""
from pathlib import Path
import argparse
import json
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--execute-portable',action='store_true');a=p.parse_args()
    notebook=json.loads((ROOT/'notebooks/colab/phase1_handover.ipynb').read_text())
    assert notebook['nbformat']==4 and notebook['nbformat_minor']>=5
    codes=[c for c in notebook['cells'] if c['cell_type']=='code']
    ids=[c['id'] for c in notebook['cells']];assert len(ids)==len(set(ids))
    for i,c in enumerate(codes):
        assert c['execution_count'] is None and c['outputs']==[]
        compile(''.join(c['source']),f'notebook-cell-{i}','exec')
    count=0
    with tempfile.TemporaryDirectory() as tmp:
        scope={'ROOT':ROOT,'RUN_ROOT':Path(tmp)}
        if a.execute_portable:
            for c in codes:
                if 'portable' in c.get('metadata',{}).get('tags',[]):
                    exec(compile(''.join(c['source']),c['id'],'exec'),scope)
                    count+=1
    print(json.dumps({'compiled_code_cells':len(codes),'executed_portable_cells':count,
                      'colab_session_run':False,'gpu_inference_run':False}))

if __name__=='__main__':main()
