#!/usr/bin/env python3
"""Run model-free startup comparisons; suitable for Codex and native Terminal."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from trustdesc.reproduction.startup import startup_smoke, python_binary, launch_environment
from trustdesc.sandbox.seatbelt import SeatbeltPython


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--context',choices=['codex','terminal'],required=True)
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    relevant={k:v for k,v in os.environ.items() if k.startswith(('DYLD_','PYTHON')) or k in {'PATH','LIBRARY_PATH','LD_LIBRARY_PATH','VIRTUAL_ENV','TERM_PROGRAM'}}
    result={'context':args.context,'parent_pid':os.getppid(),'controller_pid':os.getpid(),
            'executable':str(python_binary()),'cwd':str(Path.cwd()),'environment':relevant,
            'controller_parent':subprocess.run(['ps','-p',str(os.getppid()),'-o','pid,ppid,comm'],capture_output=True,text=True).stdout,
            'direct_inherited':startup_smoke(repeats=10),
            'direct_clean':startup_smoke(repeats=10,env=launch_environment())}
    if result['direct_inherited']['passed'] and result['direct_clean']['passed']:
        boundary=SeatbeltPython(args.output.parent/'scratch')
        result['seatbelt_probe']=boundary.probe()
        result['seatbelt_startup']=boundary.startup_result
    result['passed']=all(result.get(key,{}).get('passed',False) for key in ['direct_inherited','direct_clean','seatbelt_probe','seatbelt_startup'])
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['context','executable','passed']},indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
