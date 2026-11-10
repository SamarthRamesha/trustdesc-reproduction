import unittest

from trustdesc.dynver.recovered import build_module, strip_imports, verdict_for

SLICE = '''
import json
from pathlib import Path
import mcp.types as types
from ..config import Settings

async def handle_echo(arguments):
    value = (arguments.get('value') or '').strip()
    if not value:
        return [types.TextContent(type='text', text='Error: value is required')]
    Path('echo.json').write_text(json.dumps({'value': value}))
    return [types.TextContent(type='text', text='ok')]
'''


class RecoveredDynVerTests(unittest.TestCase):
    def test_imports_are_replaced_by_the_shim_preamble(self):
        stripped = strip_imports(SLICE)
        self.assertNotIn('import mcp', stripped)
        self.assertNotIn('from ..config', stripped)
        self.assertIn('handle_echo', stripped)

    def test_module_keeps_the_real_body(self):
        module = build_module(SLICE, 'arxiv-mcp-server')
        self.assertIn('TextContent', module)          # shim supplies the type
        self.assertIn("echo.json", module)            # body is unchanged
        self.assertIn('class Settings', module)

    def test_unknown_server_is_refused(self):
        with self.assertRaises(KeyError):
            build_module(SLICE, 'not-a-server')

    def test_verdicts_require_evidence(self):
        ok = {'process_status': 'exited', 'observation': {'status': 'ok'}}
        self.assertEqual(verdict_for(ok, False), 'supported')
        self.assertEqual(verdict_for(ok, True), 'inconclusive')
        self.assertEqual(verdict_for({'process_status': 'timeout', 'observation': None}, False),
                         'inconclusive')
        self.assertEqual(verdict_for({'process_status': 'exited',
                                      'observation': {'status': 'tool_error'}}, False), 'refuted')


if __name__ == '__main__':
    unittest.main()
