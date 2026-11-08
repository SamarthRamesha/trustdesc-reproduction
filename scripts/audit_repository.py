#!/usr/bin/env python3
"""Publication checks over tracked files and reachable Git history.

High-signal secret patterns only; reports names/locations, never matching values.
This complements review and does not guarantee absence of every possible secret.
No credentials, untracked raw artifacts, network or external code are accessed.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
PATTERNS={
    'GitHub token':re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})'),
    'AWS access key':re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'private key material':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'service API key':re.compile(rb'\bsk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{24,}'),
    'credential URL':re.compile(rb'https?://[^\s/:]+:[^\s/@]+@'),
    'literal credential assignment':re.compile(rb'''(?im)^\s*(?:export\s+)?(?:[A-Z_]*(?:API_KEY|SECRET_KEY|ACCESS_TOKEN|PASSWORD))\s*=\s*["']?[A-Za-z0-9_+/=-]{20,}'''),
}


def git(*args):
    return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=True).stdout


def audit():
    tracked=[x for x in git('ls-files','-z').decode().split('\0') if x]
    # Include newly prepared source/docs until the final staging/commit.
    untracked=[x for x in git('ls-files','--others','--exclude-standard','-z').decode().split('\0') if x]
    files=sorted(set(tracked+untracked))
    findings=[];links=[];syntax=[];json_count=0;largest=[]
    for name in files:
        p=ROOT/name
        if not p.is_file():
            findings.append({'kind':'nonregular_or_missing','path':name});continue
        data=p.read_bytes();largest.append((len(data),name))
        if any(x in {'.venv','.git','__pycache__'} for x in Path(name).parts) or name.startswith(('data/raw/','data/interim/','data/processed/','experiments/runs/')) or (Path(name).name.startswith('.env') and Path(name).name!='.env.example'):
            findings.append({'kind':'excluded_content_tracked','path':name})
        if len(data)>5_000_000:findings.append({'kind':'large_file','path':name,'bytes':len(data)})
        for label,pattern in PATTERNS.items():
            if pattern.search(data):findings.append({'kind':label,'path':name})
        if p.suffix=='.py':
            try:ast.parse(data.decode(),filename=name)
            except SyntaxError:syntax.append(name)
        if p.suffix in {'.json','.ipynb'}:
            json.loads(data);json_count+=1
        if p.suffix=='.md':
            for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',data.decode()):
                target=target.split(' "')[0].strip('<>')
                if not target.startswith(('https:','http:','#','mailto:')) and not (p.parent/target.split('#')[0]).exists():
                    links.append({'path':name,'target':target})
    historical=[];blobs=0
    for line in git('rev-list','--objects','--all').decode().splitlines():
        sha,*path=line.split(' ',1)
        if git('cat-file','-t',sha).strip()!=b'blob':continue
        blobs+=1;data=git('cat-file','blob',sha)
        for label,pattern in PATTERNS.items():
            if pattern.search(data):historical.append({'kind':label,'blob':sha,'path':path[0] if path else None})
    probes=['.env','.env.local','.env.example','.venv-audit/bin/python','data/raw/sample.zip','data/interim/source.py','experiments/runs/run.json','.ipynb_checkpoints/file','.cache/file','result.zip']
    ignored={n:subprocess.run(['git','check-ignore','--no-index','-q',n],cwd=ROOT).returncode==0 for n in probes}
    return {'checked_files':len(files),'historical_blobs_checked':blobs,'current_secret_or_content_findings':findings,
            'historical_secret_findings':historical,'secret_scan_scope':'tracked/new intended files and all reachable blob objects, high-signal patterns; manual review also required',
            'broken_local_document_links':links,'python_syntax_errors':syntax,'json_notebook_files_parsed':json_count,
            'ignore_probes':ignored,'largest_files':[{'path':n,'bytes':s} for s,n in sorted(largest,reverse=True)[:5]],
            'passed':not(findings or historical or links or syntax) and not ignored['.env.example'] and ignored['.env'] and ignored['.env.local']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    result=audit()
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
