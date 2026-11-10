#!/usr/bin/env python3
"""Package tracked project files only, with deterministic ZIP entry metadata."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=ROOT.parent/'trustdesc-phase1.zip')
    a=p.parse_args()
    status=subprocess.run(['git','status','--porcelain'],cwd=ROOT,text=True,capture_output=True,check=True).stdout
    if status.strip():raise RuntimeError('Commit the intended project state before packaging')
    revision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
    tracked=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True).stdout.decode().split('\0')
    files={}
    for name in sorted(x for x in tracked if x):
        # Never package a previously built archive or its sidecar: the archive must not
        # contain itself, and a stale checksum inside the next archive would be misleading.
        if name.startswith(a.output.name) or Path(name).suffix == '.zip':
            continue
        parts=Path(name).parts
        if any(x in {'.git','.venv','__pycache__'} for x in parts) or ('.env' in parts) or name.startswith(('data/raw/','data/processed/','data/interim/','experiments/runs/')):
            raise RuntimeError(f'Restricted file tracked: {name}')
        path=ROOT/name
        if path.is_symlink() or not path.is_file():raise RuntimeError('Only regular tracked files can be packaged')
        files[name]=path.read_bytes()
    manifest={'schema_version':1,'git_commit':revision,'files':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()},
              'excluded':['.git','.venv','.env','raw external artifacts','private PDF','model weights','repeated ignored runs'],
              'note':'Git history stays in local repository; archive is a source snapshot.'}
    files['PORTABLE_MANIFEST.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo('trustdesc-reproduction/'+name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            archive.writestr(info,data)
    sha=hashlib.sha256(a.output.read_bytes()).hexdigest()
    a.output.with_suffix(a.output.suffix+'.sha256').write_text(f'{sha}  {a.output.name}\n')
    print(json.dumps({'archive':str(a.output),'sha256':sha,'files':len(files),'git_commit':revision}))

if __name__=='__main__':main()
