#!/usr/bin/env python3
"""Analysis and figures for the matched-task and poisoning experiments.

Validity is decided before any comparison: a task is only eligible if its
observation reflects the call it claims to test. Tasks whose setup calls ran in a
different temporary directory are excluded and marked unsupported, never counted.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / 'reports/new_experiments'
FIG = ROOT / 'reports/figures'
DATA = FIG / 'figure_data'
DPI = 300

INK = '#1b2a41'; MUTED = '#6b7a8f'; GRID = '#dde3ea'
OK = '#2f7d5d'; BAD = '#b03a3a'; NEUTRAL = '#c2a24a'; ACCENT = '#3f6fb5'; LIGHT = '#e8eef6'

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9.5, 'axes.titlesize': 11,
                     'axes.titleweight': 'bold', 'axes.labelsize': 9.5, 'axes.edgecolor': MUTED,
                     'axes.linewidth': 0.7, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
                     'text.color': INK, 'figure.dpi': DPI, 'savefig.dpi': DPI})

# Tasks whose observation depends on state that could not persist across sandbox calls.
INVALID_TASKS = {
    'T2-watch-update': 'setup call ran in a separate temporary directory; the observed call '
                       'created a watch instead of updating one',
    'T4-list-one': 'setup call ran in a separate temporary directory; listing saw empty state',
    'T5-unwatch-existing': 'setup call ran in a separate temporary directory; removal could '
                           'not be attempted on an existing watch',
}


def main():
    matched = json.loads((EXP / 'matched_comparison.json').read_text())
    poison = json.loads((EXP / 'poisoning_detection.json').read_text())

    tasks = {t['task']['id']: t for t in matched['tasks']}
    valid_ids = [tid for tid in tasks if tid not in INVALID_TASKS]
    groups = defaultdict(list)
    for row in matched['judgements']:
        groups[row['condition']].append(row)

    condition_summary = {}
    for condition, rows in groups.items():
        valid = [r for r in rows if r['task_id'] in valid_ids]
        condition_summary[condition] = {
            'judged_cells_total': len(rows),
            'valid_cells': len(valid),
            'consistent': sum(r['verdict'] == 'consistent' for r in valid),
            'contradicted': sum(r['verdict'] == 'contradicted' for r in valid),
            'inconclusive': sum(r['verdict'] == 'inconclusive' for r in valid),
            'model_errors': sum(bool(r.get('model_error')) for r in valid),
        }

    per_task = {}
    for tid in valid_ids:
        per_task[tid] = {c: next((r['verdict'] for r in groups[c] if r['task_id'] == tid), 'missing')
                         for c in ('original', 'full', 'lite')}

    # Poisoning metrics over detection-eligible cases only.
    eligible = [c for c in poison['cases'] if c['detection_supported']]
    tp = sum(1 for c in eligible if c['ground_truth'] == 'poisoned' and c['detected'] is True)
    fn = sum(1 for c in eligible if c['ground_truth'] == 'poisoned' and c['detected'] is False)
    fp = sum(1 for c in eligible if c['ground_truth'] == 'benign' and c['detected'] is True)
    tn = sum(1 for c in eligible if c['ground_truth'] == 'benign' and c['detected'] is False)
    unsupported = [c for c in poison['cases'] if not c['detection_supported']]
    by_category = {}
    for c in poison['cases']:
        bucket = by_category.setdefault(c['category'], {'cases': 0, 'detected': 0,
                                                        'not_detected': 0, 'unsupported': 0})
        bucket['cases'] += 1
        if not c['detection_supported']:
            bucket['unsupported'] += 1
        elif c['detected']:
            bucket['detected'] += 1
        else:
            bucket['not_detected'] += 1

    metrics = {
        'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
        'detection_rate': round(tp / (tp + fn), 4) if tp + fn else None,
        'false_positive_rate': round(fp / (fp + tn), 4) if fp + tn else None,
        'unsupported_cases': len(unsupported),
        'eligible_cases': len(eligible),
        'total_cases': len(poison['cases']),
    }

    results = {
        'generated_utc': matched['generated_utc'],
        'classification': 'new experiments on recovered tools; synthetic ground truth where stated',
        'execution_backend': 'macOS Seatbelt, fresh temporary directory per execution',
        'experiment_a_matched_tasks': {
            'design': ('six authored tasks; one sandbox execution per task; the identical '
                       'observation judged against three descriptions, blind to condition'),
            'executions': len(matched['tasks']),
            'judgements': len(matched['judgements']),
            'valid_cells': sum(v['valid_cells'] for v in condition_summary.values()),
            'invalid_tasks': INVALID_TASKS,
            'conditions': condition_summary,
            'per_task': per_task,
            'separation_observed': len({(v['consistent'], v['contradicted'])
                                        for v in condition_summary.values()}) > 1,
        },
        'experiment_b_poisoning': {
            'design': ('12 synthetic descriptions with author labels; each claim executed as a '
                       'fixed task in the sandbox, then judged by the implemented path'),
            'metrics': metrics,
            'by_category': by_category,
            'false_negative_cases': [c['case_id'] for c in eligible
                                     if c['ground_truth'] == 'poisoned' and c['detected'] is False],
            'false_positive_cases': [c['case_id'] for c in eligible
                                     if c['ground_truth'] == 'benign' and c['detected'] is True],
            'unsupported_cases': [c['case_id'] for c in unsupported],
            'claim_verdicts': dict(Counter(c['claim_verdict'] for c in poison['cases'])),
        },
        'cannot_conclude': [
            'detection of prompt injection: no injection detector exists in this pipeline',
            'generalisation of the poisoning result: 9 eligible cases, 1 tool server',
            'any task success rate or comparison with the paper benchmark',
            'that identical matched verdicts mean the descriptions are equivalent',
        ],
    }
    (ROOT / 'reports/NEW_EXPERIMENT_RESULTS.json').write_text(json.dumps(results, indent=2) + '\n')

    rows = []
    for c in ('original', 'full', 'lite'):
        s = condition_summary[c]
        rows.append({'experiment': 'A_matched', 'unit': c, 'metric': 'consistent',
                     'value': s['consistent'], 'denominator': s['valid_cells'],
                     'note': 'valid single-call tasks only'})
        rows.append({'experiment': 'A_matched', 'unit': c, 'metric': 'contradicted',
                     'value': s['contradicted'], 'denominator': s['valid_cells'], 'note': ''})
    for key, value in metrics.items():
        rows.append({'experiment': 'B_poisoning', 'unit': 'all_eligible', 'metric': key,
                     'value': value, 'denominator': metrics['eligible_cases'],
                     'note': 'injection cases excluded as unsupported'})
    for category, bucket in by_category.items():
        rows.append({'experiment': 'B_poisoning', 'unit': category, 'metric': 'detected',
                     'value': bucket['detected'], 'denominator': bucket['cases'],
                     'note': f"unsupported={bucket['unsupported']}"})
    with (ROOT / 'reports/NEW_EXPERIMENT_RESULTS.csv').open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    DATA.mkdir(parents=True, exist_ok=True)
    # ---------------------------------------------------------------- figure 9
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.6, 4.4), gridspec_kw={'width_ratios': [1, 1.5]})
    conds = ['original', 'full', 'lite']
    width = 0.26
    for j, (verdict, colour) in enumerate((('consistent', OK), ('contradicted', BAD))):
        vals = [condition_summary[c][verdict] for c in conds]
        bars = ax.bar(np.arange(3) + (j - 0.5) * width, vals, width=width, color=colour, label=verdict)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.06, str(v), ha='center', fontsize=9)
    ax.set_xticks(np.arange(3)); ax.set_xticklabels(conds)
    ax.set_ylim(0, 3.6); ax.set_ylabel('matched tasks')
    ax.set_title('(a) Same task, same observation', loc='left')
    ax.legend(frameon=False, fontsize=8.5, loc='upper center', ncol=2,
              bbox_to_anchor=(0.5, -0.12))
    ax.grid(axis='x', visible=False)

    ids = sorted(per_task)
    verdict_code = {'consistent': 1.0, 'contradicted': 0.0, 'inconclusive': 0.5, 'missing': np.nan}
    grid = np.array([[verdict_code[per_task[t][c]] for c in conds] for t in ids])
    ax2.imshow(grid, cmap=matplotlib.colors.ListedColormap([BAD, NEUTRAL, OK]), vmin=0, vmax=1,
               aspect='auto')
    ax2.set_xticks(range(3)); ax2.set_xticklabels(conds)
    ax2.set_yticks(range(len(ids)))
    ax2.set_yticklabels([i.split('-', 1)[1].replace('-', ' ') for i in ids], fontsize=8.5)
    ax2.grid(False)
    for i in range(len(ids)):
        for j in range(3):
            v = per_task[ids[i]][conds[j]]
            ax2.text(j, i, 'C' if v == 'consistent' else ('X' if v == 'contradicted' else '?'),
                     ha='center', va='center', color='white', weight='bold', fontsize=9)
    ax2.set_title('(b) Per-task verdicts', loc='left')
    fig.suptitle('Figure 9 — Matched-task comparison (new experiment, paired by task)',
                 x=0.02, ha='left', fontsize=12.5, weight='bold')
    fig.text(0.005, -0.055, 'source: reports/new_experiments/matched_comparison.json — '
             '3 invalid stateful tasks excluded (setup state cannot cross sandbox calls)',
             fontsize=6.6, color=MUTED, ha='left', va='top')
    for ext in ('png', 'pdf'):
        fig.savefig(FIG / f'fig9_matched_comparison.{ext}', bbox_inches='tight', facecolor='white')
    plt.close(fig)
    with (DATA / 'fig9_matched_comparison.csv').open('w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['task_id'] + conds)
        for t in ids:
            w.writerow([t] + [per_task[t][c] for c in conds])

    # ---------------------------------------------------------------- figure 10
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.6, 4.3), gridspec_kw={'width_ratios': [1, 1.35]})
    matrix = np.array([[tn, fp], [fn, tp]])  # rows: benign/poisoned truth; cols: not detected/detected
    ax.imshow(matrix, cmap='Blues', aspect='auto')
    labels = [['TN', 'FP'], ['FN', 'TP']]
    for i in range(2):
        for j in range(2):
            value = matrix[i, j]
            ax.text(j, i, f'{labels[i][j]}\n{value}', ha='center', va='center', fontsize=13,
                    color='white' if value > matrix.max() / 2 else INK, weight='bold')
    ax.set_xticks([0, 1]); ax.set_xticklabels(['not detected', 'detected'])
    ax.set_yticks([0, 1]); ax.set_yticklabels(['benign', 'poisoned'])
    ax.grid(False)
    ax.set_title('(a) Detection confusion (9 eligible cases)', loc='left')


    cats = ['benign', 'false_functionality', 'misleading_side_effect', 'embedded_instruction']
    pretty = ['benign\n(control)', 'false\nfunctionality', 'misleading\nside effect', 'embedded\ninstruction']
    det = [by_category.get(c, {}).get('detected', 0) for c in cats]
    miss = [by_category.get(c, {}).get('not_detected', 0) for c in cats]
    uns = [by_category.get(c, {}).get('unsupported', 0) for c in cats]
    x = np.arange(len(cats))
    ax2.bar(x, det, color=OK, width=0.55, label='flagged / refuted')
    ax2.bar(x, miss, bottom=det, color=NEUTRAL, width=0.55, label='not flagged (false negative)')
    ax2.bar(x, uns, bottom=np.array(det) + np.array(miss), color=LIGHT, width=0.55,
            edgecolor=MUTED, linewidth=0.6, label='unsupported (no detector)')
    for i, (d, m, u) in enumerate(zip(det, miss, uns)):
        total = d + m + u
        ax2.text(i, total + 0.08, f'{total}', ha='center', fontsize=9, color=INK)
    ax2.set_xticks(x); ax2.set_xticklabels(pretty, fontsize=8.3)
    ax2.set_ylim(0, 4.2); ax2.set_ylabel('cases')
    ax2.grid(axis='x', visible=False)
    ax2.legend(frameon=False, fontsize=7.8, loc='upper right')
    ax2.set_title('(b) Outcome by poison category', loc='left')
    fig.suptitle('Figure 10 — Controlled poisoning detection (synthetic, author-labelled)',
                 x=0.02, ha='left', fontsize=12.5, weight='bold')
    fig.text(0.005, -0.07, f'source: reports/new_experiments/poisoning_detection.json — TP {tp}, FN {fn}, TN {tn}, FP {fp}; '
             f'3 injection cases unsupported, not detections',
             fontsize=6.6, color=MUTED, ha='left', va='top')
    for ext in ('png', 'pdf'):
        fig.savefig(FIG / f'fig10_poisoning_detection.{ext}', bbox_inches='tight', facecolor='white')
    plt.close(fig)
    with (DATA / 'fig10_poisoning_detection.csv').open('w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['category', 'flagged', 'not_flagged', 'unsupported'])
        for c, d, m, u in zip(cats, det, miss, uns):
            w.writerow([c, d, m, u])

    print(json.dumps({'conditions': condition_summary, 'metrics': metrics,
                      'by_category': by_category,
                      'false_negatives': results['experiment_b_poisoning']['false_negative_cases']},
                     indent=1))


if __name__ == '__main__':
    main()
