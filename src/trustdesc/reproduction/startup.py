"""Python-only launch checks. This module never imports an inference library."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys


def python_binary():
    """Use Homebrew's actual framework executable, avoiding its spawn launcher."""
    framework = (Path(sys.base_prefix)/'Resources/Python.app/Contents/MacOS/Python').resolve()
    return framework if framework.is_file() else Path(sys.executable).resolve()


def launch_environment():
    # No inherited DYLD_*, Python home/path, framework or library overrides.
    return {'PATH':'/usr/bin:/bin','LANG':'C','PYTHONDONTWRITEBYTECODE':'1'}


STARTUP_CODE = ('import json,os,platform,sys; print(json.dumps({"startup":"ok",'
                '"version":platform.python_version(),"machine":platform.machine(),'
                '"executable":sys.executable,"pid":os.getpid(),"ppid":os.getppid()}))')


def startup_smoke(executable=None, *, cwd=None, repeats=3, env=None, prefix=()):
    """Stop on the first failed startup; no retry of a crashing process."""
    binary = str(executable or python_binary())
    rows = []
    for index in range(repeats):
        command = [*map(str,prefix),binary,'-I','-S','-c',STARTUP_CODE]
        result = subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,timeout=8)
        row = {'attempt':index+1,'command':command,'cwd':str(Path(cwd or '.').resolve()),
               'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
        try:row['observation']=json.loads(result.stdout)
        except ValueError:row['observation']=None
        row['passed'] = result.returncode==0 and bool(row['observation']) and row['observation'].get('startup')=='ok'
        rows.append(row)
        if not row['passed']:
            break
    return {'passed':len(rows)==repeats and all(r['passed'] for r in rows),'attempts':rows,
            'retry_after_failure':False,'inference_imported':False}
