#!/usr/bin/env python3
"""Continuation entry point shipped inside the handover; notebook stays primary."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from trustdesc.reproduction.session import Session

if __name__ == '__main__':
    session = Session(ROOT, ROOT.parent/'automatic-rerun')
    print(session.run_all())
