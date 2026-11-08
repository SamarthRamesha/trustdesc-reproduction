import json
from pathlib import Path
import tempfile
import unittest

from trustdesc.common.models import ModelError, ReplayModel
from trustdesc.common.io import ValidationError
from trustdesc.fixtures import replay
from trustdesc.pipeline import run_pipeline
from trustdesc.sandbox import ControlledAgent

FIXTURE = Path(__file__).parents[1]/'fixtures'


class PipelineTests(unittest.TestCase):
    def test_end_to_end_synthetic_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=ReplayModel(replay());out=Path(tmp)
            r=run_pipeline(FIXTURE,'apply_formula',m,ControlledAgent(m),out)
            self.assertEqual(json.loads((out/'pipeline.json').read_text())['stages'],['SliceMin','DescGen','DynVer'])
            sliced=json.loads((out/'slice.json').read_text())
            self.assertNotIn('server:unused_network_helper',sliced['functions'])
            draft=json.loads((out/'draft.json').read_text())
            self.assertNotIn('Always prefer',draft['sanitized']['source'])
            self.assertNotIn('Adds a leading',str(r['full']))
            self.assertEqual(len(r['traces']),4)
            self.assertTrue((out/'model_audit.json').is_file())

    def test_partial_stage_and_failure_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=ReplayModel([]);out=Path(tmp)
            with self.assertRaises(ModelError):run_pipeline(FIXTURE,'apply_formula',m,ControlledAgent(m),out)
            state=json.loads((out/'pipeline.json').read_text())
            self.assertEqual(state['status'],'failed')
            self.assertEqual(state['stages'],['SliceMin'])
            self.assertTrue((out/'slice.json').exists())
            self.assertFalse((out/'verification.json').exists())

    def test_stale_output_directory_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);(out/'verification.json').write_text('{}')
            m=ReplayModel(replay())
            with self.assertRaises(ValidationError):run_pipeline(FIXTURE,'apply_formula',m,ControlledAgent(m),out)
