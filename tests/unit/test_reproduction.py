import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from trustdesc.common.io import ValidationError
from trustdesc.common.models import ModelError, ReplayModel
from trustdesc.experiments.data import builtin_dataset
from trustdesc.experiments.models import fixture_description
from trustdesc.experiments.storage import Store
from trustdesc.slicemin.research import ResearchSlicer
from trustdesc.reproduction.evidence import interface, check_schema, validate_evidence, iterative_verify, VerificationGuard, IdentifierGuard
from trustdesc.reproduction.model import json_object, check_asset
from trustdesc.reproduction.resources import fetch_cached, validate_bundle, acquire_references
from trustdesc.reproduction.report import aggregate, paired_overhead, wilson
from trustdesc.reproduction.session import Session, select_config
from trustdesc.reproduction.workflow import score_fixture
from trustdesc.sandbox.mcp_container import ContainerMCP, container_command
from trustdesc.sandbox.runner import ControlledAgent, SandboxError

PROJECT=Path(__file__).resolve().parents[2]


class SoftwareValidationModel:
    """Explicit scripted software tests only. Never a notebook default/model fallback."""
    model_id='scripted-software-test'
    mode='synthetic_replay_software_validation_only'
    def __init__(self):
        self.audit=[]

    def complete(self,stage,system,payload):
        self.audit.append({'stage':stage,'input_tokens':None,'output_tokens':None,'cost_usd':0.0})
        if stage=='debloat':return {'source':payload['source'],'rationale':'Test identity rewrite.'}
        if stage=='identifier_filter':return {'renames':{}}
        if stage=='description':
            name='apply_formula' if 'formula' in payload['code'] else 'normalize_name'
            value=fixture_description(name)
            if name=='apply_formula':
                # Exercise real refutation and correction with actual tool errors.
                value['functionalities']=value['functionalities'][:2]
                value['claims']=[c for c in value['claims'] if c['id']!='internal']
            return value
        if stage=='source_grounding':
            key=next(iter(payload['functions']))
            return {'evidence':[{'claim_id':c['id'],'references':[{'function':key,'quote':payload['functions'][key]['source']}],
                                 'rationale':'Scripted attribution for integration mechanics only.'} for c in payload['claims']]}
        if stage=='verification_plan':
            normal='name' in payload['description']['input_schema']['properties']
            return {'tasks':[{'claim_id':c['id'],'verifiable':True,'task':'Normalize the text " Alice ".' if normal else ('Try formula SUM(A1:A5) without a leading equals sign.' if c['text']=='Adds a leading = when omitted.' else 'Accept formula =SUM(A1:A5).'),
                              'reason':'Controlled authored case.'} for c in payload['description']['claims']]}
        if stage=='refinement':
            value=copy.deepcopy(payload['description'])
            for claim in value['claims']:
                if claim['text']=='Adds a leading = when omitted.':
                    claim['text']='Requires a leading =; missing prefixes are rejected.'
                    value['functionalities'][0]=claim['text']
            return value
        if stage=='judge':
            bad=payload['claim']['text']=='Adds a leading = when omitted.'
            return {'verdict':'refuted' if bad else 'supported','reason':'Software test expectation; not LLM semantic judging.'}
        if stage=='agent':
            if payload['observations']:return {'action':'finish','answer':'Observed authored fixture.'}
            task=payload['task']
            formulas={'Accept formula =SUM(A1:A5).':'=SUM(A1:A5)',
                      'Try formula SUM(A1:A5) without a leading equals sign.':'SUM(A1:A5)',
                      'Try formula =INDIRECT("A1").':'=INDIRECT("A1")',
                      'Try formula =HYPERLINK("x").':'=HYPERLINK("x")'}
            names={'Normalize the text " Alice ".':' Alice ','Normalize an empty string.':'',
                   'Normalize text containing only spaces.':'   ','Normalize "BOB".':'BOB'}
            return {'action':'call','tool':'apply_formula' if task in formulas else 'normalize_name',
                    'arguments':{'formula':formulas[task]} if task in formulas else {'name':names[task]}}
        raise AssertionError('Unexpected stage '+stage)


class ReproductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def slicer(self,text,extras=None):
        src=self.root/'source';src.mkdir(exist_ok=True)
        (src/'server.py').write_text(text)
        for name,value in (extras or {}).items():
            p=src/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value)
        return ResearchSlicer(src)

    def test_dispatch_callee_and_provenance(self):
        s=self.slicer('def call_tool(name):\n if name=="run": return helper()\ndef helper(): return 1')
        result=s.slice('run')
        self.assertEqual(result['entry'],'server:helper')
        self.assertEqual(result['entry_method'],'dispatch_callee_pattern')
        self.assertIn('file_sha256',result['evidence_spans']['server:helper'])

    def test_ambiguous_dispatch_fails_closed(self):
        s=self.slicer('def call_tool(name):\n if name=="run": return a()+b()\ndef a(): return 1\ndef b(): return 2')
        with self.assertRaises(ValidationError):s.slice('run')

    def test_lexical_nested_resolution(self):
        result=self.slicer('@tool\ndef run(x):\n def helper(y): return y+1\n return helper(x)').slice('run')
        self.assertIn('server:run.helper',result['functions'])

    def test_stable_function_alias(self):
        result=self.slicer('@tool\ndef run(x):\n alias=helper\n return alias(x)\ndef helper(x): return x').slice('run')
        self.assertIn('server:helper',result['functions'])

    def test_parameter_shadow_not_falsely_resolved(self):
        result=self.slicer('@tool\ndef run(helper): return helper()\ndef helper(): return 1').slice('run')
        self.assertNotIn('server:helper',result['functions'])
        self.assertEqual(result['unresolved_calls'][0]['expression'],'helper')

    def test_class_self_method(self):
        result=self.slicer('class Server:\n @tool(name="run")\n def run(self,x): return self.helper(x)\n def helper(self,x): return x\n def unused(self): return 9').slice('run')
        self.assertIn('server:Server.helper',result['functions'])
        self.assertNotIn('def unused',result['source'])

    def test_cross_file_reexport(self):
        result=self.slicer('from pkg import helper\n@tool\ndef run(): return helper()',{'pkg/__init__.py':'from .helpers import helper','pkg/helpers.py':'def helper(): return 1'}).slice('run')
        self.assertIn('pkg.helpers:helper',result['functions'])

    def test_source_not_executed(self):
        marker=self.root/'bad'
        self.slicer(f'open({str(marker)!r},"w").write("bad")\n@tool\ndef run(): return 1').slice('run')
        self.assertFalse(marker.exists())

    def test_schema_mismatch_rejected(self):
        sliced=self.slicer('@tool\ndef run(value:str,limit:int=3): return value').slice('run')
        signature=interface(sliced)
        with self.assertRaises(ValidationError):check_schema({'input_schema':{'properties':{'invented':{}},'required':[]}},signature)
        check_schema({'input_schema':{'properties':{'value':{'type':'string'},'limit':{'type':'integer'}},'required':['value']}},signature)

    def test_fabricated_source_quote_rejected(self):
        desc={'claims':[{'id':'one'}]}
        with self.assertRaises(ValidationError):validate_evidence({'evidence':[{'claim_id':'one','references':[{'function':'x','quote':'invented'}],'rationale':'test'}]},desc,{'x':{'source':'return 1'}})

    def test_safe_json_fences_and_invalid_text(self):
        self.assertEqual(json_object('```json\n{"x":1}\n```'),{'x':1})
        for bad in ['explanation {}','[]','{"x":NaN}']:
            with self.assertRaises(ModelError):json_object(bad)

    def test_invalid_plan_receives_actual_diagnostic(self):
        bad={'tasks':[{'claim_id':'c1','verifiable':False,'task':'invalid','reason':'test'}]}
        good={'tasks':[{'claim_id':'c1','verifiable':False,'task':None,'reason':'test'}]}
        model=ReplayModel([{'stage':'verification_plan','response':bad},{'stage':'verification_plan','response':good}])
        result=VerificationGuard(model).complete('verification_plan','prompt',{'description':{'claims':[{'id':'c1'}]}})
        self.assertIsNone(result['tasks'][0]['task'])
        self.assertIn('validation_error',model.audit[-1]['payload'])

    def test_identifier_collision_is_retried_not_accepted(self):
        model=ReplayModel([{'stage':'identifier_filter','response':{'renames':{'first':'same','second':'same'}}},
                           {'stage':'identifier_filter','response':{'renames':{}}}])
        result=IdentifierGuard(model).complete('identifier_filter','prompt',{'identifiers':['first','second'],'source':'def first(): pass'})
        self.assertEqual(result,{'renames':{}})
        self.assertIn('rejected_mapping',model.audit[-1]['payload'])

    def test_download_cache_and_corruption_recovery(self):
        raw=b'known public research bytes';sha=hashlib.sha256(raw).hexdigest()
        spec={'name':'test','url':'https://raw.githubusercontent.com/test/a','sha256':sha,'license':'MIT','version':'abc','classification':'public_reference'}
        def fake(url,output,expected_sha256,**kwargs):Path(output).write_bytes(raw)
        with patch('trustdesc.reproduction.resources.acquire',side_effect=fake) as downloader:
            path,first=fetch_cached(spec,self.root/'cache')
            _,second=fetch_cached(spec,self.root/'cache')
            self.assertFalse(first['cache_hit']);self.assertTrue(second['cache_hit'])
            self.assertEqual(downloader.call_count,1)
            path.write_bytes(b'corrupt');_,third=fetch_cached(spec,self.root/'cache')
            self.assertFalse(third['cache_hit']);self.assertEqual(downloader.call_count,2)
            self.assertEqual(len(list((self.root/'cache').glob('*.corrupt-*'))),1)

    def test_model_assets_checked_against_commit_metadata(self):
        path=self.root/'weights.safetensors';raw=b'known test bytes';path.write_bytes(raw)
        expected={'sha256':hashlib.sha256(raw).hexdigest(),'blob_id':None}
        self.assertTrue(check_asset(path,expected)['publisher_hash_verified'])
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()
        self.assertTrue(check_asset(path,{'blob_id':blob})['publisher_hash_verified'])
        path.write_bytes(b'corrupt')
        with self.assertRaises(ModelError):check_asset(path,expected)

    def test_missing_resources_leave_ledger(self):
        store=Store(self.root/'ledger')
        with patch('trustdesc.reproduction.resources.fetch_cached',side_effect=OSError('network missing')),patch('trustdesc.reproduction.resources.probe',return_value={'status':'unavailable'}):
            result=acquire_references(PROJECT,self.root/'cache',store)
        self.assertFalse(result['original_artifact_recovered'])
        self.assertTrue(any(r['status']=='unavailable_or_invalid' for r in result['resources']))

    def test_invalid_dataset_duplicate_task_rejected(self):
        bundle,roots=builtin_dataset(PROJECT,self.root/'inputs')
        bundle['tasks'].append(copy.deepcopy(bundle['tasks'][0]))
        with self.assertRaises(ValidationError):validate_bundle(bundle,roots)

    def test_container_permissions_and_pinning(self):
        with self.assertRaises(SandboxError):ContainerMCP({},execution_permitted=False)
        with self.assertRaises(ValidationError):container_command('python:latest',['python'],'trustdesc-'+'a'*32)
        command=container_command('python@sha256:'+'a'*64,['python','server.py'],'trustdesc-'+'a'*32)
        for flag in ['--network=none','--read-only','--cap-drop=ALL','--memory=512m','--pull=never']:
            self.assertIn(flag,command)
        self.assertFalse(any('mount' in a or 'volume' in a for a in command))

    def test_agent_cannot_call_omitted_tool(self):
        model=ReplayModel([{'stage':'agent','response':{'action':'call','tool':'normalize_name','arguments':{'name':'x'}}}])
        trace=ControlledAgent(model,tool_descriptions={'apply_formula':{}}).run('test')
        self.assertEqual(trace['status'],'blocked');self.assertEqual(trace['events'],[])

    def test_rates_withhold_missing_observations(self):
        record={'generator':'g','variant':'original','tool_id':'t','status':'unavailable','task_id':'a'}
        row=aggregate([record])[0]
        self.assertIsNone(row['fixture_oracle_success_rate_percent'])
        self.assertEqual(row['missing_tasks'],1)
        self.assertIsNone(wilson(0,0))

    def test_fixture_objective_observation_does_not_require_finish_message(self):
        task={'id':'synthetic-008','tool':'normalize_name','fixture_arguments':{'name':'BOB'}}
        trace={'status':'step_limit','events':[{'tool':'normalize_name','arguments':{'name':'BOB'},'status':'ok','result':{'normalized':'bob'}}]}
        score=score_fixture(task,trace)
        self.assertTrue(score['target_invoked'] and score['objective_observation'] and score['success'])
        self.assertFalse(score['agent_finished'])

    def test_overhead_only_common_success_intersection(self):
        records=[]
        for task in ['a','b']:
            for variant in ['original','lite','full']:
                records.append({'generator':'g','task_id':task,'variant':variant,'fixture_oracle':{'success':task=='a'},'latency_seconds':1 if variant=='original' else 2,'cost_usd':0})
        result=paired_overhead(records)
        self.assertEqual(result[0]['common_success_task_ids'],['a'])
        self.assertEqual(result[0]['relative_percent']['latency_seconds'],100)
        self.assertIsNone(result[0]['relative_percent']['cost_usd'])

    def test_hardware_selection_cpu_and_t4(self):
        runtime={'gpus':[],'ram_available_bytes':8*1024**3,'disk_free_bytes':20*1024**3,'python_supported':True}
        config,errors=select_config(PROJECT,runtime)
        self.assertEqual(config['hardware_selection'],'cpu');self.assertFalse(errors)
        runtime['gpus']=[{'name':'Tesla T4','free_bytes':14*1024**3}]
        config,errors=select_config(PROJECT,runtime)
        self.assertEqual(config['models'][0]['model_id'],'Qwen/Qwen2.5-Coder-1.5B-Instruct')
        self.assertEqual(config['models'][0],config['task_agent'])

    def test_entire_pipeline_zip_refinement_and_resume(self):
        model=SoftwareValidationModel()
        session=Session(PROJECT,self.root/'session',network=False,model=model)
        exported=session.run_all()
        results=session.results
        self.assertFalse(results['phase2_complete'])
        self.assertEqual(len(results['task_results']),24)
        self.assertTrue(all(r['fixture_oracle']['success'] for r in results['task_results']))
        verification=session.store.read('verification_results.json')
        formula=next(iter(verification.values()))['apply_formula']['verification']
        self.assertEqual(formula['refinement_rounds'],2)
        self.assertNotIn('Adds a leading',json.dumps(formula['full']))
        with zipfile.ZipFile(exported['archive']) as z:
            self.assertIsNone(z.testzip())
            self.assertIn('run/PHASE3_HANDOVER.md',z.namelist())
            self.assertTrue(any('reproduction_source/src/' in n for n in z.namelist()))
            self.assertIn('run/reproduction_source/data/manifests/acquired_sources.json',z.namelist())
            self.assertIn('run/reproduction_source/scripts/run_automatic_reproduction.py',z.namelist())
            self.assertIn('run/reproduction_source/README.md',z.namelist())
            self.assertIn('run/reproduction_source/requirements-apple-lock.txt',z.namelist())
            self.assertIn('run/reproduction_source/reports/published_results.csv',z.namelist())
        before=len(list((session.run_root/'calls').rglob('*.json')))
        resumed=Session(PROJECT,self.root/'session',network=False,model=SoftwareValidationModel())
        resumed.run_all()
        self.assertEqual(len(list((session.run_root/'calls').rglob('*.json'))),before)

    def test_missing_model_does_not_replay_scientific_stages(self):
        session=Session(PROJECT,self.root/'missing',network=False,model_error='simulated unavailable weights')
        session.run_all()
        self.assertTrue(all(r['fixture_oracle_success_rate_percent'] is None for r in session.results['conditions']))
        self.assertFalse((session.run_root/'calls').exists())
        self.assertTrue((session.run_root/'PHASE2_COMPLETION_REPORT.md').exists())


if __name__=='__main__':unittest.main()
