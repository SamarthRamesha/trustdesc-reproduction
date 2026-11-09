#!/usr/bin/env python3
"""Bounded end-to-end pilot on three recovered tools with successful DescGen output.

Conditions:
  original  - the developer docstring shipped in the recovered source (verbatim)
  full      - real local-model DescGen output (already produced, reused)
  lite      - mechanical removal of the functionality list (paper's lite definition)

DynVer: the model decomposes claims into executable tasks (real output). Execution of
third-party MCP code is gated in this implementation, so no judgement is fabricated:
verdicts are recorded as `blocked` with the reason.
"""
from __future__ import annotations

import ast
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from trustdesc.descgen.prompts import PLAN  # noqa: E402
from trustdesc.reproduction.backends import ManagedModel  # noqa: E402
from trustdesc.reproduction.model import RepairModel  # noqa: E402

PILOT = ['arxiv-mcp-server::watch_topic', 'yfinance-mcp::yfinance_get_ticker_info',
         'excel-mcp-server::set_note']

SOURCE_ROOTS = {
    'arxiv-mcp-server': 'arxiv-mcp-server/src/arxiv_mcp_server',
    'yfinance-mcp': 'yfinance-mcp/src/yfmcp',
    'excel-mcp-server': 'excel-mcp-server/src/excel_mcp',
}


def config():
    cfg = json.loads((ROOT / 'configs/reproduction.json').read_text())
    merged = {**cfg['model_settings'], **cfg['models_by_hardware']['mlx']}
    merged['seed'] = cfg['seed']
    merged['max_worker_rss_bytes'] = 5 * 1024 ** 3
    return merged


def original_description(tool_record):
    root = ROOT / 'data/raw/recovered' / SOURCE_ROOTS[tool_record['server']]
    path = root / tool_record['file']
    tree = ast.parse(path.read_text(encoding='utf-8', errors='replace'))
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for node in funcs:
        if node.name == tool_record['tool']:
            doc = ast.get_docstring(node)
            return {'text': doc, 'origin': 'recovered_public_source_docstring',
                    'file': tool_record['file'], 'line': node.lineno,
                    'note': 'developer-authored description shipped with the tool; not TRUSTDESC output'}
    # Decorator override: @mcp.tool(name="...") on a differently-named function.
    for node in funcs:
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call):
                for kw in dec.keywords:
                    if kw.arg == 'name' and isinstance(kw.value, ast.Constant) and kw.value.value == tool_record['tool']:
                        return {'text': ast.get_docstring(node), 'origin': 'recovered_public_source_docstring',
                                'file': tool_record['file'], 'line': node.lineno,
                                'note': 'developer-authored description shipped with the tool; not TRUSTDESC output'}
    # Tool objects: the developer description is the Tool(...) description literal.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            kv = {k.arg: k.value for k in node.keywords}
            name = kv.get('name')
            if isinstance(name, ast.Constant) and name.value == tool_record['tool']:
                desc = kv.get('description')
                if isinstance(desc, ast.Constant) and isinstance(desc.value, str):
                    return {'text': desc.value, 'origin': 'recovered_public_source_tool_description',
                            'file': tool_record['file'], 'line': node.lineno,
                            'note': 'developer-authored Tool(description=...) literal; not TRUSTDESC output'}
    raise SystemExit(f'entry not found for {tool_record["id"]}')


def main():
    state = json.loads((ROOT / 'reports/recovered_descgen/run_state.json').read_text())
    bench = {t['id']: t for t in json.loads((ROOT / 'data/manifests/recovered_benchmark.json').read_text())['tools']}
    generated = {r['id']: r for r in state['results'] if r['status'] == 'generated'}
    out = ROOT / 'reports/pilot_3tools'
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for tid in PILOT:
        if tid not in generated:
            raise SystemExit(f'missing successful draft for {tid}')
        record = generated[tid]
        original = original_description(bench[tid])
        full = record['description']
        lite = {'summary': full['summary'], 'input_schema': full['input_schema'],
                'functionalities': [], 'claims': [c for c in full['claims']
                                                  if c['target'][0] != 'functionalities'],
                'note': 'lite removes only the functionality list (paper definition)'}
        rows.append({'tool_id': tid, 'server': record['server'], 'tool': record['tool'],
                     'source_file': bench[tid]['file'], 'commit': bench[tid]['commit'],
                     'slice': {'functions': bench[tid]['functions'], 'edges': bench[tid]['edges'],
                               'unresolved_calls': bench[tid]['unresolved_calls'],
                               'slice_sha256': bench[tid]['slice_sha256']},
                     'conditions': {'original': original, 'full': full, 'lite': lite}})

    skip_plan = '--no-plan' in sys.argv
    if skip_plan:
        for row in rows:
            row['dynver'] = {'status': 'plan_not_run_session_budget',
                             'execution': {'status': 'blocked', 'reason': 'no validated isolated runner for these servers',
                                           'verdicts': None},
                             'note': 'task generation can be produced on demand; no verdict is claimed without execution'}
        write(out, rows, state, [])
        return

    model = RepairModel(ManagedModel(config(), ROOT / 'model_cache'))
    try:
        for row in rows:
            began = time.perf_counter()
            try:
                plan = model.complete('verification_plan', PLAN, {'description': row['conditions']['full']})
                row['dynver'] = {'status': 'plan_generated_execution_blocked',
                                 'plan': plan, 'seconds': round(time.perf_counter() - began, 2),
                                 'execution': {'status': 'blocked',
                                               'reason': ('third-party MCP execution is gated: no validated '
                                                          'isolated runner exists for these servers in this build'),
                                               'verdicts': None,
                                               'note': 'no judgement is recorded without real observations'}}
            except Exception as exc:
                row['dynver'] = {'status': 'plan_failed', 'error_type': type(exc).__name__,
                                 'error': str(exc)[:2000]}
            print(row['tool_id'], row['dynver']['status'], flush=True)
    finally:
        calls = list(model.audit)
        model.close()

    write(out, rows, state, calls)


def write(out, rows, state, calls):
    result = {'generated_utc': datetime.now(timezone.utc).isoformat(),
              'classification': 'bounded_pilot_independently_collected_real_tools',
              'is_original_paper_benchmark': False,
              'tools': rows, 'model': state['model_config'],
              'task_agent': 'none (execution gated; identical agent across conditions is vacuous without execution)',
              'task_success_rate': None,
              'tsr_reason': 'no executable task set; reporting a TSR would be fabricated',
              'calls': calls}
    (out / 'pilot.json').write_text(json.dumps(result, indent=2) + '\n')
    print('wrote', (out / 'pilot.json').relative_to(ROOT))


if __name__ == '__main__':
    main()
