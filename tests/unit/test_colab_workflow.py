import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import types

from trustdesc.common.io import ValidationError
from trustdesc.experiments.data import builtin_dataset,supplied_bundle
from trustdesc.experiments.workflow import Workflow
from trustdesc.experiments.models import ModelPool,cost_preview
from trustdesc.experiments.report import analyze
from trustdesc.experiments.review import submit_review
from trustdesc.experiments.storage import Store
from trustdesc.experiments.export import export_results,restore_results
from trustdesc.experiments.setup import prepare_inputs,extract_resource_bundle
from trustdesc.sandbox.runner import ControlledAgent

PROJECT=Path(__file__).resolve().parents[2]
RUNTIME={'python':'test-version','machine':'test-cpu','gpus':[],'packages':{}}


class ColabWorkflowTests(unittest.TestCase):
    def test_failed_model_load_does_not_poison_previous_model_cache(self):
        runtime={'gpus':[{'name':'test','total_bytes':40*1024**3,'free_bytes':40*1024**3}]}
        cfg={'id':'a','provider':'transformers','model_id':'test/a','revision':'abcdef0','max_calls':10}
        other={**cfg,'id':'b','model_id':'test/b'}
        pool=ModelPool(Store(self.base/'cache-pool'),runtime,allow_download=True)
        fake=types.SimpleNamespace(model_id='test/a',mode='mocked_loading_test',audit=[])
        torch=types.SimpleNamespace(cuda=types.SimpleNamespace(empty_cache=lambda:None))
        with patch.dict('sys.modules',{'torch':torch}), patch('trustdesc.experiments.models.TransformersModel',side_effect=[fake,RuntimeError('simulated allocation failure'),fake]) as loader:
            pool.get(cfg,'descgen',self.bundle['tools'][0])
            with self.assertRaises(RuntimeError):pool.get(other,'descgen',self.bundle['tools'][0])
            recovered=pool.get(cfg,'descgen',self.bundle['tools'][0])
            self.assertEqual(recovered.model_id,'test/a');self.assertEqual(loader.call_count,3)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        self.bundle,self.roots=builtin_dataset(PROJECT,self.base/'inputs')
        self.cfg={'profile':'A','models':json.loads((PROJECT/'configs/colab_models.json').read_text())['models'][:1],
                  'agent_max_steps':6,'generate_reconstructed_tasks':False}
        self.plot=patch('trustdesc.experiments.report.make_plots',return_value=[{'status':'unit_test_no_plot'}]);self.plot.start()
    def tearDown(self):self.plot.stop();self.tmp.cleanup()
    def workflow(self,**kwargs):return Workflow(PROJECT,self.base/'run',self.cfg,self.bundle,self.roots,RUNTIME,**kwargs)
    def execute(self):
        w=self.workflow();pred=w.benchmark();return w,pred

    def test_all_tools_conditions_and_unreviewed_metrics(self):
        w,pred=self.execute();r=analyze(w.root)
        self.assertEqual(len(pred),24)
        self.assertEqual({x['variant'] for x in pred},{'original','lite','full'})
        self.assertEqual({x['tool_id'] for x in pred},{'apply_formula','normalize_name'})
        self.assertTrue(all(x['status']=='completed' and x['observed_target_invoked'] for x in pred))
        self.assertTrue(all(x['TSR_percent'] is None for x in r['conditions']))
        self.assertFalse(r['full_scientific_reproduction'])

    def test_actual_conditions_are_passed_to_agent(self):
        w,pred=self.execute()
        hashes={r['variant']:r['condition_descriptions_hash'] for r in pred if r['task_id']=='synthetic-001'}
        self.assertEqual(len(set(hashes.values())),3)

    def test_tsr_requires_objective_and_review_complete(self):
        w,pred=self.execute()
        for i,r in enumerate(pred):
            submit_review(w.root,r['result_id'],target_invoked=True,objective_achieved=(i!=0),reviewer='unit-test annotation',confirmed=True)
        result=analyze(w.root);original=next(s for s in result['conditions'] if s['variant']=='original')
        self.assertEqual(original['TSR_percent'],87.5)
        self.assertTrue(all(len(x['matched_successful_tasks'])==7 for x in result['overheads']))

    def test_one_missing_review_withholds_condition_metric(self):
        w,pred=self.execute()
        for r in pred[:-1]:submit_review(w.root,r['result_id'],target_invoked=True,objective_achieved=True,reviewer='unit-test',confirmed=True)
        result=analyze(w.root)
        self.assertIsNone(next(s for s in result['conditions'] if s['variant']=='full')['TSR_percent'])
        self.assertEqual(result['overheads'],[])

    def test_resume_reuses_completed_tasks_without_calls(self):
        w,_=self.execute();before=len(list((w.root/'calls').rglob('*.json')))
        resumed=self.workflow(resume=True);resumed.benchmark()
        self.assertEqual(len(list((w.root/'calls').rglob('*.json'))),before)

    def test_resume_requires_explicit_choice(self):
        self.execute()
        with self.assertRaises(ValidationError):self.workflow()

    def test_resume_rejects_changed_configuration(self):
        self.execute();self.cfg['agent_max_steps']=5
        with self.assertRaises(ValidationError):self.workflow(resume=True)

    def test_resume_rejects_changed_source(self):
        self.execute();p=self.roots['normalize_name']/'server.py';p.write_text(p.read_text()+'\nX=1\n')
        with self.assertRaises(ValidationError):self.workflow(resume=True)

    def test_resume_rejects_changed_dataset(self):
        self.execute();self.bundle['tasks'][0]['task']='Changed objective'
        with self.assertRaises(ValidationError):self.workflow(resume=True)

    def test_completed_checkpoint_corruption_rejected(self):
        store=Store(self.base/'checkpoint');store.job({'x':1},lambda:{'status':'completed','value':1})
        p=next((store.root/'checkpoints').rglob('result.json'));p.write_text('{}')
        with self.assertRaises(ValidationError):store.job({'x':1},lambda:{})

    def test_partial_interrupted_checkpoint_retries(self):
        store=Store(self.base/'checkpoint')
        def interrupt():raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):store.job({'x':1},interrupt)
        r=store.job({'x':1},lambda:{'value':2})
        self.assertEqual(r['value'],2)
        self.assertEqual(json.loads(next((store.root/'checkpoints').rglob('state.json')).read_text())['attempt'],2)

    def test_failed_checkpoint_is_preserved_until_explicit_retry(self):
        store=Store(self.base/'checkpoint')
        def fail():raise RuntimeError('controlled failure')
        self.assertEqual(store.job({'x':1},fail)['status'],'failed')
        self.assertEqual(store.job({'x':1},lambda:{'value':1})['status'],'failed')
        self.assertEqual(store.job({'x':1},lambda:{'value':1},retry_failed=True)['value'],1)

    def test_unavailable_provider_does_not_stop_replay(self):
        self.cfg['models'].append({'id':'not-approved','provider':'http','model_id':'explicit-test','endpoint':'https://example.com','max_calls':2})
        w,pred=self.execute()
        self.assertTrue(all(r['status']=='completed' for r in pred if r['model']=='replay'))
        self.assertTrue(all(not r.get('trace') for r in pred if r['model']=='not-approved'))
        r=analyze(w.root)
        self.assertTrue(all(s['TSR_percent'] is None and s['mean_cost_usd'] is None for s in r['conditions'] if s['model']=='not-approved'))

    def test_external_tool_is_never_executed(self):
        extra=copy.deepcopy(self.bundle['tools'][0]);extra.update(id='external',backend='disabled')
        self.bundle['tools'].append(extra)
        t=copy.deepcopy(self.bundle['tasks'][0]);t.update(id='external-task',tool_id='external',origin='reconstructed')
        self.bundle['tasks'].append(t)
        w,pred=self.execute()
        self.assertTrue(all(r['status']=='blocked' and not r.get('trace') for r in pred if r['tool_id']=='external'))

    def test_unvalidated_typescript_is_skipped(self):
        self.bundle['tools'][0]['language']='typescript'
        w=self.workflow();r=w.static()
        self.assertEqual(r['apply_formula']['status'],'unavailable')
        self.assertEqual(r['normalize_name']['status'],'completed')

    def test_model_cannot_inject_new_executable_tool_via_metadata(self):
        with self.assertRaises(ValidationError):ControlledAgent(None,tool_descriptions={'shell':{}})

    def test_human_review_requires_confirmation_and_matching_evidence(self):
        w,pred=self.execute();r=pred[0]
        with self.assertRaises(ValidationError):submit_review(w.root,r['result_id'],target_invoked=True,objective_achieved=True,reviewer='test')
        with self.assertRaises(ValidationError):submit_review(w.root,r['result_id'],target_invoked=True,objective_achieved=True,reviewer='test',confirmed=True,evidence_hash='wrong')

    def test_export_restore_and_resume(self):
        w,_=self.execute();analyze(w.root)
        result=export_results(w.root,self.base/'TRUSTDESC_COLAB_RESULTS.zip')
        restored=restore_results(result['archive'],result['sha256'],self.base/'restore')
        resumed=Workflow(PROJECT,restored,self.cfg,self.bundle,self.roots,RUNTIME,resume=True)
        before=len(list((restored/'calls').rglob('*.json')));resumed.benchmark()
        self.assertEqual(len(list((restored/'calls').rglob('*.json'))),before)

    def test_export_excludes_unregistered_personal_files(self):
        w,_=self.execute();(w.root/'personal.json').write_text('{"private":"not part of experiment"}')
        result=export_results(w.root,self.base/'export.zip')
        with zipfile.ZipFile(result['archive']) as z:self.assertNotIn('run/personal.json',z.namelist())

    def test_credentials_redacted_before_persistence_and_export(self):
        secret='sk-'+'A'*40;store=Store(self.base/'safe',secrets=[secret])
        store.write('EXPERIMENT_MANIFEST.json',{'run_id':'safe','fingerprint':'test'})
        store.write('error.json',{'error':'Failure with '+secret,'api_key':secret,secret:'credential echoed as a key'})
        self.assertNotIn(secret,(store.root/'error.json').read_text())
        result=export_results(store.root,self.base/'export.zip')
        with zipfile.ZipFile(result['archive']) as z:self.assertNotIn(secret.encode(),z.read('run/error.json'))

    def test_restore_rejects_bad_checksum_and_traversal(self):
        p=self.base/'bad.zip'
        with zipfile.ZipFile(p,'w') as z:z.writestr('../escape','bad')
        with self.assertRaises(ValidationError):restore_results(p,'wrong',self.base/'out')
        with self.assertRaises(ValidationError):restore_results(p,hashlib.sha256(p.read_bytes()).hexdigest(),self.base/'out')

    def test_paid_gate_and_defensible_cost_preview(self):
        cfg={'id':'paid','provider':'http','model_id':'explicit','endpoint':'https://example.com','max_calls':10,'max_new_tokens':100}
        self.assertIsNone(cost_preview(cfg)['planning_estimate_usd'])
        cfg['price_per_million']={'input':1,'output':2}
        self.assertAlmostEqual(cost_preview(cfg,assumed_input_tokens=100)['planning_estimate_usd'],.003)
        pool=ModelPool(Store(self.base/'pool'),RUNTIME)
        with self.assertRaises(RuntimeError):pool.get(cfg,'descgen',self.bundle['tools'][0])

    def test_failed_public_acquisition_preserves_cpu_inputs(self):
        with patch('trustdesc.experiments.setup.add_public_source',side_effect=OSError('offline')):
            bundle,roots,report=prepare_inputs(PROJECT,self.base/'offline',acquire_public=True)
        self.assertEqual(report['public_source'],'unavailable');self.assertEqual(len(bundle['tasks']),8)

    def test_original_candidate_not_fabricated(self):
        p=self.base/'bundle.json';p.write_text(json.dumps({'origin':'author_released','provenance':'test','tools':[],'tasks':[]}))
        with self.assertRaises(ValidationError):supplied_bundle(p)

    def test_resource_extractor_never_accepts_traversal(self):
        p=self.base/'bad.zip'
        with zipfile.ZipFile(p,'w') as z:z.writestr('../code.py','raise RuntimeError()')
        with self.assertRaises(ValidationError):extract_resource_bundle(p,hashlib.sha256(p.read_bytes()).hexdigest(),self.base/'source')
