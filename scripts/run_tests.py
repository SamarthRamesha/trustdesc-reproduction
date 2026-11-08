#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import io
import platform
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from trustdesc.common.io import dump

def main():
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    text=stream.getvalue()
    (ROOT/'reports/test_output.txt').write_text(text)
    dump(ROOT/'reports/test_results.json',{'timestamp_utc':datetime.now(timezone.utc).isoformat(),
          'command':'PYTHONPATH=src .venv/bin/python scripts/run_tests.py','python':platform.python_version(),
          'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
          'skipped':result.skipped,'passing':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
          'success':result.wasSuccessful()})
    print(text)
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
