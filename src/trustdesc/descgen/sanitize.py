from __future__ import annotations

import ast
import io
import keyword
import tokenize

from trustdesc.common.io import ValidationError, require_fields
from .prompts import IDENTIFIERS


class StripDocstrings(ast.NodeTransformer):
    def visit(self, node):
        node = super().visit(node)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                node.body = node.body[1:]
                if not node.body and not isinstance(node, ast.Module):
                    node.body = [ast.Pass()]
        return node


def names(tree):
    result = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name): result.add(n.id)
        elif isinstance(n, ast.arg): result.add(n.arg)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): result.add(n.name)
        elif isinstance(n, ast.Attribute): result.add(n.attr)
        elif isinstance(n, ast.keyword) and n.arg: result.add(n.arg)
        elif isinstance(n, ast.alias):
            result.update(n.name.split('.'))
            if n.asname: result.add(n.asname)
    return result


def rename_tokens(source, mapping):
    # Token-based replacement changes identifiers, never behavior-bearing strings.
    ts = tokenize.generate_tokens(io.StringIO(source).readline)
    return tokenize.untokenize([t._replace(string=mapping.get(t.string, t.string)) if t.type == tokenize.NAME else t for t in ts])


def check_mapping(all_names, mapping):
    targets = []
    for name in all_names:
        target = mapping.get(name, name)
        if not isinstance(target, str) or not target.isidentifier() or keyword.iskeyword(target) or len(target) > 20:
            raise ValidationError("Identifier normalization produced an invalid/overlong name")
        targets.append(target)
    if len(targets) != len(set(targets)):
        raise ValidationError("Identifier normalization collision; preserve evidence and review")


def sanitize(source: str, model=None):
    if not isinstance(source, str) or not source.strip():
        raise ValidationError("Cannot sanitize an empty slice")
    try:
        tree = StripDocstrings().visit(ast.parse(source))
        cleaned = ast.unparse(ast.fix_missing_locations(tree))
    except SyntaxError as exc:
        raise ValidationError("Malformed Python slice") from exc
    original = names(tree)
    truncated = {n: n[:20] for n in original if len(n) > 20}
    check_mapping(original, truncated)
    cleaned = rename_tokens(cleaned, truncated)
    neutral = {}
    if model is not None:
        current_names = names(ast.parse(cleaned))
        response = model.complete("identifier_filter", IDENTIFIERS,
                                  {"source": cleaned, "identifiers": sorted(current_names)})
        require_fields(response, {'renames'}, 'identifier_filter')
        neutral = response['renames']
        if not isinstance(neutral, dict) or not set(neutral).issubset(current_names):
            raise ValidationError("Identifier filter used unknown identifiers")
        check_mapping(current_names, neutral)
        cleaned = rename_tokens(cleaned, neutral)
    return {"source": cleaned, "truncations": truncated, "semantic_renames": neutral,
            "semantic_filter": "model" if model is not None else "not_run",
            "warning": "Reasoning representation only. Renamed attributes/imports may not execute equivalently; string literals remain untrusted."}
