"""Conservative Python resolver extension; never imports inspected source.

Static resolution is deliberately incomplete. Shadowing and dynamic expressions
are reported rather than guessed. Rewrites remain reasoning artifacts.
"""
from __future__ import annotations
import ast
import copy
from .python import PythonSlicer, SliceError, BodyCalls, dotted


class ResearchSlicer(PythonSlicer):
    def __init__(self, root, **limits):
        super().__init__(root, **limits)
        self.local_aliases = {}
        self.parents = {}
        for mod, tree in self.modules.items():
            path = next(f.path for f in self.functions.values() if f.module == mod) if any(f.module == mod for f in self.functions.values()) else next(p for p in self.sources if p[:-3].replace('/', '.').removesuffix('.__init__') == mod)
            def index(body, scope=''):
                for node in body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        name = (scope + '.' if scope else '') + node.name
                        if not isinstance(node, ast.ClassDef) and scope:
                            self._add(mod, path, node, name)
                            self.parents[f'{mod}:{name}'] = scope
                        index(node.body, name)
            index(tree.body)
        for key, f in self.functions.items():
            aliases = {}
            # A name assigned more than once, a parameter, or assigned in control
            # flow is not a stable alias. Never perform flow-insensitive guessing.
            parameters = {a.arg for a in f.node.args.posonlyargs + f.node.args.args + f.node.args.kwonlyargs}
            counts = {}
            visitor = _Assignments()
            for statement in f.node.body:
                visitor.visit(statement)
            for name in visitor.names:
                counts[name] = counts.get(name, 0) + 1
            for stmt in f.node.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    name = stmt.targets[0].id
                    if counts[name] == 1 and name not in parameters and dotted(stmt.value):
                        aliases[name] = stmt.value
            self.local_aliases[key] = (aliases, parameters | set(visitor.names))

    def resolve_in(self, caller, node):
        f = self.functions[caller]
        name = dotted(node)
        if not name:
            return None
        aliases, shadowed = self.local_aliases[caller]
        first, *rest = name.split('.')
        lexical = caller + '.' + name
        if lexical in self.functions:
            return lexical
        if first in aliases:
            name = '.'.join([dotted(aliases[first])] + rest)
        elif first in shadowed:
            # self/cls methods are the one explicit receiver case we support.
            if first in {'self', 'cls'} and len(rest) == 1 and '.' in caller.split(':')[1]:
                owner = caller.rsplit('.', 1)[0]
                candidate = owner + '.' + rest[0]
                return candidate if candidate in self.functions else None
            return None
        scope = caller.split(':', 1)[1].split('.')
        for end in range(len(scope), -1, -1):
            candidate = f.module + ':' + '.'.join(scope[:end] + [name])
            if candidate in self.functions:
                return candidate
        expr = ast.parse(name, mode='eval').body
        target = super().resolve(f.module, expr)
        if target:
            return target
        # Follow import re-exports without importing any package.
        first, *rest = name.split('.')
        expanded = '.'.join([self.aliases[f.module].get(first, first)] + rest)
        seen = set()
        while expanded not in seen and '.' in expanded:
            seen.add(expanded)
            module, symbol = expanded.rsplit('.', 1)
            if f'{module}:{symbol}' in self.functions:
                return f'{module}:{symbol}'
            if symbol not in self.aliases.get(module, {}):
                break
            expanded = self.aliases[module][symbol]
        return None

    def entry(self, tool, explicit=None):
        try:
            return super().entry(tool, explicit)
        except SliceError:
            if explicit:
                raise
        found = set()
        for key, f in self.functions.items():
            for n in ast.walk(f.node):
                if not isinstance(n, ast.If) or not isinstance(n.test, ast.Compare):
                    continue
                test = n.test
                if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
                    continue
                parts = [test.left, *test.comparators]
                if not any(isinstance(x, ast.Constant) and x.value == tool for x in parts):
                    continue
                if not any(isinstance(x, (ast.Name, ast.Attribute)) and (dotted(x) or '').split('.')[-1] in {'name', 'tool', 'tool_name'} for x in parts):
                    continue
                calls = BodyCalls()
                for stmt in n.body:
                    calls.visit(stmt)
                targets = {self.resolve_in(key, c.func) for c in calls.calls} - {None}
                if len(targets) == 1:
                    found.update(targets)
        if len(found) != 1:
            raise SliceError(f'Ambiguous/missing dispatcher entry for {tool}: {sorted(found)}')
        return found.pop(), 'dispatch_callee_pattern'

    def _graph(self, entry, nodes):
        visited, edges, unresolved = set(), [], []
        def dfs(key):
            if key in visited:
                return
            visited.add(key)
            calls = BodyCalls()
            for stmt in nodes[key].body:
                calls.visit(stmt)
            for call in calls.calls:
                target = self.resolve_in(key, call.func)
                row = {'caller': key, 'callee': target, 'callsite': ast.unparse(call), 'line': call.lineno}
                if target:
                    edges.append(row)
                    dfs(target)
                else:
                    unresolved.append({**row, 'expression': ast.unparse(call.func), 'kind': 'external_or_unresolved'})
        dfs(entry)
        return visited, edges, unresolved

    def slice(self, tool, **kwargs):
        result = super().slice(tool, **kwargs)
        spans = {}
        for key in result['functions']:
            f = self.functions[key]
            spans[key] = {'path': f.path, 'line_start': f.node.lineno, 'line_end': f.node.end_lineno,
                          'file_sha256': self.sources[f.path], 'source': ast.unparse(f.node)}
        result['evidence_spans'] = spans
        result['resolver'] = 'python_ast_conservative_v2'
        result['warnings'] = [w for w in result['warnings'] if 'class methods retained as context; method resolution unsupported' not in w]
        result['warnings'].append('Only statically named self/cls methods and lexical nested calls are resolved; object instances, closures and reflection remain partial')
        result['resolution_confidence'] = 'partial' if result['unresolved_calls'] else 'resolved_in_supported_subset'
        # Original full class/context can contain unreachable methods; narrow it
        # while preserving nested lexical context and module dependencies.
        chunks = []
        reachable = set(result['functions'])
        for mod, tree in self.modules.items():
            if not any(self.functions[k].module == mod for k in reachable):
                continue
            body = []
            for n in tree.body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if f'{mod}:{n.name}' in reachable:
                        body.append(n)
                elif isinstance(n, ast.ClassDef):
                    methods = [x for x in n.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and f'{mod}:{n.name}.{x.name}' in reachable]
                    if methods:
                        node = copy.deepcopy(n)
                        node.body = methods + [x for x in n.body if not isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
                        body.append(node)
                else:
                    body.append(n)
            # Referenced constants/imports are conservative context. Top-level
            # expressions are excluded (source is never executed in either case).
            body = [n for n in body if not isinstance(n, ast.Expr)]
            chunks.append(f'# module: {mod}\n' + ast.unparse(ast.Module(body=body, type_ignores=[])))
        if not result['revisions']:
            result['source'] = '\n\n'.join(chunks)
        result['transformation_validation'] = 'no_executable_transformation' if not result['revisions'] else 'NOT_PROVEN_reasoning_only'
        return result


class _Assignments(ast.NodeVisitor):
    def __init__(self):
        self.names = []

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.names.append(node.id)

    def visit_FunctionDef(self, node):
        self.names.append(node.name)

    visit_AsyncFunctionDef = visit_FunctionDef
    def visit_ClassDef(self, node):
        self.names.append(node.name)
