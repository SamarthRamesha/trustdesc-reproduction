import copy
import unittest

from trustdesc.common.io import ValidationError
from trustdesc.common.models import ReplayModel
from trustdesc.dynver import verify
from trustdesc.dynver.verify import validate_trace
from trustdesc.fixtures import DESCRIPTION, record, replay
from trustdesc.sandbox import ControlledAgent, DisabledRunner, SandboxError
from trustdesc.sandbox.fixture_tools import invoke
from trustdesc.sandbox.runner import docker_review_plan


def one_claim():
    d=copy.deepcopy(DESCRIPTION)
    d['functionalities']=[]
    d['input_schema']['properties']['formula'].pop('description')
    d['claims']=d['claims'][:1]
    return d


def plan_one():
    return record('verification_plan',{'tasks':[{'claim_id':'summary','verifiable':True,'task':'Try =1','reason':'Observe acceptance'}]})


class FixedRunner:
    def __init__(self, trace=None, error=None):self.trace,self.error=trace,error
    def run(self, task):
        if self.error:raise self.error
        return self.trace


def good_trace():
    return {'backend':'unit_test_trace','status':'completed','events':[{'tool':'apply_formula','arguments':{'formula':'=1'},'status':'ok','result':{'accepted_formula':'=1'}}]}


class VerificationTests(unittest.TestCase):
    def test_full_fixture_verification(self):
        m=ReplayModel(replay()[2:])
        r=verify(copy.deepcopy(DESCRIPTION),m,ControlledAgent(m))
        decisions={d['claim_id']:d['verdict'] for d in r['decisions']}
        self.assertEqual(decisions,{'summary':'supported','auto_prefix':'refuted','unsafe':'supported','internal':'not_runtime_verifiable','input':'supported'})
        self.assertEqual(r['full']['functionalities'],['Rejects HYPERLINK and INDIRECT formulas.'])
        self.assertNotIn('functionalities',r['lite'])
        self.assertEqual(r['lite']['input_schema'],r['full']['input_schema'])
        self.assertEqual(r['full']['claims'][1]['target'],['functionalities',0])
        self.assertEqual(r['trust_decision'],'not_assessed')

    def test_disabled_untrusted_execution(self):
        m=ReplayModel([plan_one()])
        r=verify(one_claim(),m,DisabledRunner())
        self.assertEqual(r['decisions'][0]['verdict'],'inconclusive')
        self.assertFalse(r['usable_summary'])

    def test_environment_errors_inconclusive(self):
        for status in ['timeout','dependency_error','sandbox_error','blocked','step_limit']:
            with self.subTest(status=status):
                r=verify(one_claim(),ReplayModel([plan_one()]),FixedRunner({'backend':'test','status':status,'events':[]}))
                self.assertEqual(r['decisions'][0]['verdict'],'inconclusive')

    def test_runner_failures_inconclusive(self):
        for exc in [SandboxError('fail'),TimeoutError('time'),ImportError('dependency')]:
            with self.subTest(error=type(exc).__name__):
                r=verify(one_claim(),ReplayModel([plan_one()]),FixedRunner(error=exc))
                self.assertEqual(r['decisions'][0]['verdict'],'inconclusive')

    def test_malformed_log_not_sent_to_judge(self):
        r=verify(one_claim(),ReplayModel([plan_one()]),FixedRunner({'status':'completed','events':'not logs'}))
        self.assertEqual(r['decisions'][0]['verdict'],'inconclusive')

    def test_unexpected_behavior_event_rejected(self):
        t=good_trace();t['events'][0]['status']='exfiltration'
        with self.assertRaises(ValidationError):validate_trace(t)

    def test_empty_success_log_insufficient(self):
        r=verify(one_claim(),ReplayModel([plan_one()]),FixedRunner({'backend':'test','status':'completed','events':[]}))
        self.assertEqual(r['decisions'][0]['verdict'],'inconclusive')

    def test_malformed_judge(self):
        m=ReplayModel([plan_one(),record('judge',{'verdict':'probably','reason':'unknown'})])
        with self.assertRaises(ValidationError):verify(one_claim(),m,FixedRunner(good_trace()))

    def test_plan_omitted_claim(self):
        with self.assertRaises(ValidationError):verify(one_claim(),ReplayModel([record('verification_plan',{'tasks':[]})]),DisabledRunner())

    def test_plan_duplicate_claim(self):
        p=plan_one();p['response']['tasks']*=2
        with self.assertRaises(ValidationError):verify(one_claim(),ReplayModel([p]),DisabledRunner())

    def test_nonverifiable_claim_removed(self):
        p=plan_one();p['response']['tasks'][0].update(verifiable=False,task=None)
        r=verify(one_claim(),ReplayModel([p]),DisabledRunner())
        self.assertEqual(r['decisions'][0]['verdict'],'not_runtime_verifiable')

    def test_agent_unknown_tool_blocked(self):
        m=ReplayModel([record('agent',{'action':'call','tool':'shell','arguments':{'command':'touch marker'}})])
        self.assertEqual(ControlledAgent(m).run('test')['status'],'blocked')

    def test_agent_step_limit(self):
        m=ReplayModel([record('agent',{'action':'call','tool':'apply_formula','arguments':{'formula':'=1'}})])
        self.assertEqual(ControlledAgent(m,max_steps=1).run('test')['status'],'step_limit')

    def test_observed_exception_type_is_preserved_for_judging(self):
        m=ReplayModel([record('agent',{'action':'call','tool':'apply_formula','arguments':{'formula':'SUM(A1:A5)'}}),
                       record('agent',{'action':'finish','answer':'Observed rejection.'})])
        trace=ControlledAgent(m,max_steps=2).run('Try the formula without a prefix.')
        self.assertEqual(trace['events'][0]['error_type'],'ValueError')
        self.assertEqual(trace['events'][0]['error'],'Formula must start with =')

    def test_agent_failure(self):
        self.assertEqual(ControlledAgent(ReplayModel([])).run('test')['status'],'agent_error')

    def test_bad_argument_does_not_execute_arbitrary_callable(self):
        with self.assertRaises(ValueError):invoke('apply_formula',{'formula':'=1','callback':'evil'})
        with self.assertRaises(ValueError):invoke('arbitrary',{})

    def test_formula_constraints(self):
        self.assertEqual(invoke('apply_formula',{'formula':'=1'})['accepted_formula'],'=1')
        for value in ['1','=INDIRECT("A1")','=hyperlink("x")']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):invoke('apply_formula',{'formula':value})

    def test_normalize_fixture(self):
        self.assertEqual(invoke('normalize_name',{'name':'  Alice '}),{'normalized':'alice'})

    def test_docker_plan_review_only_and_pinned(self):
        with self.assertRaises(ValidationError):docker_review_plan('python:latest')
        p=docker_review_plan('python@sha256:'+'a'*64)
        for required in ['--network=none','--read-only','--cap-drop=ALL','--pull=never']:
            self.assertIn(required,p)
