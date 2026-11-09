#!/usr/bin/env python3
"""Build an independently collected benchmark from the paper's 12 named public servers.

Every record is labelled `independently_collected`: the paper's random sampling
seed, exact revisions and 208 task texts were never released, so this is not the
paper's benchmark. Source is parsed as text/AST only and never imported.

Stages:
  1. static discovery of tool registrations (four observed styles)
  2. deterministic selection of the paper's per-server tool count
  3. SliceMin (ResearchSlicer) coverage measurement per selected tool
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from trustdesc.slicemin.python import dotted  # noqa: E402
from trustdesc.slicemin.research import ResearchSlicer  # noqa: E402

RECOVERED = ROOT / 'data/raw/recovered'
SERVER_MANIFEST = ROOT / 'data/manifests/paper_servers.json'

# paper server name -> (clone directory, analysis root inside clone)
SOURCES = {
    'excel-mcp-server': ('excel-mcp-server', 'src/excel_mcp'),
    'markdownify-mcp': ('markdownify-mcp', 'src'),
    'mysql_mcp_server': ('mysql_mcp_server', 'src/mysql_mcp_server'),
    'arxiv-mcp-server': ('arxiv-mcp-server', 'src/arxiv_mcp_server'),
    'paper-search-mcp': ('paper-search-mcp', 'paper_search_mcp'),
    'filesystem': ('mcp-servers-monorepo/src/filesystem', '.'),
    'context7': ('context7', '.'),
    'wikipedia-mcp': ('wikipedia-mcp', 'wikipedia_mcp'),
    'yfinance-mcp': ('yfinance-mcp', 'src/yfmcp'),
    'travel-planner-mcp': ('travel-planner-mcp-server', '.'),
    'healthcare-mcp': ('healthcare-mcp-public', 'server'),
    'imagesorcery-mcp': ('imagesorcery-mcp', 'src/imagesorcery_mcp'),
}

SKIP_PARTS = {'node_modules', 'dist', 'build', '.git', '__pycache__', 'venv', '.venv', 'tests', 'test'}
SCRIPT_SUFFIXES = ('.ts', '.js', '.mjs')
REGISTRY_ATTRS = {'tool', 'reader', 'destroyer', 'exporter', 'writer', 'creator'}
TS_REGISTRATION = re.compile(
    r'(?:registerTool|server\s*\.\s*tool|\.tool)\s*\(\s*[\'"](?P<quoted>[A-Za-z0-9_\-]+)[\'"]'
    r'|name\s*:\s*[\'"](?P<named>[A-Za-z0-9_\-]+)[\'"]\s*,\s*(?:description|title|inputSchema|parameters)'
)


def walk_python(root: Path):
    for path in sorted(root.rglob('*.py')):
        parts = path.relative_to(root).parts
        if any(p in SKIP_PARTS or p.startswith('.') for p in parts):
            continue
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding='utf-8', errors='replace'), filename=rel)
        except (SyntaxError, RecursionError, UnicodeDecodeError):
            continue
        yield path, rel, tree


def module_of(rel: str) -> str:
    mod = rel[:-3].replace('/', '.')
    return mod[:-9] if mod.endswith('.__init__') else mod


def decorator_name(dec) -> str:
    target = dec.func if isinstance(dec, ast.Call) else dec
    return dotted(target) or ''


def string_arg(dec) -> str | None:
    if isinstance(dec, ast.Call) and dec.args and isinstance(dec.args[0], ast.Constant):
        if isinstance(dec.args[0].value, str):
            return dec.args[0].value
    return None


def discover_python(root: Path):
    found = []
    for path, rel, tree in walk_python(root):
        parents = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node

        def qualified(node):
            names, current = [node.name], parents.get(node)
            while current is not None:
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.append(current.name)
                current = parents.get(current)
            return '.'.join(reversed(names))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    name = decorator_name(dec)
                    if not name:
                        continue
                    last = name.split('.')[-1]
                    exposed = None
                    confidence = None
                    if last == 'tool':
                        exposed = node.name
                        if isinstance(dec, ast.Call):
                            for kw in dec.keywords:
                                if kw.arg == 'name' and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                    exposed = kw.value.value
                        confidence = 'decorator_tool_literal'
                    elif last in REGISTRY_ATTRS or last.endswith('register_tool'):
                        if isinstance(dec, ast.Call) and string_arg(dec):
                            # Custom registry decorator: the MCP name is the function name
                            # (verified against excel-mcp-server's ToolRegistry).
                            exposed = node.name
                            confidence = 'custom_registry_decorator_function_name'
                    if not exposed:
                        continue
                    found.append({
                        'tool': exposed, 'function': node.name, 'file': rel, 'line': node.lineno,
                        'decorator': name, 'entry_kind': 'decorator_registration',
                        'confidence': confidence, 'language': 'python',
                        'entry_key': f'{module_of(rel)}:{qualified(node)}',
                        'async': isinstance(node, ast.AsyncFunctionDef),
                    })
            elif isinstance(node, ast.Call):
                name = dotted(node.func) or ''
                if name.split('.')[-1] != 'Tool':
                    continue
                kv = {k.arg: k.value for k in node.keywords}
                nm = kv.get('name')
                if isinstance(nm, ast.Constant) and isinstance(nm.value, str) and ('description' in kv or 'inputSchema' in kv):
                    found.append({
                        'tool': nm.value, 'function': None, 'file': rel, 'line': node.lineno,
                        'decorator': name, 'entry_kind': 'tool_object_literal',
                        'confidence': 'Tool_object_name_literal', 'language': 'python',
                        'entry_key': None, 'async': None,
                    })
    dedup, seen = [], set()
    for item in sorted(found, key=lambda t: (t['file'], t['line'], t['tool'])):
        key = (item['tool'], item['entry_key'])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)
    return dedup


def discover_scripts(root: Path):
    found, seen = [], set()
    for path in sorted(root.rglob('*')):
        if path.suffix not in SCRIPT_SUFFIXES or not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(p in SKIP_PARTS for p in rel.split('/')) or rel.endswith('.d.ts'):
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
                'decorator': 'registerTool/tool/object-literal',
                'entry_kind': 'script_static_pattern',
                'confidence': 'js_ts_literal_pattern', 'language': path.suffix.lstrip('.'),
                'entry_key': None, 'async': None,
            })
    return sorted(found, key=lambda t: (t['file'], t['line'], t['tool']))


def license_of(root: Path):
    for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'COPYING'):
        candidate = root / name
        if candidate.is_file():
            text = candidate.read_text(encoding='utf-8', errors='replace')
            first = text.strip().splitlines()[0].strip() if text.strip() else ''
            return {'file': name, 'first_line': first,
                    'sha256': hashlib.sha256(candidate.read_bytes()).hexdigest()}
    return None


def commit_of(repo: Path):
    import subprocess
    try:
        return subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True,
                              text=True, timeout=30).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def main():
    paper = {s['name']: s for s in json.loads(SERVER_MANIFEST.read_text())}
    tools_out, coverage, servers_out = [], [], []
    for server, (directory, subdir) in SOURCES.items():
        clone = RECOVERED / directory
        info = {'server': server, 'clone_directory': directory,
                'analysis_root': f'{directory}/{subdir}'.rstrip('./'),
                'paper': {k: paper[server][k] for k in ('source', 'paper_language', 'category', 'selected_count')}}
        if not clone.is_dir():
            info['status'] = 'source_unavailable'
            servers_out.append(info)
            continue
        root = (clone / subdir).resolve() if subdir != '.' else clone
        info['commit'] = commit_of(clone)
        info['license'] = license_of(clone)
        info['status'] = 'recovered_public_source_at_current_head'
        py = discover_python(root)
        scripts = discover_scripts(root)
        info['discovered_python'] = len(py)
        info['discovered_scripts'] = len(scripts)
        info['slicer_supported_language'] = 'python' if py else 'none'
        servers_out.append(info)

        target = paper[server]['selected_count']
        selected = py[:target]
        info['selected_count'] = len(selected)
        info['selection'] = ('deterministic prefix of static discovery order; '
                             'the paper sampled randomly and never released its seed')
        slicer = ResearchSlicer(root) if py else None
        for item in selected:
            record = {'id': f"{server}::{item['tool']}", 'server': server, 'tool': item['tool'],
                      'language': 'python', 'file': item['file'], 'line': item['line'],
                      'decorator': item['decorator'], 'entry_kind': item['entry_kind'],
                      'confidence': item['confidence'], 'proposed_entry': item['entry_key'],
                      'origin': 'independently_collected', 'selection': info['selection'],
                      'source': paper[server]['source'], 'commit': info['commit'],
                      'license': (info['license'] or {}).get('first_line')}
            slice_result, error, method = None, None, None
            for attempt, entry in ((1, None), (2, item['entry_key'])):
                try:
                    slice_result = slicer.slice(item['tool'], explicit_entry=entry)
                    method = 'registration_pattern' if entry is None else 'explicit_name_match'
                    break
                except Exception as exc:  # SliceError or unresolved graph
                    error = f'{type(exc).__name__}: {exc}'
            if slice_result:
                record.update({
                    'slice_status': 'sliced', 'entry_resolution': method,
                    'resolved_entry': slice_result['entry'],
                    'functions': len(slice_result['functions']),
                    'edges': len(slice_result['edges']),
                    'unresolved_calls': len(slice_result['unresolved_calls']),
                    'slice_sha256': hashlib.sha256(slice_result['source'].encode()).hexdigest(),
                    'slice_bytes': len(slice_result['source'].encode()),
                })
                slices_dir = ROOT / 'data/recovered_slices'
                slices_dir.mkdir(parents=True, exist_ok=True)
                name = re.sub(r'[^A-Za-z0-9_.-]', '_', record['id'])
                (slices_dir / f'{name}.json').write_text(json.dumps(slice_result, indent=2) + '\n')
            else:
                record.update({'slice_status': 'entry_unresolved', 'slice_error': error})
            tools_out.append(record)
        coverage.append({'server': server, 'selected': len(selected),
                         'sliced': sum(1 for t in tools_out if t['server'] == server and t['slice_status'] == 'sliced')})

    manifest = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'classification': 'independently_collected_recovered_public_source',
        'is_original_paper_benchmark': False,
        'not_original_reason': ('Paper released no tool list, sampling seed, revisions, tasks, prompts, '
                                'labels or traces; its anonymous artifact expired (API: repository_expired) '
                                'and has no Wayback snapshot.'),
        'source_policy': 'static AST/text analysis only; third-party code is never imported or executed',
        'selection_policy': 'deterministic prefix of discovery order to match the paper per-server counts',
        'servert_total_expected': 52,
        'servers': servers_out,
        'tools': tools_out,
        'coverage': coverage,
    }
    out = ROOT / 'data/manifests/recovered_benchmark.json'
    out.write_text(json.dumps(manifest, indent=2) + '\n')
    sliced = [t for t in tools_out if t['slice_status'] == 'sliced']
    print(f'tools selected: {len(tools_out)}')
    print(f'tools sliced:   {len(sliced)}')
    for c in coverage:
        print(f"  {c['server']:26} {c['sliced']}/{c['selected']}")
    for t in tools_out:
        if t['slice_status'] != 'sliced':
            print(f"  UNRESOLVED {t['id']}: {t['slice_error'][:110]}")
    print(f'saved {out.relative_to(ROOT)}')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
