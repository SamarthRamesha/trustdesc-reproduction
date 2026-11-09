#!/usr/bin/env python3
"""Aggregate the recovered-corpus experiment into the handover deliverables."""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'reports/recovered_descgen'
BENCH = ROOT / 'data/manifests/recovered_benchmark.json'
FIXTURE_RUN = ROOT / 'reports/apple_silicon_delivery/automatic-93589e7e9672adf4a537'


def svg_bar(title, rows, width=720, height=340):
    """Minimal dependency-free SVG bar chart."""
    pad, top = 60, 60
    maxv = max((v for _, v, _ in rows), default=1) or 1
    bar_h = max(16, (height - top - 40) // max(len(rows), 1) - 6)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
             f'<rect width="100%" height="100%" fill="#ffffff"/>',
             f'<text x="{pad}" y="30" font-family="Helvetica" font-size="16" fill="#111">{title}</text>']
    for i, (label, value, total) in enumerate(rows):
        y = top + i * (bar_h + 6)
        bar_w = int((width - pad - 160) * (value / maxv))
        parts.append(f'<text x="6" y="{y + bar_h - 4}" font-family="Helvetica" font-size="11" fill="#333">{label[:38]}</text>')
        parts.append(f'<rect x="{pad + 150}" y="{y}" width="{bar_w}" height="{bar_h}" fill="#2f6feb"/>')
        parts.append(f'<text x="{pad + 150 + bar_w + 6}" y="{y + bar_h - 4}" font-family="Helvetica" '
                     f'font-size="11" fill="#333">{value}/{total}</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


def main():
    bench = json.loads(BENCH.read_text())
    state = json.loads((RUN / 'run_state.json').read_text())
    qualification = json.loads((RUN / 'model_qualification.json').read_text())
    runtime = json.loads((RUN / 'runtime.json').read_text())
    results = state['results']
    generated = [r for r in results if r['status'] == 'generated']
    failed = [r for r in results if r['status'] != 'generated']
    now = datetime.now(timezone.utc).isoformat()

    per_server = defaultdict(lambda: {'attempted': 0, 'generated': 0})
    for r in results:
        per_server[r['server']]['attempted'] += 1
        per_server[r['server']]['generated'] += r['status'] == 'generated'

    slices = {t['id']: t for t in bench['tools'] if t['slice_status'] == 'sliced'}
    timing = [r['seconds'] for r in results if r.get('seconds')]

    experiment = {
        'experiment_id': 'recovered-public-source-descgen',
        'generated_utc': now,
        'classification': 'independent_supplementary_experiment',
        'is_original_paper_benchmark': False,
        'corpus': {
            'source': '12 paper-named public servers cloned at pinned commits',
            'manifest': 'data/manifests/recovered_benchmark.json',
            'paper_tools_reported': 52, 'tools_selected': len(bench['tools']),
            'tools_sliced': len(slices), 'unsupported_language_tools': 52 - len(bench['tools']),
            'task_records': 0, 'labels': 0, 'traces_from_authors': 0,
        },
        'model': {'model_id': runtime.get('model_id'), 'revision': runtime.get('revision'),
                  'backend': runtime.get('backend'), 'mlx': runtime.get('mlx'),
                  'mlx_lm': runtime.get('mlx_lm'), 'precision': runtime.get('precision'),
                  'temperature': state['model_config'].get('temperature'),
                  'max_new_tokens': state['model_config'].get('max_new_tokens'),
                  'host': 'Apple M3, 16 GiB unified memory',
                  'paper_equivalence': False},
        'qualification': {'passed': qualification.get('passed'),
                          'checks': [(c['name'], c['passed']) for c in qualification.get('checks', [])],
                          'scope': qualification.get('scope')},
        'stages': {
            'SliceMin': {'status': 'executed_on_recovered_source',
                         'tools_sliced': len(slices),
                         'entry_registration_pattern': sum(1 for t in slices.values() if t.get('entry_resolution') == 'registration_pattern'),
                         'entry_explicit_name_match': sum(1 for t in slices.values() if t.get('entry_resolution') == 'explicit_name_match'),
                         'total_functions': sum(t.get('functions', 0) for t in slices.values()),
                         'total_edges': sum(t.get('edges', 0) for t in slices.values()),
                         'total_unresolved_calls': sum(t.get('unresolved_calls', 0) for t in slices.values()),
                         'debloating': 'not_applied_static_only',
                         'limit': 'Python only; TypeScript/JavaScript unsupported'},
            'DescGen': {'status': 'executed_real_local_model',
                        'attempted': len(results), 'generated': len(generated), 'failed': len(failed),
                        'valid_structure_rate_percent': round(100 * len(generated) / len(results), 1) if results else None,
                        'failure_types': dict(Counter(r.get('error_type', 'unknown') for r in failed)),
                        'median_seconds': round(statistics.median(timing), 2) if timing else None,
                        'max_seconds': round(max(timing), 2) if timing else None,
                        'note': 'sanitize + description; each rejected output is preserved raw'},
            'DynVer': {'status': 'blocked',
                       'reason': ('executing third-party MCP tool code is gated in this implementation; '
                                  'no validated isolated runner or task set exists for these servers'),
                       'claims_judged': 0},
        },
        'per_server': [{'server': k, **v} for k, v in sorted(per_server.items())],
        'per_tool': results,
        'paper_comparison': {
            'paper_TSR_original_percent': 84.1, 'paper_TSR_full_percent': 87.7,
            'paper_TSR_lite_percent': 86.3,
            'our_TSR': None,
            'reason': ('no recovered task texts or human labels, so TSR cannot be computed; '
                       'reporting a number here would be fabrication'),
        },
    }
    (ROOT / 'EXPERIMENT_RESULTS.json').write_text(json.dumps(experiment, indent=2) + '\n')

    # Tool-level CSV (no task rows exist for this corpus)
    csv_path = ROOT / 'RESULTS_recovered_tools.csv'
    with csv_path.open('w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(['record_type', 'server', 'tool_id', 'entry_resolution', 'slice_functions',
                         'slice_edges', 'unresolved_calls', 'descgen_status', 'seconds', 'error_type'])
        for r in results:
            s = slices.get(r['id'], {})
            writer.writerow(['description_generation', r['server'], r['id'],
                             s.get('entry_resolution'), s.get('functions'), s.get('edges'),
                             s.get('unresolved_calls'), r['status'], r.get('seconds'),
                             r.get('error_type', '')])

    # Task CSV: reuse the authored-fixture task rows, labelled by corpus.
    src = FIXTURE_RUN / 'task_results.csv'
    if src.exists():
        with src.open(newline='') as inf, (ROOT / 'TASK_RESULTS.csv').open('w', newline='') as outf:
            reader = list(csv.reader(inf))
            writer = csv.writer(outf)
            writer.writerow(['corpus'] + reader[0])
            for row in reader[1:]:
                writer.writerow(['authored_fixture_software_check'] + row)

    viz = ROOT / 'RESULTS_VISUALIZATION'
    viz.mkdir(exist_ok=True)
    rows = [(k, v['generated'], v['attempted']) for k, v in sorted(per_server.items())]
    (viz / 'descgen_by_server.svg').write_text(svg_bar('DescGen valid structured output per server (real local model)', rows))
    (viz / 'viz_manifest.json').write_text(json.dumps({
        'generated_utc': now,
        'charts': [{'file': 'descgen_by_server.svg',
                    'data': [{'server': k, 'generated': v['generated'], 'attempted': v['attempted']}
                             for k, v in sorted(per_server.items())],
                    'caption': 'Counts of valid structured descriptions; failures are model format rejections.'}],
        'not_plotted': ['TSR by condition', 'runtime overhead', 'tool-selection rate', 'adaptive-attack trajectory'],
        'reason': 'no recovered task set, labels or attack fixtures; plotting them would require fabricated data',
    }, indent=2) + '\n')

    # Metrics report
    lines = ['# Metrics report', '', f'Generated {now}.', '',
             '## Scope', '',
             'Two separate evidence tracks are kept apart and never pooled:', '',
             '| Track | Corpus | Tasks | Status |', '|---|---|---|---|',
             '| A. Authored fixture software check | 2 authored tools, 8 authored tasks | 8 | executed (earlier run, preserved) |',
             f'| B. Recovered public source | {len(bench["tools"])} Python tools from 12 paper-named servers | 0 | '
             'SliceMin + DescGen executed; DynVer blocked |', '',
             'Track A is a software/agent check. Track B is a real-source supplementary experiment. Neither is '
             'the paper\'s 52-tool / 208-task benchmark.', '',
             '## Track B: SliceMin on recovered real source', '',
             '| Metric | Value |', '|---|---|',
             f'| Tools sliced | {len(slices)} |',
             f'| Entry via registration pattern | {experiment["stages"]["SliceMin"]["entry_registration_pattern"]} |',
             f'| Entry via explicit module-qualified match | {experiment["stages"]["SliceMin"]["entry_explicit_name_match"]} |',
             f'| Functions retained across slices | {experiment["stages"]["SliceMin"]["total_functions"]} |',
             f'| Internal call edges | {experiment["stages"]["SliceMin"]["total_edges"]} |',
             f'| Unresolved (external/unexpanded) calls | {experiment["stages"]["SliceMin"]["total_unresolved_calls"]} |',
             f'| Tools in unsupported languages (JavaScript/TypeScript) | {52 - len(bench["tools"])} |', '',
             'SliceMin ran static-only: LLM debloating was not applied, so slices are over-approximate.', '',
             '## Track B: DescGen with the local model', '',
             f"Model: `{runtime.get('model_id')}` at revision `{runtime.get('revision')}`, "
             f"MLX {runtime.get('mlx')} / MLX-LM {runtime.get('mlx_lm')}, temperature "
             f"{state['model_config'].get('temperature')}. Qualification: "
             f"{'passed' if qualification.get('passed') else 'failed'}.", '',
             '| Metric | Value |', '|---|---|',
             f'| Tools attempted | {len(results)} |', f'| Valid structured descriptions | {len(generated)} |',
             f'| Rejected by the validator | {len(failed)} |',
             f'| Valid-structure rate | {experiment["stages"]["DescGen"]["valid_structure_rate_percent"]}% |',
             f'| Median seconds per tool | {experiment["stages"]["DescGen"]["median_seconds"]} |',
             f'| Max seconds per tool | {experiment["stages"]["DescGen"]["max_seconds"]} |', '',
             '| Server | Generated / attempted |', '|---|---|']
    for k, v in sorted(per_server.items()):
        lines.append(f"| {k} | {v['generated']} / {v['attempted']} |")
    lines += ['', '## What is deliberately null', '',
              '| Paper quantity | Our value | Why |', '|---|---|---|',
              '| Q1 task success rate (TSR) | — | no recovered task texts or human labels |',
              '| Q2 generation cost / latency | — | paid providers were not used; local weights are unpriced |',
              '| Q3 degraded-tool selection rate | — | no recovered degradation variants or task set |',
              '| Q4 TPA blocking | — | no recovered attack fixtures with author outcomes |',
              '| Q5 adaptive-attack trajectory | — | authors printed only fit statistics, not per-iteration data |', '',
              'Reference values from the paper (not our measurements): TSR 84.1% original, 86.3% lite, 87.7% full; '
              'Gemini-3-Flash generation $0.013 / 25.7 s per tool; adaptive selection 44.7–67.4% over 15 iterations.', '',
              '## Track A: authored fixture results (preserved, unchanged)', '',
              '| Condition | Exact tool objectives | Agent completed | Oracle rate |', '|---|---|---|---|',
              '| original | 6/8 | 7/8 | 75.0% |', '| lite | 6/8 | 6/8 | 75.0% |',
              '| full | 6/8 | 3/8 | 75.0% |', '',
              'These are eight authored tasks over two authored tools with an exact-trace oracle; they show no '
              'measured improvement and are not evidence about the paper\'s benchmark.']
    (ROOT / 'METRICS_REPORT.md').write_text('\n'.join(lines) + '\n')

    # Failure analysis
    types = Counter(r.get('error_type', 'unknown') for r in failed)
    lines = ['# Failure analysis', '', f'Generated {now}.', '',
             'Failures are reported as observed. None were retried into a different semantic path, and no '
             'scripted description was substituted for model output.', '',
             '## B1. DescGen structural rejections (real model, recovered source)', '',
             '| Failure type | Count | Cause |', '|---|---|---|',
             f'| `ValidationError` | {types.get("ValidationError", 0)} | the generated JSON did not satisfy the '
             'claim-coverage rule (every summary, functionality and schema description needs exactly one matching claim) |',
             f'| `ModelError` | {types.get("ModelError", 0)} | output was not the required single JSON object, or '
             'the generation deadline/length limit was hit |',
             f'| other | {sum(v for k, v in types.items() if k not in {"ValidationError", "ModelError"})} | '
             'worker or slice lookup issue; see per-tool records |', '',
             'Raw rejected outputs are preserved in `reports/recovered_descgen/model_calls.json` and '
             '`run_state.json`, so the rejection can be audited rather than trusted.', '',
             'The dominant cause is model capability at the required structure, not an unreachable code path: '
             'the same binary passes the qualification suite (arithmetic, structured JSON, exact tool action) and '
             'the same validator accepted descriptions for the small authored fixture tools.', '',
             '## B2. Stage-level blockers', '',
             '| Blocker | Effect | Mitigation taken |', '|---|---|---|',
             '| DynVer needs to execute third-party tool code | no behavioural claim adjudication on recovered tools | '
             'stage recorded as blocked; authored-fixture DynVer evidence preserved |',
             '| TypeScript/JavaScript unsupported | 22 of the paper\'s 52 tool slots cannot be sliced | recorded per server; no substitution |',
             '| Original artifact expired (HTTP 410) | no exact benchmark | independent corpus built and labelled |',
             '| Current HEAD ≠ paper revision | tool sets and code differ from the paper\'s snapshot | commit pinned and disclosed per server |',
             '| LLM debloating not applied | slices over-approximate; descriptions may mention unreachable logic | '
             '`mode: static_only_no_debloating` recorded in every slice |', '',
             '## B3. Slice quality caveats', '',
             '- Class and instance method bodies are retained as context but resolved statically only; nested '
             'helpers appear as unresolved calls.',
             '- excel-mcp-server slices are small because its tool bodies delegate to helper modules and '
             'workspace objects that the resolver does not expand; a description built from them is necessarily thin.',
             '- Unresolved-call counts per tool are recorded, so the reader can see how much behaviour is outside '
             'the slice rather than assuming completeness.', '',
             '## B4. What would change the conclusion', '',
             '1. Author release of the 52-tool list, 208 tasks, prompts and labels.',
             '2. A validated isolated runner for third-party MCP execution, enabling DynVer on real tools.',
             '3. TypeScript parsing, which would cover the remaining 22 tool slots.']
    (ROOT / 'FAILURE_ANALYSIS.md').write_text('\n'.join(lines) + '\n')
    print(f"generated {len(generated)}/{len(results)}; wrote EXPERIMENT_RESULTS.json, METRICS_REPORT.md, "
          f"FAILURE_ANALYSIS.md, RESULTS_recovered_tools.csv, RESULTS_VISUALIZATION/")


if __name__ == '__main__':
    main()
