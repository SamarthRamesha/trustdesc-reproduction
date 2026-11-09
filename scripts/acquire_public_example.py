#!/usr/bin/env python3
"""Acquire the pinned MIT example as data; never import or execute downloads."""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args()
    spec=json.loads((ROOT/'data/manifests/public_example.json').read_text())
    with urllib.request.urlopen(spec['url'],timeout=30) as response:
        raw=response.read(100001)
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if len(raw)>100000 or hashlib.sha256(raw).hexdigest()!=spec['sha256'] or blob!=spec['git_blob_sha1']:
        raise RuntimeError('Public source does not match the pinned manifest')
    if args.destination.exists():
        raise RuntimeError('Preserve existing source: destination must be new')
    args.destination.parent.mkdir(parents=True,exist_ok=True)
    args.destination.write_bytes(raw)
    print(json.dumps({'acquired':str(args.destination),'manifest':spec,'executed':False},indent=2))


if __name__=='__main__':main()
