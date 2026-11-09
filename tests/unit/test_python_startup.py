import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from trustdesc.reproduction.startup import startup_smoke, launch_environment
from trustdesc.sandbox.seatbelt import policy


class StartupTests(unittest.TestCase):
    def test_collection_format_repair_preserves_model_records_and_raw_failure(self):
        from trustdesc.reproduction.model import RepairModel
        from trustdesc.common.models import ModelError
        rows=[{'claim_id':'c1','references':[{'function':'server:tool'}],'rationale':'Model-generated rationale.'}]
        class RawArrayModel:
            model_id='software-test';mode='software_validation'
            audit=[]
            def complete(self,*args):
                self.audit.append({'raw_content':json.dumps(rows),'status':'failed','error':'Expected a JSON object'})
                raise ModelError('Expected a JSON object')
        raw=RawArrayModel();fixed=RepairModel(raw)
        self.assertEqual(fixed.complete('source_grounding','system',{}),{'evidence':rows})
        self.assertEqual(len(raw.audit),1)
        self.assertEqual(raw.audit[0]['status'],'failed')
        self.assertFalse(raw.audit[0]['format_normalization']['semantic_content_changed'])

    def test_model_data_download_includes_separate_chat_template(self):
        import fnmatch
        from trustdesc.reproduction.model import MODEL_FILE_PATTERNS
        self.assertTrue(any(fnmatch.fnmatch('chat_template.jinja',p) for p in MODEL_FILE_PATTERNS))
        self.assertFalse(any(fnmatch.fnmatch('modeling_remote.py',p) for p in MODEL_FILE_PATTERNS))

    def test_failed_startup_stops_before_another_launch(self):
        failed=subprocess.CompletedProcess([], -6, '', '')
        with patch('trustdesc.reproduction.startup.subprocess.run',return_value=failed) as run:
            result=startup_smoke(repeats=10)
        self.assertFalse(result['passed'])
        self.assertEqual(run.call_count,1)
        self.assertFalse(result['retry_after_failure'])

    def test_environment_drops_inherited_loader_overrides(self):
        with patch.dict('os.environ',{'DYLD_SHARED_CACHE_DIR':'bad','PYTHONHOME':'bad'}):
            environment=launch_environment()
        self.assertFalse(any(k.startswith(('DYLD_','PYTHONHOME','PYTHONPATH')) for k in environment))

    def test_seatbelt_root_exception_is_literal_not_recursive(self):
        profile=policy(Path(tempfile.gettempdir())/'trustdesc-test')
        self.assertIn('(allow file-read-data (literal "/")',profile)
        self.assertNotIn('(subpath "/")',profile)

    def test_native_worker_never_starts_after_python_failure(self):
        from trustdesc.reproduction.backends import ManagedModel
        from trustdesc.common.models import ModelError
        with patch('trustdesc.reproduction.startup.startup_smoke',return_value={'passed':False}),patch('multiprocessing.get_context') as context:
            with self.assertRaisesRegex(ModelError,'startup failed'):
                ManagedModel({'model_id':'never_load'},'/unused')
        context.assert_not_called()
