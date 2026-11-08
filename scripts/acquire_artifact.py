#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from trustdesc.dataset.acquire import acquire, inventory_zip

def main():
    p=argparse.ArgumentParser(description='Quarantine public bytes after checksum/license review. Never executes or extracts.')
    p.add_argument('url');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sha256',required=True);p.add_argument('--license-note',required=True)
    p.add_argument('--inventory-zip',action='store_true')
    a=p.parse_args();print(acquire(a.url,a.output,a.sha256,license_note=a.license_note))
    if a.inventory_zip:print(inventory_zip(a.output))

if __name__=='__main__':main()
