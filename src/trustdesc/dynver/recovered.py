"""Execute recovered tool bodies inside the Seatbelt boundary.

Every recovered tool is an adapter over an external SDK, so behavioural
verification needs *something* for the transport. This module replaces only the
transport/adapter imports with explicit, recorded shims (network-facing calls
raise), keeps real standard-library and installed dependency code, and runs the
unmodified tool body inside the OS sandbox. Claims that depend on a shimmed
adapter are reported as inconclusive rather than supported.
"""
from __future__ import annotations

import ast
import json

# Shims for one representative server (arxiv-mcp-server). Each name below is an
# import the slice needs; none of them performs work the claims under test
# concern, except the two network helpers which raise by design.
ARXIV_SHIMS = '''
import json, os, logging, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dateutil import parser

class TextContent:
    def __init__(self, type='text', text=''):
        self.type, self.text = type, text
    def __repr__(self):
        return f'TextContent({self.text!r})'

ToolAnnotations = None
types = type('types', (), {'TextContent': TextContent, 'ToolAnnotations': None})

class Settings:
    STORAGE_PATH = os.getcwd()
    MAX_RESULTS = 50

class ArxivRateLimitError(Exception):
    pass

def _rate_limited_response(*a, **k):
    raise RuntimeError('network disabled inside the sandbox')

def _raw_arxiv_search(*a, **k):
    raise RuntimeError('network disabled inside the sandbox')
'''

SHIMS = {'arxiv-mcp-server': ARXIV_SHIMS}


def strip_imports(source: str) -> str:
    """Drop module-level imports; the shim preamble supplies every name."""
    tree = ast.parse(source)
    keep = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        keep.append(node)
    tree.body = keep
    return ast.unparse(ast.fix_missing_locations(tree))


def build_module(source: str, server: str, extra_path: str | None = None) -> str:
    if server not in SHIMS:
        raise KeyError(f'no adapter shims defined for {server}')
    preamble = SHIMS[server]
    if extra_path:
        # Read-only dependency directory explicitly permitted by the sandbox policy.
        preamble = f'import sys\nsys.path.insert(0, {extra_path!r})\n' + preamble
    return preamble + '\n' + strip_imports(source)


WRAPPER = '''import asyncio, inspect, json, os, resource, runpy, sys
resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
resource.setrlimit(resource.RLIMIT_FSIZE, (262144, 262144))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
request = json.loads(open('request.json').read())
SKIP = {'tool.py', 'wrapper.py', 'request.json', 'policy.sb', 'stdout', 'stderr'}

def normalise(value):
    text = getattr(value, 'text', None)
    if isinstance(text, str):
        return {'type': type(value).__name__, 'text': text}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [normalise(item) for item in value]
    if isinstance(value, dict):
        return {str(k): normalise(v) for k, v in value.items()}
    return {'type': type(value).__name__, 'repr': repr(value)[:2000]}

def snapshot():
    files = {}
    for root, _dirs, names in os.walk('.'):
        for name in names:
            if name in SKIP:
                continue
            path = os.path.join(root, name)
            try:
                files[path] = open(path, encoding='utf-8', errors='replace').read()[:4000]
            except OSError:
                files[path] = '<unreadable>'
    return files

try:
    namespace = runpy.run_path('tool.py')
    function = namespace[request['function']]
    # MCP handlers take a single request dict; plain functions take keywords.
    parameters = list(inspect.signature(function).parameters)
    if parameters == ['arguments']:
        value = function(request['arguments'])
    else:
        value = function(**request['arguments'])
    if inspect.isawaitable(value):
        value = asyncio.run(value)
    payload = {'status': 'ok', 'result': normalise(value), 'files': snapshot()}
except Exception as exc:
    import traceback
    payload = {'status': 'tool_error', 'error_type': type(exc).__name__, 'error': str(exc),
               'traceback': traceback.format_exc()[-4000:], 'files': snapshot()}
print(json.dumps(payload, allow_nan=False, default=str))
'''


def verdict_for(observation: dict, shim_dependent: bool) -> str:
    """supported / refuted / inconclusive, only from observed evidence."""
    if observation.get('process_status') not in {None, 'exited'}:
        return 'inconclusive'
    body = observation.get('observation')
    if not isinstance(body, dict):
        return 'inconclusive'
    if body.get('status') != 'ok':
        return 'refuted' if not shim_dependent else 'inconclusive'
    return 'inconclusive' if shim_dependent else 'supported'
