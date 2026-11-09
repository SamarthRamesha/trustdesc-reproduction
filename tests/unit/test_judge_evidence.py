import unittest
from trustdesc.dynver.verify import verify
from trustdesc.sandbox.fixture_tools import invoke


class JudgeEvidenceTests(unittest.TestCase):
    def test_judge_gets_actual_return_value_without_agent_fabrication(self):
        description={'summary':'Normalizes text.','functionalities':[],
                     'input_schema':{'type':'object','properties':{}},
                     'claims':[{'id':'c1','text':'Normalizes text.','target':['summary']}]}
        class Runner:
            def run(self,task):
                return {'backend':'software_test','status':'completed',
                        'events':[{'tool':'normalize_name','arguments':{'name':' Alice '},'status':'ok',
                                   'result':invoke('normalize_name',{'name':' Alice '})}],
                        'answer':'Invented transport and output fields must not reach the judge.'}
        seen=[]
        class Model:
            model_id='software-validation';mode='software_validation'
            def complete(self,stage,system,payload):
                if stage=='verification_plan':
                    return {'tasks':[{'claim_id':'c1','verifiable':True,'task':'Normalize the input.','reason':'Observe actual text output.'}]}
                seen.append(payload)
                return {'verdict':'supported','reason':'Software test response, not research evidence.'}
        verify(description,Model(),Runner())
        self.assertNotIn('answer',seen[0]['execution'])
        self.assertEqual(seen[0]['execution']['events'][0]['result'],{'normalized':'alice'})
