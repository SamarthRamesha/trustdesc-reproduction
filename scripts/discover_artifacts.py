#!/usr/bin/env python3
"""Repeat bounded public transport checks; HTTP 200 is not artifact authenticity."""
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import sys
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from trustdesc.common.io import dump, load
from trustdesc.common.models import NoRedirect

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--online',action='store_true',help='Public URL GET only, no authentication')
    p.add_argument('--output',type=Path,default=ROOT/'reports/discovery_checks.json')
    a=p.parse_args()
    urls=['https://arxiv.org/abs/2604.07536v1','https://splash-ye.github.io/',
          'https://anonymous.4open.science/r/ae-trustdesc-13A6/']
    urls += [r['source'] for r in load(ROOT/'data/manifests/paper_servers.json')]
    def check(url):
        if not a.online:return {'url':url,'status':'not_requested_offline','authenticity':'not_assessed'}
        try:
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
            req=urllib.request.Request(url,headers={'User-Agent':'trustdesc-public-research/0.1'})
            with opener.open(req,timeout=15) as r:
                body=r.read(250000)
                return {'url':url,'http_status':r.status,'bytes_sampled':len(body),
                        'status':'transport_response_only','authenticity':'not_assessed',
                        'warning':'Client-side app expiry/availability requires interactive verification.'}
        except Exception as e:return {'url':url,'status':'transport_failed','error_type':type(e).__name__,'error':str(e)}
    checks=list(ThreadPoolExecutor(max_workers=4).map(check,urls))
    dump(a.output,{'timestamp_utc':datetime.now(timezone.utc).isoformat(),'online':a.online,'checks':checks,
                   'prior_observation':'2026-11-08: interactive anonymous service reported repository expired; see evidence ledger.'})
    print(f'Saved {len(checks)} transport checks; no source executed.')

if __name__=='__main__':main()
