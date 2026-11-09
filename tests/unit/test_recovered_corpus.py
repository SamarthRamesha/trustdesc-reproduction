"""Regression tests for static discovery of recovered public tool registrations.

The recovered source trees are not tracked, so these tests exercise the four
observed registration styles on synthetic look-alikes and must never execute
inspected source.
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'build_recovered_benchmark', ROOT / 'scripts/build_recovered_benchmark.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RecoveredDiscoveryTests(unittest.TestCase):
    def _discover(self, files):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, text in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            return MODULE.discover_python(root)

    def test_decorator_registration_uses_override_name(self):
        found = self._discover({'server.py': '''
class MCP:
    def tool(self, *a, **k):
        def wrap(fn): return fn
        return wrap
mcp = MCP()
@mcp.tool(name="search_papers")
def search(query: str):
    return query
'''})
        self.assertEqual([t['tool'] for t in found], ['search_papers'])
        self.assertEqual(found[0]['confidence'], 'decorator_tool_literal')
        self.assertEqual(found[0]['entry_key'], 'server:search')

    def test_custom_registry_decorator_uses_function_name(self):
        found = self._discover({'data_tools.py': '''
def register(tools, workspace):
    @tools.reader("Read range")
    def read_range(path):
        return path
'''})
        self.assertEqual([t['tool'] for t in found], ['read_range'])
        self.assertEqual(found[0]['confidence'], 'custom_registry_decorator_function_name')
        self.assertEqual(found[0]['entry_key'], 'data_tools:register.read_range')

    def test_tool_object_literal_registration(self):
        found = self._discover({'server.py': '''
TOOL = Tool(name="execute_sql", description="run", inputSchema={})
'''})
        self.assertEqual([t['tool'] for t in found], ['execute_sql'])
        self.assertEqual(found[0]['confidence'], 'Tool_object_name_literal')
        self.assertIsNone(found[0]['entry_key'])

    def test_script_registration_and_deduplication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'index.ts').write_text('''
server.registerTool(\n  "read_file",\n  { description: "x" }
);
server.registerTool(\n  "read_file",\n  { description: "x" }
);
''')
            found = MODULE.discover_scripts(root)
        self.assertEqual([t['tool'] for t in found], ['read_file'])
        self.assertEqual(found[0]['language'], 'ts')

    def test_source_is_parsed_not_imported(self):
        found = self._discover({'boom.py': '''
raise SystemExit("must never run")

@tool
def ping():
    return 1
'''})
        self.assertEqual([t['tool'] for t in found], ['ping'])


if __name__ == '__main__':
    unittest.main()
