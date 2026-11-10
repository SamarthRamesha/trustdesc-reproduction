#!/usr/bin/env python3
"""Re-judge recorded claims with the negation-aware layer, score the injection
screen, and draw figures 11-12. Reads recorded evidence only; executes nothing."""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

from trustdesc.dynver.negation import combine, polarity  # noqa: E402
from trustdesc.injection_detector import screen  # noqa: E402

FIG = ROOT / 'reports' / 'figures'
DATA = ROOT / 'reports' / 'figure_data'
INK, MUTED, GREEN, RED, AMBER, GREY = '#1f2933', '#6b7280', '#2f7d5f', '#b23a48', '#c08a3e', '#cbd2d9'

poison = json.loads((ROOT / 'reports/new_experiments/poisoning_detection.json').read_text())
cases = poison['cases']

# ---------------------------------------------------------------- experiment 1
rows = []
for c in cases:
    obs = {'status': c['observation_status'], 'files': c['observation_files']}
    fixed = combine(c['synthetic_description_claim'], obs, c['claim_verdict'], c['reason'])
    rows.append({'case_id': c['case_id'], 'category': c['category'],
                 'claim': c['synthetic_description_claim'],
                 'polarity': fixed['polarity'],
                 'old_verdict': c['claim_verdict'], 'new_verdict': fixed['verdict'],
                 'source': fixed['source'], 'rule': fixed['rule'],
                 'overrode': fixed['overrode'],
                 'new_detected': (None if c['detected'] is None else fixed['verdict'] == 'refuted'),
                 'old_detected': c['detected']})

changed = [r for r in rows if r['new_verdict'] != r['old_verdict']]

# polarity handling table (behaviour of the deterministic layer on probe claims)
probe_claims = [
    ('positive existence, present', 'Creating a watch writes ./watched_topics.json.',
     {'status': 'ok', 'files': {'./watched_topics.json': '{}'}}),
    ('positive existence, absent', 'Creating a watch writes ./watched_topics.json.',
     {'status': 'ok', 'files': {}}),
    ('negated existence, file present', 'No file is created by creating a watch.',
     {'status': 'ok', 'files': {'./watched_topics.json': '{}'}}),
    ('negated path claim, file present', 'The tool does not write ./watched_topics.json.',
     {'status': 'ok', 'files': {'./watched_topics.json': '{}'}}),
    ('negated path claim, file absent', 'The tool does not write ./watched_topics.json.',
     {'status': 'ok', 'files': {}}),
    ('double negative', 'It is not true that no file is created by creating a watch.',
     {'status': 'ok', 'files': {'./watched_topics.json': '{}'}}),
    ('ambiguous (three cues)', 'It is not never the case that no file is created.',
     {'status': 'ok', 'files': {}}),
    ('non-existence claim', 'The call returns a success message.',
     {'status': 'ok', 'files': {'./watched_topics.json': '{}'}}),
    ('missing evidence', 'Creating a watch writes ./watched_topics.json.',
     {'status': 'ok'}),
]
probes = []
for name, claim, obs in probe_claims:
    d = combine(claim, obs, 'supported', 'model said supported')
    probes.append({'probe': name, 'claim': claim, 'polarity': d['polarity'],
                   'verdict': d['verdict'], 'source': d['source'], 'rule': d['rule'],
                   'defers_to_model': d['source'] == 'model'})

# ---------------------------------------------------------------- experiment 2
ds = json.loads((ROOT / 'data/experiments/synthetic_injection_cases.json').read_text())
screened = []
for case in ds['cases']:
    result = screen(case['text'])
    screened.append({**{k: case[k] for k in ('case_id', 'label', 'category', 'text', 'rationale',
                                              'provenance')},
                     'flagged': result['flagged'], 'rules_fired': result['rules_fired'],
                     'findings': result['findings'], 'suppressed': result['suppressed']})

tp = sum(1 for s in screened if s['label'] == 'malicious' and s['flagged'])
fn = sum(1 for s in screened if s['label'] == 'malicious' and not s['flagged'])
tn = sum(1 for s in screened if s['label'] == 'benign' and not s['flagged'])
fp = sum(1 for s in screened if s['label'] == 'benign' and s['flagged'])
amb = [s for s in screened if s['label'] == 'ambiguous']
precision = tp / (tp + fp) if tp + fp else None
recall = tp / (tp + fn) if tp + fn else None
f1 = (2 * precision * recall / (precision + recall)) if precision and recall else None

by_rule = {}
for s in screened:
    for rule in s['rules_fired']:
        by_rule[rule] = by_rule.get(rule, 0) + 1

neg_metrics = {
    'recorded_cases': len(rows),
    'verdicts_changed': len(changed),
    'changed_cases': changed,
    'detection_before': {'tp': 5, 'fn': 1, 'tn': 3, 'fp': 0},
    'detection_after': {
        'tp': sum(1 for r in rows if r['category'] != 'benign' and r['old_detected'] is not None
                  and r['new_verdict'] == 'refuted'),
        'fn': sum(1 for r in rows if r['category'] != 'benign' and r['old_detected'] is not None
                  and r['new_verdict'] != 'refuted'),
        'tn': sum(1 for r in rows if r['category'] == 'benign' and r['new_verdict'] != 'refuted'),
        'fp': sum(1 for r in rows if r['category'] == 'benign' and r['new_verdict'] == 'refuted'),
        'eligible': sum(1 for r in rows if r['old_detected'] is not None),
        'unsupported': sum(1 for r in rows if r['old_detected'] is None),
    },
    'deterministic_overrides': sum(1 for r in rows if r['source'] == 'deterministic'),
    'probes': probes,
}

neg = {
    'schema_version': 1,
    'note': ('Re-judging of recorded evidence only; no new executions. The deterministic layer '
             'adjudicates file-existence claims and defers everything else to the recorded model '
             'verdict. One recorded case is negated, so this cannot support a general claim.'),
    'recorded_cases': rows,
    'metrics': neg_metrics,
}
(ROOT / 'reports/NEGATION_TEST_RESULTS.json').write_text(json.dumps(neg, indent=2) + '\n')

inj = {
    'schema_version': 1,
    'note': ('Deterministic static screening of synthetic descriptions. Prototype, not a '
             'defence. Labels and rationales were authored before the screen ran; no text was '
             'executed. Ambiguous cases are reported separately and excluded from P/R/F1.'),
    'dataset': 'data/experiments/synthetic_injection_cases.json',
    'confusion': {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
                  'eligible': tp + fp + tn + fn, 'ambiguous_excluded': len(amb)},
    'metrics': {'precision': precision, 'recall': recall, 'f1': f1},
    'by_rule': by_rule,
    'cases': screened,
}
(ROOT / 'reports/INJECTION_DETECTION_RESULTS.json').write_text(json.dumps(inj, indent=2) + '\n')

DATA.mkdir(parents=True, exist_ok=True)
with (DATA / 'fig11_judge_reliability.csv').open('w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['case_id', 'category', 'polarity', 'old_verdict', 'new_verdict', 'source', 'rule'])
    for r in rows:
        w.writerow([r['case_id'], r['category'], r['polarity'], r['old_verdict'],
                    r['new_verdict'], r['source'], r['rule'] or ''])
with (DATA / 'fig12_injection_detection.csv').open('w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['case_id', 'label', 'category', 'flagged', 'rules'])
    for s in screened:
        w.writerow([s['case_id'], s['label'], s['category'], s['flagged'],
                    ';'.join(s['rules_fired'])])

# ---------------------------------------------------------------- figures
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': '#9aa5b1', 'axes.linewidth': 0.8})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={'width_ratios': [1, 1]})
fig.suptitle('Figure 11 — Negation-aware re-judging of recorded claims', fontsize=13,
             fontweight='bold', x=0.012, ha='left', y=0.985)

cats = ['benign', 'false_functionality', 'misleading_side_effect']
labels = ['benign', 'false\nfunctionality', 'misleading\nside effect']
old_ref = [sum(1 for r in rows if r['category'] == c and r['old_verdict'] == 'refuted') for c in cats]
new_ref = [sum(1 for r in rows if r['category'] == c and r['new_verdict'] == 'refuted') for c in cats]
x = range(len(cats))
ax1.bar([i - 0.19 for i in x], old_ref, 0.38, color=GREY, edgecolor=INK, linewidth=0.6,
        label='model judge only')
ax1.bar([i + 0.19 for i in x], new_ref, 0.38, color=GREEN,
        label='with negation-aware layer')
ax1.set_xticks(list(x)); ax1.set_xticklabels(labels)
ax1.set_ylabel('refuted claims (of 3 per category)'); ax1.set_ylim(0, 3.5)
ax1.legend(frameon=False, fontsize=8.5, loc='upper left')
ax1.set_title('(a) Recorded poisoning cases, 9 eligible', fontsize=10.5, loc='left')
ax1.text(0.02, 0.62, 'only S1 changes:\nclaim "No file is created"\n-> refuted (was supported)',
         transform=ax1.transAxes, fontsize=8, color=MUTED)

ax2.axis('off')
ax2.set_title('(b) Deterministic layer on probe claims', fontsize=10.5, loc='left')
tbl = ax2.table(cellText=[[p['probe'], p['polarity'], p['verdict'],
                           'model' if p['defers_to_model'] else 'rule'] for p in probes],
                colLabels=['probe', 'polarity', 'verdict', 'decided by'],
                loc='upper left', cellLoc='left', colWidths=[0.47, 0.19, 0.18, 0.16])
tbl.auto_set_font_size(False); tbl.set_fontsize(7.2); tbl.scale(1, 1.28)
for (r, _c), cell in tbl.get_celld().items():
    cell.set_linewidth(0.4)
    if r == 0:
        cell.set_text_props(fontweight='bold')
ax2.text(0, -0.02, 'ambiguous or double-negated probes return inconclusive, never a guess',
         transform=ax2.transAxes, fontsize=7.5, color=MUTED, va='top')

fig.text(0.012, 0.012, 'source: reports/NEGATION_TEST_RESULTS.json (re-judged recorded evidence; '
         'no new executions)', fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.05, 1, 0.94))
for ext in ('png', 'pdf'):
    fig.savefig(FIG / f'fig11_judge_reliability.{ext}', dpi=300, bbox_inches='tight')
plt.close(fig)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={'width_ratios': [0.85, 1.15]})
fig.suptitle('Figure 12 — Static injection screening of synthetic descriptions', fontsize=13,
             fontweight='bold', x=0.012, ha='left', y=0.985)
grid = [[tn, fp], [fn, tp]]
im = ax1.imshow(grid, cmap='Blues', vmin=0, vmax=max(grid[0][0], grid[1][1]))
ax1.set_xticks([0, 1]); ax1.set_xticklabels(['not flagged', 'flagged'])
ax1.set_yticks([0, 1]); ax1.set_yticklabels(['benign', 'malicious'])
ax1.set_title(f'(a) Confusion, {tp + fp + tn + fn} labelled cases', fontsize=10.5, loc='left')
names = [['TN', 'FP'], ['FN', 'TP']]
for i in range(2):
    for j in range(2):
        ax1.text(j, i, f'{names[i][j]}\n{grid[i][j]}', ha='center', va='center',
                 fontsize=15, fontweight='bold',
                 color='white' if grid[i][j] > max(grid[0][0], grid[1][1]) * 0.6 else INK)
ax1.text(0.5, -0.34, f'precision {precision:.0%}  recall {recall:.0%}  F1 {f1:.2f}\n'
         f'{len(amb)} ambiguous cases excluded', transform=ax1.transAxes, ha='center',
         fontsize=8.5, color=MUTED)

groups = ['benign', 'malicious', 'ambiguous']
counts = [[sum(1 for s in screened if s['label'] == g and not s['flagged']),
           sum(1 for s in screened if s['label'] == g and s['flagged'])] for g in groups]
ax2.bar(range(3), [c[0] for c in counts], 0.55, color=GREY, edgecolor=INK, linewidth=0.6,
        label='not flagged')
ax2.bar(range(3), [c[1] for c in counts], 0.55, bottom=[c[0] for c in counts], color=AMBER,
        label='flagged')
for i, c in enumerate(counts):
    ax2.text(i, c[0] + c[1] + 0.15, str(c[0] + c[1]), ha='center', fontsize=9, color=INK)
ax2.set_xticks(range(3)); ax2.set_xticklabels(['benign\n(n=8)', 'malicious\n(n=12)',
                                               'ambiguous\n(n=3)'])
ax2.set_ylabel('descriptions'); ax2.set_ylim(0, 17.5)
ax2.legend(frameon=False, fontsize=8.5, ncol=2, loc='upper center',
           bbox_to_anchor=(0.5, -0.26))
ax2.set_title('(b) Screening outcome by author label', fontsize=10.5, loc='left')
ax2.text(0.02, 0.93, 'rules fire: ' + ', '.join(f'{k} {v}' for k, v in sorted(by_rule.items())),
         transform=ax2.transAxes, fontsize=7.2, color=MUTED)
ax2.text(0.02, 0.86, 'prototype screen; a miss is not evidence of safety',
         transform=ax2.transAxes, fontsize=7.2, color=MUTED)

fig.text(0.012, 0.012, 'source: reports/INJECTION_DETECTION_RESULTS.json — synthetic text only, '
         'never executed', fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.15, 1, 0.94))
for ext in ('png', 'pdf'):
    fig.savefig(FIG / f'fig12_injection_detection.{ext}', dpi=300, bbox_inches='tight')
plt.close(fig)

print(json.dumps({'judge': neg_metrics['detection_before'], 'judge_after':
                  {k: v for k, v in neg_metrics['detection_after'].items()},
                  'changed': [r['case_id'] for r in changed],
                  'overrides': neg_metrics['deterministic_overrides'],
                  'injection': {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
                                'precision': precision, 'recall': recall, 'f1': f1,
                                'ambiguous': len(amb)}, 'by_rule': by_rule}, indent=1))
