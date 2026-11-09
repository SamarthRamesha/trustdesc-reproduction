"""Mechanical source context; indications, never inferred runtime guarantees."""
from __future__ import annotations
import ast
from trustdesc.common.io import digest


def implementation_context(sliced):
    records=[]
    dependencies=[]
    for key,span in sliced.get('evidence_spans',{}).items():
        tree=ast.parse(span['source'])
        for node in ast.walk(tree):
            kind=None
            if isinstance(node,ast.Return):kind='return_expression'
            elif isinstance(node,ast.Raise):kind='possible_exception'
            elif isinstance(node,(ast.Yield,ast.YieldFrom)):kind='yield_expression'
            elif isinstance(node,(ast.Global,ast.Nonlocal)):kind='shared_state_declaration'
            elif isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
                targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                if any(isinstance(t,(ast.Attribute,ast.Subscript)) for t in targets):kind='possible_mutation'
            elif isinstance(node,ast.Call):
                name=ast.unparse(node.func)
                dependencies.append({'function':key,'call':name,'expression':ast.unparse(node)})
                # These names are hints only: aliasing and dynamic semantics can
                # change their meaning; absence is not absence of side effects.
                leaf=name.rsplit('.',1)[-1]
                if leaf in {'open','write','write_text','write_bytes','unlink','remove','rename','replace','mkdir','rmdir','save','execute','commit','send','post','put','delete','connect','system','Popen','run'}:
                    kind='possible_external_side_effect'
            if kind:
                records.append({'kind':kind,'function':key,'expression':ast.unparse(node),
                                'path':span['path'],'function_line_start':span['line_start'],
                                'function_line_end':span['line_end'],'file_sha256':span['file_sha256']})
    return {'records':records,'dependencies':dependencies,'source_identity':digest(sliced.get('source_hashes',{})),
            'scope':'static syntax indications only; names may be aliased; no absence or entailment guarantee'}
