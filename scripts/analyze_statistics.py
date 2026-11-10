#!/usr/bin/env python3
"""Descriptive statistics for the recovered-corpus pilot.

Every statistic here is computed from recorded evidence. The script also states
what it refuses to compute (paired tests, equivalence tests) and why.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports'


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (float('nan'), float('nan'), float('nan'))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def describe(values):
    vals = sorted(values)
    n = len(vals)
    if not n:
        return {}
    mid = n // 2
    median = vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / (n - 1) if n > 1 else 0.0
    return {'n': n, 'median': round(median, 2), 'mean': round(mean, 2),
            'stdev': round(math.sqrt(var), 2), 'min': round(vals[0], 2), 'max': round(vals[-1], 2),
            'total': round(sum(vals), 2)}


def classify(error: str) -> str:
    text = error.lower()
    if 'beyond configured cap' in text:
        return 'input over token cap'
    if 'generation deadline' in text:
        return 'generation deadline'
    if 'identifier normalization' in text:
        return 'identifier normalisation rejected'
    if 'input_schema' in text or 'argument names disagree' in text:
        return 'schema/argument validation'
    return 'other model error'


def main():
    descgen = json.loads((ROOT / 'reports/recovered_descgen/run_state.json').read_text())
    dyn = json.loads((ROOT / 'reports/dynver_recovered/results.json').read_text())
    bench = json.loads((ROOT / 'data/manifests/recovered_benchmark.json').read_text())

    attempts = len(descgen['results'])
    valid = [r for r in descgen['results'] if r['status'] == 'generated']
    failures = Counter(classify(f['error']) for f in descgen['failures'])
    y_p, y_lo, y_hi = wilson(len(valid), attempts)

    units = dyn['units']
    verdict_counts = Counter(u['verdict'] for u in units)
    s_p, s_lo, s_hi = wilson(verdict_counts['supported'], len(units))

    per_condition = {}
    for condition in ('original', 'full', 'lite'):
        bucket = Counter(u['verdict'] for u in units if u['condition'] == condition)
        total = sum(bucket.values())
        p, lo, hi = wilson(bucket.get('supported', 0), total)
        per_condition[condition] = {
            'units': total,
            'supported': bucket.get('supported', 0),
            'refuted': bucket.get('refuted', 0),
            'inconclusive': bucket.get('inconclusive', 0),
            'supported_rate': round(p, 4),
            'wilson_95': [round(lo, 4), round(hi, 4)],
        }

    per_tool = {}
    for tool in sorted({u['tool_id'] for u in units}):
        bucket = Counter(u['verdict'] for u in units if u['tool_id'] == tool)
        per_tool[tool] = {'units': sum(bucket.values()), **{k: bucket.get(k, 0) for k in
                                                            ('supported', 'refuted', 'inconclusive')}}

    # Are the generated tasks the same across conditions? This decides whether a
    # paired test by task index would even be meaningful.
    task_texts = defaultdict(dict)
    for unit in units:
        task_texts[unit['task_index']][unit['condition']] = json.dumps(unit['task'], sort_keys=True)
    identical_across_conditions = all(len(set(v.values())) == 1 for v in task_texts.values())

    # Exact per-(tool, task) agreement between conditions, reported only as raw counts.
    lookup = {(u['tool_id'], u['task_index'], u['condition']): u['verdict'] for u in units}
    keys = sorted({(u['tool_id'], u['task_index']) for u in units})
    pairs = {}
    for a, b in (('original', 'full'), ('original', 'lite'), ('full', 'lite')):
        same = sum(1 for k in keys if lookup.get((k[0], k[1], a)) == lookup.get((k[0], k[1], b)))
        pairs[f'{a}_vs_{b}'] = {'cells': len(keys), 'identical_verdicts': same,
                                'agreement': round(same / len(keys), 4)}

    gen_seconds = [r['seconds'] for r in valid]
    fail_seconds = [f['seconds'] for f in descgen['failures']]
    claims_per_description = Counter(len(r['description'].get('claims', [])) for r in valid)
    dyn_seconds = [u['seconds'] for u in units]
    process_status = Counter(u['process_status'] for u in units)
    observation_status = Counter((u.get('observation') or {}).get('status') for u in units)

    coverage = bench['coverage']
    results = {
        'generated_utc': dyn['generated_utc'],
        'scope_note': ('Descriptive statistics for an independently collected pilot corpus. '
                       'The paper 208-task benchmark was not recovered; no metric here is the '
                       'paper TSR.'),
        'descgen': {
            'attempts': attempts,
            'valid': len(valid),
            'rejected': attempts - len(valid),
            'yield': round(y_p, 4),
            'yield_wilson_95': [round(y_lo, 4), round(y_hi, 4)],
            'failure_categories': dict(failures),
            'failure_shares': {k: round(v / (attempts - len(valid)), 4) for k, v in failures.items()},
            'valid_seconds': describe(gen_seconds),
            'failed_seconds': describe(fail_seconds),
            'model_seconds_total': round(sum(gen_seconds) + sum(fail_seconds), 1),
            'claims_per_description': dict(sorted(claims_per_description.items())),
            'claims_total': sum(len(r['description'].get('claims', [])) for r in valid),
        },
        'corpus': {
            'servers_recovered': len(bench['servers']),
            'tools_selected': len(bench['tools']),
            'tools_sliced': sum(c['sliced'] for c in coverage),
            'unsupported_slots': sum(max((s.get('paper', {}).get('selected_count') or 0)
                                         - next(c['sliced'] for c in coverage if c['server'] == s['server']), 0)
                                     for s in bench['servers']),
        },
        'dynver': {
            'units': len(units),
            'tools': len({u['tool_id'] for u in units}),
            'tasks_per_condition': {c: sorted({u['task_index'] for u in units if u['condition'] == c})
                                    for c in ('original', 'full', 'lite')},
            'verdicts': dict(verdict_counts),
            'supported_rate': round(s_p, 4),
            'supported_rate_wilson_95': [round(s_lo, 4), round(s_hi, 4)],
            'per_condition': per_condition,
            'per_tool': per_tool,
            'execution_seconds': describe(dyn_seconds),
            'process_status': dict(process_status),
            'observation_status': dict(observation_status),
            'tasks_identical_across_conditions': identical_across_conditions,
            'cross_condition_cells': pairs,
        },
        'inference': {
            'paired_test_performed': False,
            'paired_test_reason': ('Each condition generated its own tasks; identical task indices are '
                                   'not the same task, so a paired test would be invalid.'
                                   if not identical_across_conditions else
                                   'Paired cells exist but n = 6 per condition is too small to support '
                                   'inference about separation.'),
            'equivalence_claim': False,
            'equivalence_reason': ('Identical counts are not evidence of equivalence. With n = 6 per '
                                   'condition, the confidence intervals are wide enough to contain '
                                   'materially different true rates.'),
            'significance_claimed': False,
        },
        'power_note': ('Detecting a 20 percentage-point difference at 80% power would need roughly '
                       '90 independent units per condition; the pilot has 6.'),
    }

    (OUT / 'STATISTICAL_RESULTS.json').write_text(json.dumps(results, indent=2) + '\n')

    rows = []

    def add(scope, metric, value, n, low='', high='', note=''):
        rows.append({'scope': scope, 'metric': metric, 'value': value, 'n': n,
                     'ci95_low': low, 'ci95_high': high, 'note': note})

    add('DescGen', 'valid_description_yield', results['descgen']['yield'], attempts,
        y_lo, y_hi, 'Wilson interval')
    for category, count in failures.items():
        p, lo, hi = wilson(count, attempts - len(valid))
        add('DescGen', f'rejected_share::{category}', round(p, 4), attempts - len(valid),
            round(lo, 4), round(hi, 4), 'share of rejected attempts')
    for key, value in results['descgen']['valid_seconds'].items():
        add('DescGen', f'valid_generation_seconds::{key}', value, len(gen_seconds))
    add('DynVer', 'supported_rate', results['dynver']['supported_rate'], len(units), s_lo, s_hi,
        'Wilson interval; 18 units, not independent tasks')
    for condition, stats in per_condition.items():
        add('DynVer', f'supported_rate::{condition}', stats['supported_rate'], stats['units'],
            stats['wilson_95'][0], stats['wilson_95'][1], 'Wilson interval')
    for tool, stats in per_tool.items():
        add('DynVer', f'supported::{tool}', stats['supported'], stats['units'], '', '',
            f"refuted={stats['refuted']}, inconclusive={stats['inconclusive']}")
    for pair, stats in pairs.items():
        add('Agreement', f'identical_verdict_cells::{pair}', stats['agreement'], stats['cells'], '', '',
            'descriptive only; tasks differ across conditions')
    for key, value in results['dynver']['execution_seconds'].items():
        add('DynVer', f'execution_seconds::{key}', value, len(dyn_seconds))
    add('Corpus', 'tools_sliced', results['corpus']['tools_sliced'], results['corpus']['tools_selected'],
        '', '', 'Python slots only')
    add('Corpus', 'unsupported_slots', results['corpus']['unsupported_slots'], results['corpus']['tools_selected'],
        '', '', 'TypeScript/JavaScript')

    with (OUT / 'STATISTICAL_RESULTS.csv').open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({'descgen_yield': results['descgen']['yield'],
                      'dynver': {k: v['supported_rate'] for k, v in per_condition.items()},
                      'identical_tasks': identical_across_conditions,
                      'agreement': pairs}, indent=1))


if __name__ == '__main__':
    main()
