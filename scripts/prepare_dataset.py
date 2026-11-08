#!/usr/bin/env python3
"""Use `python scripts/prepare_dataset.py INPUT --output OUTPUT`."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from trustdesc.cli import main
if __name__=='__main__':main(['prepare',*sys.argv[1:]])
