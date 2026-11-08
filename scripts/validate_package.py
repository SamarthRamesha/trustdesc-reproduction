#!/usr/bin/env python3
"""Read-only package validation; no extracted source is imported."""
import argparse
import hashlib
import json
from pathlib import PurePosixPath
import zipfile

def validate(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(set(names))!=len(names):raise ValueError('Duplicate archive entries')
        for info in z.infolist():
            p=PurePosixPath(info.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in info.filename or ((info.external_attr>>16)&0o170000)==0o120000:
                raise ValueError('Unsafe archive entry')
        manifest=json.loads(z.read('trustdesc-reproduction/PORTABLE_MANIFEST.json'))
        expected={'trustdesc-reproduction/'+name for name in manifest['files']}|{'trustdesc-reproduction/PORTABLE_MANIFEST.json'}
        if set(names)!=expected:raise ValueError('Unexpected/missing archive members')
        for name,sha in manifest['files'].items():
            if hashlib.sha256(z.read('trustdesc-reproduction/'+name)).hexdigest()!=sha:raise ValueError('Member checksum mismatch')
    return {'files_validated':len(manifest['files']),'git_commit':manifest['git_commit']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive');a=p.parse_args();print(validate(a.archive))
