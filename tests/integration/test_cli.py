import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from trustdesc.cli import main


class CLITests(unittest.TestCase):
    def test_demo_command(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['demo','--output',str(Path(tmp)/'demo')]),0)
            state=json.loads((Path(tmp)/'demo/pipeline.json').read_text())
            self.assertEqual(state['status'],'completed_with_reproduction_gaps')

    def test_cli_slice_failure_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:main(['slice',str(Path(tmp)/'missing'),'tool','--output',str(Path(tmp)/'out')])
            self.assertEqual(exc.exception.code,1)
