from pathlib import Path
import tempfile
import unittest
from trustdesc.slicemin.research import ResearchSlicer


class ResearchContextTests(unittest.TestCase):
    def test_unrelated_transport_and_metadata_do_not_describe_the_tool(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'server.py').write_text('''import framework
mcp = framework.Server("Demo")
DEFAULT = 4
UNUSED_DESCRIPTION = "best HTTP tool"
@mcp.tool()
def add(a: int, b: int = DEFAULT):
    return a + b
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
''')
            result=ResearchSlicer(root).slice('add')
        self.assertIn('DEFAULT = 4',result['source'])
        self.assertIn('framework.Server',result['source'])
        self.assertNotIn('streamable-http',result['source'])
        self.assertNotIn('UNUSED_DESCRIPTION',result['source'])
        self.assertTrue(result['context_selection'][0]['omitted'])

    def test_referenced_constant_dependencies_close_transitively(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'server.py').write_text('BASE = 2\nLIMIT = BASE + 1\nUNUSED = 7\ndef tool(value):\n    return value + LIMIT\n')
            result=ResearchSlicer(root).slice('tool',explicit_entry='server:tool')
        self.assertIn('BASE = 2',result['source'])
        self.assertIn('LIMIT = BASE + 1',result['source'])
        self.assertNotIn('UNUSED',result['source'])
