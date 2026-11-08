import ast
from pathlib import Path
import tempfile
import unittest

from trustdesc.common.models import ReplayModel
from trustdesc.slicemin import PythonSlicer, SliceError


class SliceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self): self.tmp.cleanup()

    def write(self, text, name='server.py'):
        p = self.root/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def test_nested_helper_reachability_excludes_unused(self):
        self.write('@mcp.tool()\ndef run(x): return a(x)\ndef a(x): return b(x)\ndef b(x): return x\ndef unused(): pass')
        result = PythonSlicer(self.root).slice('run')
        self.assertEqual(result['functions'], ['server:a', 'server:b', 'server:run'])
        self.assertNotIn('def unused', result['source'])
        self.assertEqual(result['mode'], 'static_only_no_debloating')

    def test_cycle_terminates(self):
        self.write('@tool\ndef a(): return b()\ndef b(): return a()')
        r = PythonSlicer(self.root).slice('a')
        self.assertEqual(len(r['edges']), 2)

    def test_all_callers_and_sites_preserved(self):
        self.write('@tool()\ndef run(): return a()+b()\ndef a(): return c(1)\ndef b(): return c(2)\ndef c(x): return x')
        r = PythonSlicer(self.root).slice('run')
        self.assertEqual(len([e for e in r['edges'] if e['callee'] == 'server:c']), 2)

    def test_decorator_name_override(self):
        self.write('@mcp.tool(name="exposed")\ndef internal(): return 1')
        self.assertEqual(PythonSlicer(self.root).slice('exposed')['entry'], 'server:internal')

    def test_explicit_registration(self):
        self.write('def handle(x): return x\nserver.registerTool("run", {}, handle)')
        self.assertEqual(PythonSlicer(self.root).slice('run')['entry'], 'server:handle')

    def test_cross_module_alias(self):
        self.write('from helpers import compute as c\n@tool()\ndef run(x): return c(x)')
        self.write('def compute(x): return x+1', 'helpers.py')
        self.assertIn('helpers:compute', PythonSlicer(self.root).slice('run')['functions'])

    def test_relative_import(self):
        self.write('from .helpers import compute\n@tool()\ndef run(x): return compute(x)', 'pkg/server.py')
        self.write('def compute(x): return x', 'pkg/helpers.py')
        self.assertIn('pkg.helpers:compute', PythonSlicer(self.root).slice('run')['functions'])

    def test_module_import(self):
        self.write('import helpers as h\n@tool()\ndef run(x): return h.compute(x)')
        self.write('def compute(x): return x', 'helpers.py')
        self.assertIn('helpers:compute', PythonSlicer(self.root).slice('run')['functions'])

    def test_external_and_dynamic_calls_recorded(self):
        self.write('@tool()\ndef run(fn): return print(fn())')
        r = PythonSlicer(self.root).slice('run')
        self.assertEqual({x['expression'] for x in r['unresolved_calls']}, {'print', 'fn'})

    def test_no_import_side_effect(self):
        marker = self.root/'marker'
        self.write(f'open({str(marker)!r},"w").write("bad")\n@tool()\ndef run(): return 1')
        PythonSlicer(self.root).slice('run')
        self.assertFalse(marker.exists())

    def test_constants_retained_as_context(self):
        self.write('LIMIT=3\n@tool()\ndef run(): return LIMIT')
        self.assertIn('LIMIT = 3', PythonSlicer(self.root).slice('run')['source'])

    def test_syntax_error(self):
        self.write('def bad(:')
        with self.assertRaises(SliceError): PythonSlicer(self.root)

    def test_missing_root(self):
        with self.assertRaises(SliceError): PythonSlicer(self.root/'missing')

    def test_missing_source_and_typescript(self):
        (self.root/'server.ts').write_text('function test() {}')
        with self.assertRaises(SliceError): PythonSlicer(self.root)

    def test_ambiguous_entry(self):
        self.write('@tool(name="run")\ndef a(): pass\n@tool(name="run")\ndef b(): pass')
        with self.assertRaises(SliceError): PythonSlicer(self.root).slice('run')

    def test_dispatch_requires_reviewed_override(self):
        self.write('def call_tool(name):\n if name=="run": return handle()\ndef handle(): return 1')
        s = PythonSlicer(self.root)
        with self.assertRaises(SliceError): s.slice('run')
        self.assertEqual(s.slice('run', explicit_entry='server:call_tool')['entry'], 'server:call_tool')

    def test_symbol_redefinition_rejected(self):
        self.write('def run(): pass\ndef run(): pass')
        with self.assertRaises(SliceError): PythonSlicer(self.root)

    def test_symlink_outside_root_rejected(self):
        (self.root/'link.py').symlink_to(Path(__file__).resolve())
        with self.assertRaises(SliceError): PythonSlicer(self.root)

    def test_resource_limit(self):
        self.write('def f(): pass')
        with self.assertRaises(SliceError): PythonSlicer(self.root, max_bytes=1)

    def test_llm_context_rewrite_and_graph_reconnect(self):
        self.write('@tool()\ndef run(): return helper()\ndef helper():\n if False: return unused()\n return 1\ndef unused(): return 2')
        s = PythonSlicer(self.root)
        # Alphabetical node order: helper, run, unused; then helper, run.
        responses = []
        for key in ['server:helper', 'server:run', 'server:unused', 'server:helper', 'server:run']:
            source = 'def helper():\n return 1' if key.endswith(':helper') else ast.unparse(s.functions[key].node)
            responses.append({'stage': 'debloat', 'response': {'source': source, 'rationale': 'Remove literal false branch only.'}})
        model = ReplayModel(responses)
        r = s.slice('run', model=model)
        self.assertTrue(r['converged'])
        self.assertNotIn('server:unused', r['functions'])
        self.assertIn('server:unused', r['initial_functions'])
        self.assertEqual(len(r['revisions']), 1)
        helper_request = model.audit[0]['payload']
        self.assertEqual(helper_request['callsites'][0]['callsite'], 'helper()')

    def test_llm_signature_change_rejected(self):
        self.write('@tool()\ndef run(x): return x')
        m = ReplayModel([{'stage':'debloat','response':{'source':'def run(): return 1','rationale':'bad'}}])
        with self.assertRaises(SliceError): PythonSlicer(self.root).slice('run', model=m)

    def test_llm_malformed_rewrite_rejected(self):
        self.write('@tool()\ndef run(x): return x')
        m = ReplayModel([{'stage':'debloat','response':{'source':'def :','rationale':'bad'}}])
        with self.assertRaises(SliceError): PythonSlicer(self.root).slice('run', model=m)

    def test_llm_added_top_level_execution_rejected(self):
        self.write('@tool()\ndef run(x): return x')
        m = ReplayModel([{'stage':'debloat','response':{'source':'import os\ndef run(x): return x','rationale':'bad'}}])
        with self.assertRaises(SliceError): PythonSlicer(self.root).slice('run', model=m)
