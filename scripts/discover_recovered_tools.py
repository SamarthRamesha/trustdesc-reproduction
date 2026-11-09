#!/usr/bin/env python3
"""Static discovery of tool registrations in independently recovered public MCP sources.

Source is parsed as text/AST only; it is never imported or executed. Discovered
tools are labelled `independently_collected` and are NOT the paper's sampled
52-tool selection, whose sampling seed and revisions were never released.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from trustdesc.slicemin.python import dotted  # noqa: E402

RECOVERED = ROOT / 'data/raw/recovered'
SERVER_MANIFEST = ROOT / 'data/manifests/paper_servers.json'

# Directory name in data/raw/recovered -> paper server name.
DIRECTORIES = {
    'excel-mcp-server': 'excel-mcp-server',
    'markdownify-mcp': 'markdownify-mcp',
    'mysql_mcp_server': 'mysql_mcp_server',
    'arxiv-mcp-server': 'arxiv-mcp-server',
    'paper-search-mcp': 'paper-search-mcp',
    'mcp-servers-monorepo/src/filesystem': 'filesystem',
    'context7': 'context7',
    'wikipedia-mcp': 'wikipedia-mcp',
    'yfinance-mcp': 'yfinance-mcp',
    'travel-planner-mcp-server': 'travel-planner-mcp-server',
    'healthcare-mcp-public': 'healthcare-mcp',
    'imagesorcery-mcp': 'imagesorcery-mcp',
}

SKIP_PARTS = {'node_modules', 'dist', 'build', '.git', '__pycache__', 'venv', '.venv'}
TS_REGISTRATION = re.compile(
    r'(?:registerTool|tool)\s*\(\s*[\'"](?P<quoted>[A-Za-z0-9_\-]+)[\'"]'
    r'|name\s*:\s*[\'"](?P<named>[A-Za-z0-9_\-]+)[\'"]\s*,\s*(?:description|title|inputSchema)'
)


def python_files(root: Path):
    return sorted(
        p for p in root.rglob('*.py')
        if not any(part in SKIP_PARTS or part.startswith('.') for part in p.relative_to(root).parts)
    )


def discover_python(root: Path):
    found = []
    for path in python_files(root):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(('test', 'tests/')) or '/tests/' in rel:
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf-8', errors='replace'), filename=rel)
        except (SyntaxError, RecursionError, UnicodeDecodeError):
            continue
        parents = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                name = (dotted(target) or '')
                if not name:
                    continue
                if name.split('.')[-1] not in {'tool', 'mcp_tool'}:
                    continue
                exposed = node.name
                if isinstance(dec, ast.Call):
                    for kw in dec.keywords:
                        if kw.arg == 'name' and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                            exposed = kw.value.value
                scope = parents.get(node)
                in_class = isinstance(scope, ast.ClassDef)
                found.append({
                    'tool': exposed, 'function': node.name, 'file': rel,
                    'line': node.lineno, 'decorator': name,
                    'entry_kind': 'decorator_registration',
                    'in_class': in_class,
                    'entry_key': f"{rel[:-3].replace('/', '.')}:{node.name}",
                    'async': isinstance(node, ast.AsyncFunctionDef),
                    'language': 'python',
                })
    return found


def discover_typescript(root: Path):
    found, seen = [], set()
    for path in sorted(root.rglob('*.ts')):
        rel = path.relative_to(root).as_posix()
        if any(part in SKIP_PARTS for part in rel.split('/')):
            continue
        if rel.endswith('.d.ts'):
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for match in TS_REGISTRATION.finditer(text):
            name = match.group('quoted') or match.group('named')
            if not name or (rel, name) in seen:
                continue
            seen.add((rel, name))
            found.append({
                'tool': name, 'function': None, 'file': rel,
                'line': text[:match.start()].count('\n') + 1,
                'decorator': 'registerTool/tool',
                'entry_kind': 'typescript_static_pattern',
                'in_class': False, 'entry_key': None, 'async': None,
                'language': 'typescript',
            })
    return found


def license_of(root: Path):
    for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'COPYING'):
        candidate = root / name
        if candidate.is_file():
            head = candidate.read_text(encoding='utf-8', errors='replace').strip().splitlines()
            return {'file': name, 'first_line': head[0].strip() if head else '',
                    'sha256': hashlib.sha256(candidate.read_bytes()).hexdigest()}
    return None


def main():
    manifest = {s['name']: s for s in json.loads(SERVER_MANIFEST.read_text())}
    report = []
    for directory, server in DIRECTORIES.items():
        root = RECOVERED / directory
        entry = {'server': server, 'directory': directory, 'path': str(root.relative_to(ROOT))}
        if not root.is_dir():
            entry.update({'status': 'source_missing', 'discovered': 0})
            report.append(entry)
            continue
        git_head = root / '.git'
        entry['status'] = 'recovered_public_source'
        entry['language_in_paper'] = manifest.get(server, {}).get('paper_language')
        entry['paper_selected_count'] = manifest.get(server, {}).get('selected_count')
        entry['repository'] = manifest.get(server, {}).get('source')
        entry['license'] = license_of(root)
        py = discover_python(root) if any(root.rglob('*.py')) else []
        ts = discover_typescript(root)
        tools = py + ts
        entry['discovered'] = len(tools)
        entry['discovered_python'] = len(py)
        entry['discovered_typescript'] = len(ts)
        entry['tools'] = tools
        entry['slicer_supported'] = [t['tool'] for t in py]
        entry['slicer_unsupported'] = [t['tool'] for t in ts]
        report.append(entry)

    out = ROOT / 'data/manifests/recovered_tools.json'
    out.write_text(json.dumps({'method': 'static_text_ast_only_never_executed',
                               'classification': 'independently_collected',
                               'not_the_paper_selection': True,
                               'servers': report}, indent=2) + '\n')
    for entry in report:
        print(f"{entry['server']:26} py={entry.get('discovered_python', 0):3} "
              f"ts={entry.get('discovered_typescript', 0):3} paper={entry.get('paper_selected_count')}")
    print(f'saved {out.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
