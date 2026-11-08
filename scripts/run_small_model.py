#!/usr/bin/env python3
"""User-run optional Colab experiment; never invoked during local preparation."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import os
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from trustdesc.common.io import dump, load
from trustdesc.common.transformers_model import TransformersModel
from trustdesc.descgen import generate
from trustdesc.pipeline import run_pipeline
from trustdesc.sandbox import ControlledAgent
from trustdesc.slicemin import PythonSlicer

def main():
    p=argparse.ArgumentParser(description='Optional GPU small-model inference on synthetic fixture only')
    p.add_argument('--allow-download',action='store_true')
    p.add_argument('--stage',choices=['description','pipeline'],default='description')
    p.add_argument('--debloat',action='store_true',help='Also attempt model-guided SliceMin; rewrites remain unproven')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    cfg=load(ROOT/'configs/small_model.json')
    if a.output.exists() and any(a.output.iterdir()):raise ValueError('Output directory must be fresh')
    a.output.mkdir(parents=True,exist_ok=True)
    model=None;status='not_started'
    try:
        model=TransformersModel(allow_download=a.allow_download,revision=cfg['revision'],seed=cfg['seed'],
                                max_input_tokens=cfg['max_input_tokens'],max_new_tokens=cfg['max_new_tokens'])
        if a.stage=='pipeline':
            run_pipeline(ROOT/'tests/fixtures','apply_formula',model,ControlledAgent(model),a.output/'pipeline',
                         debloat_model=model if a.debloat else None)
        else:
            sliced=PythonSlicer(ROOT/'tests/fixtures').slice('apply_formula',model=model if a.debloat else None)
            dump(a.output/'slice.json',sliced)
            dump(a.output/'draft.json',generate(sliced,model))
        status='completed_exploratory_only'
    except Exception as e:
        status='failed';dump(a.output/'error.json',{'type':type(e).__name__,'message':str(e)})
        raise
    finally:
        dump(a.output/'audit.json',getattr(model,'audit',[]))
        dump(a.output/'run.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
             'status':status,'config':cfg,'runtime':getattr(model,'runtime',None),
             'original_reproduction':False,'model_download_opted_in':a.allow_download})

if __name__=='__main__':main()
