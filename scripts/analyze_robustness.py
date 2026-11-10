#!/usr/bin/env python3
"""Score the challenge (v2) datasets and draw figures 13-15. Recorded data only."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from trustdesc.dynver.negation import adjudicate_claim, combine
from trustdesc.injection_detector import screen

FIG, DATA = ROOT / 'reports/figures', ROOT / 'reports/figure_data'
INK, MUTED, GREEN, RED, AMBER, GREY = '#1f2933', '#6b7280', '#2f7d5f', '#b23a48', '#c08a3e', '#cbd2d9'
FIG.mkdir(parents=True, exist_ok=True); DATA.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- injection v2
ds = json.loads((ROOT / 'data/experiments/injection_robustness_v2.json').read_text())
rows = []
for c in ds['cases']:
    r = screen(c['text'])
    rows.append({**{k: c[k] for k in ('case_id', 'label', 'category', 'text', 'rationale')},
                 'flagged': r['flagged'], 'rules_fired': r['rules_fired'],
                 'findings': r['findings'], 'suppressed': r['suppressed']})

def tally(pred):
    tp = sum(1 for r in rows if r['label'] == 'malicious' and pred(r))
    fn = sum(1 for r in rows if r['label'] == 'malicious' and not pred(r))
    tn = sum(1 for r in rows if r['label'] == 'benign' and not pred(r))
    fp = sum(1 for r in rows if r['label'] == 'benign' and pred(r))
    return tp, fp, tn, fn

tp, fp, tn, fn = tally(lambda r: r['flagged'])
precision = tp / (tp + fp) if tp + fp else None
recall = tp / (tp + fn) if tp + fn else None
f1 = 2 * precision * recall / (precision + recall) if precision and recall else None
fpr = fp / (fp + tn) if fp + tn else None

by_cat = {}
for r in rows:
    if r['label'] != 'malicious':
        continue
    s = by_cat.setdefault(r['category'], {'cases': 0, 'flagged': 0})
    s['cases'] += 1; s['flagged'] += int(r['flagged'])
for s in by_cat.values():
    s['recall'] = s['flagged'] / s['cases']

misses = [r['case_id'] for r in rows if r['label'] == 'malicious' and not r['flagged']]
fps = [{'case_id': r['case_id'], 'rules': r['rules_fired'], 'text': r['text']}
       for r in rows if r['label'] == 'benign' and r['flagged']]
amb = [{'case_id': r['case_id'], 'flagged': r['flagged'], 'rules': r['rules_fired']}
       for r in rows if r['label'] == 'ambiguous']

dev = json.loads((ROOT / 'reports/INJECTION_DETECTION_RESULTS.json').read_text())
inj = {
    'schema_version': 2,
    'note': ('Independent challenge set written after the five rules were frozen and not reused '
             'from the development set. Text is inert. Perfect development scores are not '
             'comparable to these numbers; both are reported separately, never pooled.'),
    'dataset': 'data/experiments/injection_robustness_v2.json',
    'confusion': {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
                  'eligible': tp + fp + tn + fn, 'ambiguous_excluded': len(amb)},
    'metrics': {'precision': precision, 'recall': recall, 'f1': f1, 'false_positive_rate': fpr},
    'by_attack_category': by_cat,
    'missed_attacks': misses,
    'false_positives': fps,
    'ambiguous': amb,
    'development_set_metrics': dev['metrics'],
    'development_confusion': dev['confusion'],
    'cases': rows,
}
(ROOT / 'reports/INJECTION_ROBUSTNESS_V2.json').write_text(json.dumps(inj, indent=2) + '\n')

# ---------------------------------------------------------------- negation v2
nds = json.loads((ROOT / 'data/experiments/negation_robustness_v2.json').read_text())
nrows = []
for c in nds['cases']:
    d = adjudicate_claim(c['claim'], c['observation'])
    actual = 'defer' if d is None else d['verdict']
    nrows.append({'case_id': c['case_id'], 'claim': c['claim'], 'expected': c['expected'],
                  'actual': actual, 'handled': d is not None,
                  'deferred': d is None, 'rule': (d or {}).get('rule'),
                  'polarity': (d or {}).get('polarity'),
                  'matches_expectation': actual == c['expected'],
                  'rationale': c['rationale']})
false_supported = [r['case_id'] for r in nrows
                   if r['expected'] in {'refuted', 'inconclusive', 'defer'} and r['actual'] == 'supported']
false_refuted = [r['case_id'] for r in nrows
                 if r['expected'] in {'supported', 'inconclusive', 'defer'} and r['actual'] == 'refuted']
neg = {
    'schema_version': 2,
    'note': ('Controlled probes with expected verdicts fixed before running the layer. No model '
             'judge was called: "defer" records that the layer returns None, so a model verdict '
             'would have been used.'),
    'cases_total': len(nrows),
    'matches': sum(1 for r in nrows if r['matches_expectation']),
    'mismatches': [r for r in nrows if not r['matches_expectation']],
    'handled_by_rule': sum(1 for r in nrows if r['handled']),
    'deferred_to_model': sum(1 for r in nrows if r['deferred']),
    'false_supported': false_supported,
    'false_refuted': false_refuted,
    'cases': nrows,
}
(ROOT / 'reports/NEGATION_ROBUSTNESS_V2.json').write_text(json.dumps(neg, indent=2) + '\n')

for name, header, body in (
    ('fig13_injection_robustness', ['case_id', 'label', 'category', 'flagged', 'rules'],
     [[r['case_id'], r['label'], r['category'], r['flagged'], ';'.join(r['rules_fired'])] for r in rows]),
    ('fig14_negation_robustness', ['case_id', 'expected', 'actual', 'handled', 'rule'],
     [[r['case_id'], r['expected'], r['actual'], r['handled'], r['rule'] or ''] for r in nrows]),
    ('fig15_detector_error_analysis', ['case_id', 'label', 'category', 'flagged', 'rules'],
     [[r['case_id'], r['label'], r['category'], r['flagged'], ';'.join(r['rules_fired'])]
      for r in rows if (r['label'] == 'malicious' and not r['flagged'])
      or (r['label'] == 'benign' and r['flagged'])]),
):
    with (DATA / f'{name}.csv').open('w', newline='') as fh:
        w = csv.writer(fh); w.writerow(header); w.writerows(body)

plt.rcParams.update({'font.size': 10, 'axes.edgecolor': '#9aa5b1', 'axes.linewidth': 0.8})

# fig 13: confusion + recall by category
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={'width_ratios': [0.8, 1.3]})
fig.suptitle('Figure 13 — Injection screen on an independent challenge set', fontsize=13,
             fontweight='bold', x=0.012, ha='left', y=0.985)
grid = [[tn, fp], [fn, tp]]
ax1.imshow(grid, cmap='Blues', vmin=0, vmax=max(tp, tn))
ax1.set_xticks([0, 1]); ax1.set_xticklabels(['not flagged', 'flagged'])
ax1.set_yticks([0, 1]); ax1.set_yticklabels(['benign', 'malicious'])
ax1.set_title(f'(a) Confusion, {tp + fp + tn + fn} labelled cases', fontsize=10.5, loc='left')
for i in range(2):
    for j in range(2):
        ax1.text(j, i, f'{["TN","FP"][0] if (i,j)==(0,0) else ["FP","TP"][0] if (i,j)==(0,1) else "FN" if (i,j)==(1,0) else "TP"}\n{grid[i][j]}',
                 ha='center', va='center', fontsize=15, fontweight='bold',
                 color='white' if grid[i][j] > max(tp, tn) * 0.6 else INK)
def pct(v):
    return 'undefined' if v is None else f'{v:.0%}'
ax1.text(0.5, -0.30, f'precision {pct(precision)}  recall {pct(recall)}  F1 '
         f'{"undefined" if f1 is None else f"{f1:.2f}"}\n'
         f'FPR {pct(fpr)}   ({sum(1 for r in rows if r["label"]=="ambiguous")} ambiguous excluded)',
         transform=ax1.transAxes, ha='center', fontsize=8.5, color=MUTED)

cats = sorted(by_cat)
ax2.barh(range(len(cats)), [by_cat[c]['recall'] for c in cats], 0.55, color=AMBER)
for i, c in enumerate(cats):
    ax2.text(1.02, i, f"{by_cat[c]['flagged']}/{by_cat[c]['cases']}", va='center', fontsize=8.5, color=INK)
ax2.set_yticks(range(len(cats))); ax2.set_yticklabels(cats, fontsize=8.5)
ax2.set_xlim(0, 1.18); ax2.set_xlabel('recall within category')
ax2.set_title('(b) Detection by attack family (author labels)', fontsize=10.5, loc='left')
ax2.axvline(0, color=INK, lw=0.8)
fig.text(0.012, 0.012, 'source: reports/INJECTION_ROBUSTNESS_V2.json — synthetic inert text, '
         'labels fixed before the screen ran', fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.07, 1, 0.94))
for ext in ('png', 'pdf'):
    fig.savefig(FIG / f'fig13_injection_robustness.{ext}', dpi=300, bbox_inches='tight')
plt.close(fig)

# fig 14: expected vs actual matrix
fig, ax = plt.subplots(figsize=(9.2, 5.6))
order = {'supported': 0, 'refuted': 1, 'inconclusive': 2, 'defer': 3}
actual_order = {'supported': 0, 'refuted': 1, 'inconclusive': 2, 'defer': 3}
mat = [[0] * 4 for _ in range(4)]
for r in nrows:
    mat[order[r['expected']]][actual_order[r['actual']]] += 1
ax.imshow(mat, cmap='Greens', vmin=0, vmax=max(1, max(max(x) for x in mat)))
for i in range(4):
    for j in range(4):
        if mat[i][j]:
            ax.text(j, i, str(mat[i][j]), ha='center', va='center', fontsize=15,
                    fontweight='bold', color='white' if mat[i][j] >= 3 else INK)
ax.set_xticks(range(4)); ax.set_xticklabels(['supported', 'refuted', 'inconclusive', 'defer'])
ax.set_yticks(range(4)); ax.set_yticklabels(['supported', 'refuted', 'inconclusive', 'defer'])
ax.set_xlabel('actual'); ax.set_ylabel('expected (fixed before running)')
ax.set_title(f'Figure 14 — Negation layer on {len(nrows)} controlled probes '
             f'({neg["matches"]}/{len(nrows)} match expectation)', fontsize=11, loc='left')
ax.text(0.0, -0.22, 'mismatches: ' + ', '.join(m['case_id'] for m in neg['mismatches']) if neg['mismatches']
        else 'no mismatches', transform=ax.transAxes, fontsize=8.5, color=MUTED)
fig.text(0.012, 0.012, 'source: reports/NEGATION_ROBUSTNESS_V2.json', fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.06, 1, 1))
for ext in ('png', 'pdf'):
    fig.savefig(FIG / f'fig14_negation_robustness.{ext}', dpi=300, bbox_inches='tight')
plt.close(fig)

# fig 15: development vs challenge recall, and error inventory
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.9), gridspec_kw={'width_ratios': [1, 1.1]})
fig.suptitle('Figure 15 — Error analysis: development set vs independent challenge set', fontsize=13,
             fontweight='bold', x=0.012, ha='left', y=0.985)
dev_rec = dev['metrics']['recall'] or 0
ax1.bar([0, 1], [dev_rec, recall], 0.5, color=[GREY, AMBER], edgecolor=INK, linewidth=0.6)
for i, (v, n) in enumerate(((dev_rec, dev['confusion']['tp'] + dev['confusion']['fn']),
                            (recall, tp + fn))):
    ax1.text(i, v + 0.03, f'{pct(v)}  ({n} attacks)', ha='center', fontsize=9, color=INK)
ax1.set_xticks([0, 1]); ax1.set_xticklabels(['development set\n(used to write rules)',
                                             'challenge set v2\n(unseen wording)'])
ax1.set_ylim(0, 1.15); ax1.set_ylabel('recall')
ax1.set_title('(a) Same rules, unseen attacks', fontsize=10.5, loc='left')
ax1.text(0.03, 0.35, 'gap = generalisation cost', transform=ax1.transAxes,
         fontsize=8, color=MUTED)

labels = ['missed\nattacks', 'false\npositives', 'caught\nattacks', 'true\nnegatives']
vals = [fn, fp, tp, tn]
ax2.bar(range(4), vals, 0.55, color=[RED, RED, GREEN, GREY])
for i, v in enumerate(vals):
    ax2.text(i, v + 0.2, str(v), ha='center', fontsize=10, color=INK)
ax2.set_xticks(range(4)); ax2.set_xticklabels(labels)
ax2.set_ylabel('cases'); ax2.set_ylim(0, max(vals) + 3)
ax2.set_title(f'(b) Challenge-set errors (n = {tp + fp + tn + fn} eligible)', fontsize=10.5, loc='left')
ex = fps[0]['case_id'] if fps else 'none'
ax2.text(0.03, 0.80, f'FP: {", ".join(f["case_id"] for f in fps) or "none"}',
         transform=ax2.transAxes, fontsize=8, color=MUTED)
ax2.text(0.03, 0.72, f'FN: all {len({r["category"] for r in rows if r["case_id"] in misses})} attack families',
         transform=ax2.transAxes, fontsize=8, color=MUTED)
fig.text(0.012, 0.012, 'source: reports/INJECTION_ROBUSTNESS_V2.json and '
         'reports/INJECTION_DETECTION_RESULTS.json (kept separate, never pooled)', fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.06, 1, 0.94))
for ext in ('png', 'pdf'):
    fig.savefig(FIG / f'fig15_detector_error_analysis.{ext}', dpi=300, bbox_inches='tight')
plt.close(fig)

print(json.dumps({'injection': {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
                                'precision': precision, 'recall': recall, 'f1': f1, 'fpr': fpr},
                  'by_category': by_cat, 'misses': misses,
                  'fps': [f['case_id'] for f in fps],
                  'negation': {'matches': neg['matches'], 'total': neg['cases_total'],
                               'mismatches': [m['case_id'] for m in neg['mismatches']],
                               'false_supported': false_supported,
                               'false_refuted': false_refuted}}, indent=1))
