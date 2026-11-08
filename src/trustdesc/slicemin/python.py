"""Import-free, bounded Python reachability analysis.

This is a restricted AST reimplementation, not the authors' tree-sitter analyzer.
No input source is imported, compiled to executable code, or executed.
"""
from __future__ import annotations

import ast
import copy
from dataclasses import dataclass
import hashlib
from pathlib import Path

from trustdesc.common.io import ValidationError, nonempty, require_fields


class SliceError(ValidationError):
    pass


@dataclass
class Function:
    key: str
    module: str
    path: str
    node: ast.FunctionDef | ast.AsyncFunctionDef


def dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


class BodyCalls(ast.NodeVisitor):
    def __init__(self):
        self.calls = []
        self.nested = False

    def visit_Call(self, node):
        self.calls.append(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.nested = True

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        self.nested = True


class PythonSlicer:
    def __init__(self, root: str | Path, *, max_files=500, max_bytes=5_000_000):
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise SliceError("Source directory does not exist")
        files = sorted(p for p in self.root.rglob("*.py") if not any(x.startswith('.') or x == '__pycache__' for x in p.relative_to(self.root).parts))
        if not files:
            raise SliceError("No Python source files (TypeScript is unsupported)")
        if len(files) > max_files or sum(p.stat().st_size for p in files) > max_bytes:
            raise SliceError("Source exceeds static-analysis limits")
        self.functions, self.modules, self.aliases, self.sources = {}, {}, {}, {}
        self.warnings = set()
        for p in files:
            if p.is_symlink() or not p.resolve().is_relative_to(self.root):
                raise SliceError("Symlinked source files are not accepted")
            rel = p.relative_to(self.root).as_posix()
            mod = rel[:-3].replace('/', '.')
            if mod.endswith('.__init__'):
                mod = mod[:-9]
            text = p.read_text()
            try:
                tree = ast.parse(text, filename=rel)
            except (SyntaxError, RecursionError) as exc:
                raise SliceError(f"Cannot parse {rel}: {type(exc).__name__}") from exc
            if mod in self.modules:
                raise SliceError(f"Duplicate module name {mod}")
            self.modules[mod] = tree
            self.sources[rel] = hashlib.sha256(text.encode()).hexdigest()
            aliases = {}
            for n in tree.body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._add(mod, rel, n, n.name)
                elif isinstance(n, ast.ClassDef):
                    self.warnings.add(f"{rel}: class methods retained as context; method resolution unsupported")
                elif isinstance(n, ast.ImportFrom):
                    if n.level:
                        package = mod.split('.') if p.name == '__init__.py' else mod.split('.')[:-1]
                        if n.level > len(package):
                            self.warnings.add(f"{rel}: relative import beyond package")
                        prefix = package[:len(package) - n.level + 1]
                        base = '.'.join(prefix + ([n.module] if n.module else []))
                    else:
                        base = n.module or ''
                    for a in n.names:
                        if a.name == '*':
                            self.warnings.add(f"{rel}: wildcard import unresolved")
                        aliases[a.asname or a.name] = f"{base}.{a.name}".strip('.')
                elif isinstance(n, ast.Import):
                    for a in n.names:
                        aliases[a.asname or a.name.split('.')[0]] = a.name if a.asname else a.name.split('.')[0]
            self.aliases[mod] = aliases

    def _add(self, mod, path, node, name):
        key = f"{mod}:{name}"
        if key in self.functions:
            raise SliceError(f"Repeated/redefined function {key}")
        self.functions[key] = Function(key, mod, path, node)

    def resolve(self, mod, node):
        name = dotted(node)
        if not name:
            return None
        if f"{mod}:{name}" in self.functions:
            return f"{mod}:{name}"
        first, *rest = name.split('.')
        expanded = '.'.join([self.aliases[mod].get(first, first)] + rest)
        if '.' in expanded:
            module, fn = expanded.rsplit('.', 1)
            key = f"{module}:{fn}"
            if key in self.functions:
                return key
        return None

    def entry(self, tool: str, explicit: str | None = None):
        nonempty(tool, "tool")
        if explicit is not None:
            if explicit not in self.functions:
                raise SliceError(f"Explicit entry {explicit} not found")
            return explicit, "explicit_operator_override"
        found = set()
        for key, f in self.functions.items():
            for dec in f.node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                if (dotted(target) or '').split('.')[-1] == 'tool':
                    exposed = f.node.name
                    if isinstance(dec, ast.Call):
                        for kw in dec.keywords:
                            if kw.arg == 'name' and isinstance(kw.value, ast.Constant):
                                exposed = kw.value.value
                    if exposed == tool:
                        found.add(key)
        for mod, tree in self.modules.items():
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and (dotted(n.func) or '').split('.')[-1] in {'registerTool', 'register_tool'}:
                    if n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == tool:
                        refs = [self.resolve(mod, a) for a in n.args[1:]]
                        refs += [self.resolve(mod, k.value) for k in n.keywords if k.arg in {'handler', 'callback', 'fn'}]
                        found.update(x for x in refs if x)
        if len(found) != 1:
            raise SliceError(f"Expected one registered entry for {tool!r}; found {sorted(found)}. Supply an explicit module:function after review; dispatcher/LLM fallback not implemented.")
        return found.pop(), "registration_pattern"

    def _graph(self, entry, nodes):
        visited, edges, unresolved = set(), [], []

        def dfs(key):
            if key in visited:
                return
            visited.add(key)
            f = self.functions[key]
            visitor = BodyCalls()
            for stmt in nodes[key].body:
                visitor.visit(stmt)
            if visitor.nested:
                self.warnings.add(f"{key}: nested functions/lambdas not resolved")
            for call in visitor.calls:
                target = self.resolve(f.module, call.func)
                record = {"caller": key, "callee": target, "callsite": ast.unparse(call), "line": call.lineno}
                if target:
                    edges.append(record)
                    dfs(target)
                else:
                    record['expression'] = ast.unparse(call.func)
                    record['kind'] = 'external_or_unresolved'  # do not pretend external classification is certain
                    unresolved.append(record)
        dfs(entry)
        return visited, edges, unresolved

    def slice(self, tool, *, explicit_entry=None, model=None, max_passes=3):
        if not 1 <= max_passes <= 10:
            raise SliceError("max_passes must be 1..10")
        entry, entry_method = self.entry(tool, explicit_entry)
        nodes = {k: copy.deepcopy(f.node) for k, f in self.functions.items()}
        visited, edges, unresolved = self._graph(entry, nodes)
        initial = sorted(visited)
        revisions = []
        converged = model is None
        # No offline constant propagation is masqueraded as the paper's LLM.
        if model is not None:
            from trustdesc.descgen.prompts import DEBLOAT
            for iteration in range(max_passes):
                changed = False
                for key in sorted(visited):
                    current = nodes[key]
                    callsites = [e for e in edges if e['callee'] == key]
                    response = model.complete("debloat", DEBLOAT,
                                              {"function": key, "source": ast.unparse(current),
                                               "callsites": callsites, "externally_callable": key == entry})
                    require_fields(response, {'source', 'rationale'}, 'debloat')
                    nonempty(response['rationale'], 'rationale')
                    try:
                        parsed = ast.parse(nonempty(response['source'], 'source'))
                    except SyntaxError as exc:
                        raise SliceError("Invalid LLM rewrite syntax") from exc
                    if len(parsed.body) != 1 or type(parsed.body[0]) is not type(current):
                        raise SliceError("LLM rewrite must contain only the same function kind")
                    replacement = parsed.body[0]
                    if replacement.name != current.name or ast.dump(replacement.args) != ast.dump(current.args):
                        raise SliceError("LLM rewrite cannot change function name/signature")
                    if ([ast.dump(x) for x in replacement.decorator_list] != [ast.dump(x) for x in current.decorator_list]
                            or (ast.dump(replacement.returns) if replacement.returns else None) != (ast.dump(current.returns) if current.returns else None)):
                        raise SliceError("LLM rewrite cannot change registration or return annotation")
                    different = ast.dump(replacement, include_attributes=False) != ast.dump(current, include_attributes=False)
                    if different:
                        nodes[key] = replacement
                        revisions.append({"function": key, "iteration": iteration,
                                          "before": ast.unparse(current), "after": ast.unparse(replacement),
                                          "rationale": response['rationale'], "equivalence": "not_proven"})
                        changed = True
                visited, edges, unresolved = self._graph(entry, nodes)
                if not changed:
                    converged = True
                    break
        chunks, included_modules = [], sorted({self.functions[k].module for k in visited})
        # Retain module-level imports/constants/classes as explicit conservative context.
        # It is never executed; this can over-include irrelevant information.
        for mod in included_modules:
            context = [n for n in self.modules[mod].body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            chunks.append(f"# module context: {mod}\n" + ast.unparse(ast.Module(body=context, type_ignores=[])))
        for key in sorted(visited):
            chunks.append(f"# function: {key}\n" + ast.unparse(nodes[key]))
        warnings = sorted(self.warnings | {'Python AST subset; no soundness/equivalence guarantee',
                                          'External and unresolved calls are not expanded',
                                          'Module-level context is conservatively retained'})
        return {"tool": tool, "entry": entry, "entry_method": entry_method,
                "source": '\n\n'.join(chunks), "initial_functions": initial,
                "functions": sorted(visited), "edges": edges, "unresolved_calls": unresolved,
                "source_hashes": self.sources, "revisions": revisions, "converged": converged,
                "mode": "llm_debloat_unproven" if model else "static_only_no_debloating",
                "warnings": warnings}
