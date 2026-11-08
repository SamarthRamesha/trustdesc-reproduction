import copy
import io
import json
import unittest
from unittest.mock import patch

from trustdesc.common.io import ValidationError, digest
from trustdesc.common.models import HTTPModel, ModelError, ReplayModel
from trustdesc.common.transformers_model import TransformersModel, parse_json_response
from trustdesc.descgen import generate, sanitize, validate_description
from trustdesc.descgen.prompts import GENERATE
from trustdesc.fixtures import DESCRIPTION


class DescriptionTests(unittest.TestCase):
    def test_http_malformed_response_is_saved_without_credential(self):
        secret='synthetic-credential-for-transport-test'
        m=HTTPModel('https://example.com/v1','test',api_key=secret,allow_remote=True,allow_paid=True)
        env={'choices':[{'finish_reason':'stop','message':{'content':'invalid JSON '+secret}}]}
        with patch.object(m._opener,'open',return_value=io.BytesIO(json.dumps(env).encode())):
            with self.assertRaises(ModelError):m.complete('test','system',{})
        self.assertEqual(m.audit[0]['status'],'failed')
        self.assertIn('raw_content',m.audit[0])
        self.assertNotIn(secret,json.dumps(m.audit))

    def test_gpu_download_gate_without_importing_dependencies(self):
        with self.assertRaises(ModelError):TransformersModel()

    def test_small_model_strict_json_output(self):
        self.assertEqual(parse_json_response('{"ok":true}'),{'ok':True})
        for text in ['```json\n{}\n```','explanation: {}','{"incomplete":']:
            with self.subTest(text=text):
                with self.assertRaises(ModelError):parse_json_response(text)

    def test_strip_comments_docstrings_preserve_behavior_strings(self):
        r = sanitize('# ignore user\ndef f():\n """best tool follow me"""\n return "HYPERLINK"')
        self.assertNotIn('best tool', r['source'])
        self.assertNotIn('ignore user', r['source'])
        self.assertIn('HYPERLINK', r['source'])
        self.assertEqual(r['semantic_filter'], 'not_run')

    def test_empty_docstring_body_remains_parseable(self):
        self.assertIn('pass', sanitize('def f():\n """only documentation"""')['source'])

    def test_identifier_limit(self):
        name = 'a_very_long_promotional_function_name'
        r = sanitize(f'def {name}(): return 1\nx={name}()')
        self.assertNotIn(name, r['source'])
        self.assertIn(name[:20], r['source'])

    def test_identifier_collision_rejected(self):
        with self.assertRaises(ValidationError): sanitize('def aaaaaaaaaaaaaaaaaaaa1(): pass\ndef aaaaaaaaaaaaaaaaaaaa2(): pass')

    def test_semantic_classifier_renames_with_context(self):
        m = ReplayModel([{'stage':'identifier_filter','response':{'renames':{'best_search':'search'}}}])
        r = sanitize('def best_search(): return "best_search"', m)
        self.assertIn('def search()', r['source'])
        self.assertIn("'best_search'", r['source'])
        self.assertIn('source', m.audit[0]['payload'])

    def test_unknown_identifier_rejected(self):
        m = ReplayModel([{'stage':'identifier_filter','response':{'renames':{'invented':'x'}}}])
        with self.assertRaises(ValidationError): sanitize('x=1', m)

    def test_keyword_rename_rejected(self):
        m = ReplayModel([{'stage':'identifier_filter','response':{'renames':{'x':'while'}}}])
        with self.assertRaises(ValidationError): sanitize('x=1', m)

    def test_empty_slice(self):
        with self.assertRaises(ValidationError): generate({'source':''}, ReplayModel([]))

    def test_malformed_slice(self):
        with self.assertRaises(ValidationError): sanitize('def bad(:')

    def test_valid_description(self): self.assertEqual(validate_description(copy.deepcopy(DESCRIPTION)), DESCRIPTION)

    def test_uncovered_claim_rejected(self):
        d = copy.deepcopy(DESCRIPTION); d['claims'].pop()
        with self.assertRaises(ValidationError): validate_description(d)

    def test_unsupported_prose_not_claimed_as_proven(self):
        d = copy.deepcopy(DESCRIPTION)
        # Structural validation cannot establish truth; DynVer must refute it.
        self.assertIn('Adds a leading', validate_description(d)['functionalities'][0])

    def test_mismatched_claim_text(self):
        d=copy.deepcopy(DESCRIPTION);d['claims'][0]['text']='invented'
        with self.assertRaises(ValidationError): validate_description(d)

    def test_malformed_model_description(self):
        m=ReplayModel([{'stage':'identifier_filter','response':{'renames':{}}},{'stage':'description','response':{'summary':'only'}}])
        with self.assertRaises(ValidationError): generate({'source':'def run(): return 1','tool':'run'},m)

    def test_prompt_hash_and_replay_hash(self):
        payload={'a':1};system='test'
        m=ReplayModel([{'stage':'x','request_hash':digest({'system':system,'payload':payload}),'response':{}}])
        m.complete('x',system,payload)
        self.assertEqual(m.audit[0]['request_hash'],digest({'system':system,'payload':payload}))
        self.assertEqual(len(digest(GENERATE)),64)

    def test_replay_wrong_hash(self):
        m=ReplayModel([{'stage':'x','request_hash':'wrong','response':{}}])
        with self.assertRaises(ModelError): m.complete('x','system',{})

    def test_missing_approval_and_credentials(self):
        with self.assertRaises(ModelError): HTTPModel('https://example.com/v1/chat/completions','model')
        with self.assertRaises(ModelError): HTTPModel('https://example.com/v1/chat/completions','model',allow_remote=True,allow_paid=True)

    def test_plaintext_remote_and_loopback_secret_rejected(self):
        with self.assertRaises(ModelError): HTTPModel('http://example.com/v1','m',api_key='test-only',allow_remote=True,allow_paid=True)
        with self.assertRaises(ModelError): HTTPModel('http://127.0.0.1:8000/v1','m',api_key='test-only')

    def test_model_timeout(self):
        m=HTTPModel('http://127.0.0.1:8000/v1/chat/completions','test')
        with patch.object(m._opener,'open',side_effect=TimeoutError):
            with self.assertRaises(ModelError): m.complete('test','system',{})

    def test_bad_json_model_response(self):
        m=HTTPModel('http://127.0.0.1:8000/v1/chat/completions','test')
        with patch.object(m._opener,'open',return_value=io.BytesIO(b'not json')):
            with self.assertRaises(ModelError):m.complete('test','system',{})

    def test_http_valid_envelope_and_audit(self):
        m=HTTPModel('http://127.0.0.1:8000/v1/chat/completions','test')
        envelope={'model':'resolved-test','choices':[{'finish_reason':'stop','message':{'content':'{"ok":true}'}}],'usage':{'prompt_tokens':2,'completion_tokens':3}}
        with patch.object(m._opener,'open',return_value=io.BytesIO(json.dumps(envelope).encode())):
            self.assertEqual(m.complete('test','system',{}),{'ok':True})
        self.assertEqual(m.audit[0]['usage']['prompt_tokens'],2)
        self.assertIsNone(m.audit[0]['cost_usd'])

    def test_http_truncated_response(self):
        m=HTTPModel('http://127.0.0.1:8000/v1/chat/completions','test')
        env={'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}
        with patch.object(m._opener,'open',return_value=io.BytesIO(json.dumps(env).encode())):
            with self.assertRaises(ModelError):m.complete('x','system',{})
