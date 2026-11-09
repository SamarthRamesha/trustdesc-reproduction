import ast
import hashlib
import unittest
from trustdesc.reproduction.context import implementation_context


class ContextTests(unittest.TestCase):
    def test_returns_exceptions_mutations_and_io_keep_provenance(self):
        source='def tool(path, obj):\n    obj[0] = 1\n    open(path, "w").write("x")\n    if not path:\n        raise ValueError("empty")\n    return {"saved": path}'
        sha=hashlib.sha256(source.encode()).hexdigest()
        value=implementation_context({'evidence_spans':{'server:tool':{'source':source,'path':'server.py','line_start':9,'line_end':15,'file_sha256':sha}},'source_hashes':{'server.py':sha}})
        kinds={r['kind'] for r in value['records']}
        self.assertTrue({'possible_mutation','possible_external_side_effect','possible_exception','return_expression'}.issubset(kinds))
        self.assertTrue(all(r['file_sha256']==sha and r['function_line_start']==9 for r in value['records']))
        self.assertIn('no absence',value['scope'])
