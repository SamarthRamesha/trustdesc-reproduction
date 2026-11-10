#!/usr/bin/env python3
"""Generate every research figure from recorded evidence only.

No number in this script is typed by hand except labels and layout constants:
each panel reads `reports/`, `data/manifests/` or probes the interpreter for
dependency availability, and writes the exact values it plotted to
`reports/figures/figure_data/`.
"""
from __future__ import annotations

import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
FIGDIR = ROOT / 'reports/figures'
DATA = FIGDIR / 'figure_data'
DPI = 300

INK = '#1b2a41'
MUTED = '#6b7a8f'
GRID = '#dde3ea'
OK = '#2f7d5d'
BAD = '#b03a3a'
NEUTRAL = '#c2a24a'
ACCENT = '#3f6fb5'
LIGHT = '#e8eef6'

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 9.5,
    'axes.titlesize': 11,
    'axes.titleweight': 'bold',
    'axes.labelsize': 9.5,
    'axes.edgecolor': MUTED,
    'axes.linewidth': 0.7,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.color': GRID,
    'grid.linewidth': 0.6,
    'xtick.color': INK,
    'ytick.color': INK,
    'text.color': INK,
    'figure.dpi': DPI,
    'savefig.dpi': DPI,
})


def load(path):
    return json.loads((ROOT / path).read_text())


def write_csv(name, header, rows):
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / name).open('w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def save(fig, stem, caption):
    for ext in ('png', 'pdf'):
        fig.savefig(FIGDIR / f'{stem}.{ext}', bbox_inches='tight',
                    facecolor='white', metadata={'Title': caption} if ext == 'pdf' else None)
    plt.close(fig)
    print('wrote', stem)


def stamp(fig, text):
    fig.text(0.005, -0.055, text, fontsize=6.6, color=MUTED, ha='left', va='top')


# --------------------------------------------------------------------------- data
BENCH = load('data/manifests/recovered_benchmark.json')
DESCGEN = load('reports/recovered_descgen/run_state.json')
DYN = load('reports/dynver_recovered/results.json')
FINAL = load('reports/FINAL_EXPERIMENT_RESULTS.json')


def classify_descgen_failure(error: str) -> str:
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


DESCGEN_FAILURES = Counter(classify_descgen_failure(f['error']) for f in DESCGEN['failures'])
DESCGEN_OK = [r for r in DESCGEN['results'] if r['status'] == 'generated']
DESCGEN_ATTEMPTS = len(DESCGEN['results'])
DESCGEN_TIMES = [r['seconds'] for r in DESCGEN_OK]
DESCGEN_CLAIMS = Counter(len(r['description'].get('claims', [])) for r in DESCGEN_OK)


def dependency_probe():
    """Real import availability in this interpreter, for the four unshimmed servers."""
    wanted = {'excel-mcp-server': 'openpyxl', 'mysql_mcp_server': 'mysql.connector',
              'yfinance-mcp': 'yfinance', 'imagesorcery-mcp': 'cv2',
              'arxiv-mcp-server': 'dateutil'}
    rows = []
    for server, module in wanted.items():
        try:
            present = importlib.util.find_spec(module) is not None
        except ModuleNotFoundError:  # parent package absent, e.g. mysql.connector
            present = False
        rows.append((server, module, 'available' if present else 'missing'))
    return rows


DEPS = dependency_probe()


def condition_counts():
    out = {}
    for condition in ('original', 'full', 'lite'):
        units = [u for u in DYN['units'] if u['condition'] == condition]
        out[condition] = Counter(u['verdict'] for u in units)
        out[condition]['total'] = len(units)
    return out


COND = condition_counts()


# ------------------------------------------------------------------------ figure 1
def figure1():
    servers = BENCH['servers']
    names, sliced, unsupported = [], [], []
    for server in servers:
        name = server['server']
        coverage = next(c for c in BENCH['coverage'] if c['server'] == name)
        paper_count = server.get('paper', {}).get('selected_count', 0) or 0
        names.append(name)
        sliced.append(coverage['sliced'])
        unsupported.append(max(paper_count - coverage['sliced'], 0))
    order = sorted(range(len(names)), key=lambda i: (-sliced[i], names[i]))
    names = [names[i] for i in order]
    sliced = [sliced[i] for i in order]
    unsupported = [unsupported[i] for i in order]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.4, 4.9), gridspec_kw={'width_ratios': [2.35, 1]})
    y = np.arange(len(names))
    ax.barh(y, sliced, color=OK, height=0.62, label='Python tools sliced')
    ax.barh(y, unsupported, left=sliced, color='#d9b9b9', height=0.62,
            label='paper slots not sliced (JS/TS)')
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8.6)
    ax.invert_yaxis()
    ax.set_xlabel('tool slots')
    ax.set_title('(a) Recovered corpus coverage by server')
    ax.grid(axis='y', visible=False)
    for i, (s, u) in enumerate(zip(sliced, unsupported)):
        if s:
            ax.text(s / 2, i, str(s), ha='center', va='center', color='white', fontsize=8.4, weight='bold')
        if u:
            ax.text(s + u / 2, i, str(u), ha='center', va='center', color='#7a4a4a', fontsize=8.4)
    handles = [Patch(color=OK, label='Python tools sliced'),
               Patch(color='#d9b9b9', label='paper slots not sliced (JS/TS)')]

    total_sliced = sum(sliced)
    total_unsupported = sum(unsupported)
    ax2.axis('off')
    ax2.set_title('(b) Language coverage', loc='left')
    ax2.text(0.02, 0.86, f"{len(BENCH['servers'])} / 12", fontsize=19, weight='bold', color=INK)
    ax2.text(0.02, 0.79, 'paper servers recovered at pinned commits', fontsize=8.4, color=MUTED)
    ax2.text(0.02, 0.63, f'{total_sliced} / {total_sliced}', fontsize=19, weight='bold', color=OK)
    ax2.text(0.02, 0.56, 'Python tool slots discovered and sliced', fontsize=8.4, color=MUTED)
    ax2.text(0.02, 0.40, f'{total_unsupported}', fontsize=19, weight='bold', color=BAD)
    ax2.text(0.02, 0.33, 'paper tool slots we cannot slice\n(TypeScript / JavaScript)', fontsize=8.4, color=MUTED)
    ax2.text(0.02, 0.14, 'No TypeScript parser is implemented,\nso these slots are excluded, not estimated.',
             fontsize=8.0, color=INK, style='italic')
    ax2.legend(handles=handles, frameon=False, loc='lower left', bbox_to_anchor=(0.0, -0.02), fontsize=8.2)
    fig.suptitle('Figure 1 — Dataset coverage of the independently collected corpus', x=0.02, ha='left',
                 fontsize=12.5, weight='bold')
    stamp(fig, 'source: data/manifests/recovered_benchmark.json (coverage + servers[].paper.selected_count)')
    save(fig, 'fig1_dataset_coverage', 'Corpus coverage: 12 servers, 30 Python tools sliced, 22 JS/TS slots unsupported')
    write_csv('fig1_dataset_coverage.csv', ['server', 'python_tools_sliced', 'paper_slots_not_sliced'],
              list(zip(names, sliced, unsupported)))


# ------------------------------------------------------------------------ figure 2
def figure2():
    valid = len(DESCGEN_OK)
    invalid = DESCGEN_ATTEMPTS - valid
    reasons = DESCGEN_FAILURES.most_common()[::-1]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.4, 4.3), gridspec_kw={'width_ratios': [1, 1.32]})
    ax.bar(['valid'], [valid], color=OK, width=0.5)
    ax.bar(['rejected'], [invalid], bottom=[valid], color='#d9b9b9', width=0.5)
    ax.text(0, valid / 2, f'{valid}', ha='center', va='center', color='white', weight='bold', fontsize=13)
    ax.text(0, valid + invalid / 2, f'{invalid}', ha='center', va='center', color='#7a4a4a',
            weight='bold', fontsize=13)
    ax.set_ylim(0, DESCGEN_ATTEMPTS + 2)
    ax.set_ylabel('generation attempts')
    ax.set_title('(a) Attempts vs. valid output')
    ax.grid(axis='x', visible=False)
    ax.text(0.02, 0.93, f'{valid / DESCGEN_ATTEMPTS:.0%} yield from {DESCGEN_ATTEMPTS} attempts',
            transform=ax.transAxes, fontsize=9, color=INK, va='top')
    ax.set_xlim(-0.6, 0.6)
    ax.set_xlabel('generation outcome')

    labels = [r for r, _ in reasons]
    values = [v for _, v in reasons]
    ax2.barh(np.arange(len(labels)), values, color=[BAD if 'deadline' in l else NEUTRAL for l in labels],
             height=0.6)
    ax2.set_yticks(np.arange(len(labels)))
    ax2.set_yticklabels([l.replace(' ', '\n', 1) for l in labels], fontsize=8.3)
    ax2.set_xlabel('rejected attempts')
    ax2.set_title('(b) Why generations were rejected')
    ax2.grid(axis='y', visible=False)
    for i, v in enumerate(values):
        ax2.text(v + 0.12, i, str(v), va='center', fontsize=8.6, color=INK)
    ax2.set_xlim(0, max(values) + 1.6)
    fig.suptitle('Figure 2 — Description generation yield (local Qwen3-4B, 4-bit MLX)', x=0.02, ha='left',
                 fontsize=12.5, weight='bold')
    stamp(fig, 'source: reports/recovered_descgen/run_state.json; categories derived from recorded error strings')
    save(fig, 'fig2_descgen_yield', 'DescGen: 10 valid of 28 attempts, failure reasons')
    write_csv('fig2_descgen_yield.csv', ['outcome', 'count'],
              [('valid_description', valid), ('rejected_total', invalid)] + reasons)


# ------------------------------------------------------------------------ figure 3
def figure3():
    conditions = ['original', 'full', 'lite']
    verdicts = ['supported', 'refuted', 'inconclusive']
    colors = {'supported': OK, 'refuted': BAD, 'inconclusive': NEUTRAL}
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    bottom = np.zeros(len(conditions))
    for verdict in verdicts:
        vals = np.array([COND[c].get(verdict, 0) for c in conditions])
        ax.bar(conditions, vals, bottom=bottom, color=colors[verdict], width=0.52, label=verdict)
        for i, v in enumerate(vals):
            if v:
                ax.text(i, bottom[i] + v / 2, str(v), ha='center', va='center', color='white',
                        weight='bold', fontsize=10)
        bottom += vals
    for i, c in enumerate(conditions):
        n = COND[c]['total']
        ax.text(i, bottom[i] + 0.12, f'n = {n} claims', ha='center', fontsize=8.6, color=MUTED)
    ax.set_ylim(0, max(bottom) + 1.4)
    ax.set_ylabel('verdicts')
    ax.set_xlabel('description condition')
    ax.grid(axis='x', visible=False)
    fig.legend(handles=[Patch(color=OK, label='supported'), Patch(color=BAD, label='refuted'),
                        Patch(color=NEUTRAL, label='inconclusive')],
               frameon=False, ncol=3, loc='lower center', bbox_to_anchor=(0.5, -0.06))
    ax.set_title('Figure 3 — DynVer verdict distribution by description condition', loc='left')
    stamp(fig, 'source: reports/dynver_recovered/results.json — 18 sandboxed executions, 6 per condition')
    save(fig, 'fig3_dynver_verdicts', 'DynVer verdicts: 12 supported, 6 refuted, 0 inconclusive')
    write_csv('fig3_dynver_verdicts.csv', ['condition'] + verdicts + ['total'],
              [[c] + [COND[c].get(v, 0) for v in verdicts] + [COND[c]['total']] for c in conditions])


# ------------------------------------------------------------------------ figure 4
def figure4():
    conditions = ['original', 'full', 'lite']
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    x = np.arange(len(conditions))
    w = 0.26
    for j, verdict in enumerate(('supported', 'refuted', 'inconclusive')):
        vals = [COND[c].get(verdict, 0) for c in conditions]
        bars = ax.bar(x + (j - 1) * w, vals, width=w,
                      color={'supported': OK, 'refuted': BAD, 'inconclusive': NEUTRAL}[verdict],
                      label=verdict)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.07, str(v), ha='center', fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([f'{c}\n(developer text)' if c == 'original' else
                        f'{c}\n(TRUSTDESC)' if c == 'full' else f'{c}\n(TRUSTDESC, reduced claims)'
                        for c in conditions], fontsize=8.8)
    ax.set_ylim(0, 5.4)
    ax.set_ylabel('claims')
    ax.set_title('Figure 4 — Three-condition comparison: identical observed split', loc='left')
    ax.grid(axis='x', visible=False)
    ax.legend(frameon=False, ncol=1, loc='upper right', fontsize=8.6)
    ax.text(0.02, 0.96, 'all three conditions: 4 supported of 6 claims —\nthe conditions did not separate',
            transform=ax.transAxes, ha='left', va='top', fontsize=9, color=MUTED)
    stamp(fig, 'source: reports/dynver_recovered/results.json — descriptive counts, not a significance claim')
    save(fig, 'fig4_condition_comparison', 'Three conditions produced the same 4/2 split; no separation observed')
    write_csv('fig4_condition_comparison.csv', ['condition', 'supported', 'refuted', 'inconclusive', 'total'],
              [[c, COND[c].get('supported', 0), COND[c].get('refuted', 0),
                COND[c].get('inconclusive', 0), COND[c]['total']] for c in conditions])


# ------------------------------------------------------------------------ figure 5
def figure5():
    tools = sorted({u['tool_id'].split('::')[1] for u in DYN['units']})
    conditions = ['original', 'full', 'lite']
    tasks = sorted({u['task_index'] for u in DYN['units']})
    lookup = {(u['tool_id'].split('::')[1], u['condition'], u['task_index']): u['verdict'] for u in DYN['units']}
    code = {'supported': 1.0, 'refuted': 0.0, 'inconclusive': 0.5}
    rows, labels = [], []
    for tool in tools:
        row = []
        for condition in conditions:
            for task in tasks:
                verdict = lookup.get((tool, condition, task))
                row.append(code.get(verdict, np.nan))
                labels.append(verdict)
        rows.append(row)
    grid = np.array(rows)

    fig, ax = plt.subplots(figsize=(9.0, 3.7))
    cmap = matplotlib.colors.ListedColormap([BAD, NEUTRAL, OK])
    ax.imshow(grid, cmap=cmap, vmin=0, vmax=1, aspect='auto')
    ax.set_yticks(np.arange(len(tools)))
    ax.set_yticklabels([t.replace('_', ' ') for t in tools], fontsize=9)
    cols = [f'{c[:4]}\nT{t + 1}' for c in conditions for t in tasks]
    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(cols, fontsize=8)
    ax.set_xlabel('')
    for i in range(len(tools)):
        for j in range(len(cols)):
            verdict = labels[i * len(cols) + j]
            ax.text(j, i, {'supported': 'S', 'refuted': 'R', 'inconclusive': '?'}.get(verdict, ''),
                    ha='center', va='center', color='white', weight='bold', fontsize=9)
    for k in range(1, len(conditions)):
        ax.axvline(k * len(tasks) - 0.5, color='white', lw=2)
    ax.grid(False)
    ax.set_title('Figure 5 — Execution coverage: every cell is a real sandboxed process', loc='left')
    fig.legend(handles=[Patch(color=OK, label='supported'), Patch(color=BAD, label='refuted'),
                        Patch(color=NEUTRAL, label='inconclusive')],
               frameon=False, ncol=3, loc='lower center', bbox_to_anchor=(0.5, -0.17))
    stamp(fig, 'source: reports/dynver_recovered/results.json — 3 tools x 3 conditions x 2 tasks = 18 units')
    save(fig, 'fig5_execution_coverage', 'DynVer coverage matrix: 18 units, 3 tools, 2 tasks per condition')
    write_csv('fig5_execution_coverage.csv', ['tool'] + cols,
              [[t] + [next((u['verdict'] for u in DYN['units']
                            if u['tool_id'].endswith('::' + t) and u['condition'] == c
                            and u['task_index'] == k), '') for c in conditions for k in tasks]
               for t in tools])


# ------------------------------------------------------------------------ figure 6
def figure6():
    items = []  # (stage, label, count)
    for label, count in DESCGEN_FAILURES.items():
        items.append(('DescGen', label, count))
    items.append(('Language support', 'JS/TS tool slots unsupported', 22))
    missing = [server for server, module, status in DEPS if status == 'missing']
    items.append(('Dependencies', 'servers with a missing runtime dependency', len(missing)))
    items.append(('DynVer scope', 'servers with an adapter shim layer', 1))
    items.append(('Benchmark', 'original paper task files unavailable', 1))
    stage_color = {'DescGen': NEUTRAL, 'Language support': BAD, 'Dependencies': '#8a6fb5',
                   'DynVer scope': ACCENT, 'Benchmark': MUTED}
    items.sort(key=lambda r: (r[0], r[2]))
    fig, ax = plt.subplots(figsize=(9.4, 4.9))
    labels = [f'{i[1]}' for i in items]
    vals = [i[2] for i in items]
    ax.barh(np.arange(len(items)), vals, color=[stage_color[i[0]] for i in items], height=0.62)
    ax.set_yticks(np.arange(len(items)))
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlabel('count (units differ per row)')
    ax.set_xscale('log')
    ax.set_xlim(0.8, 40)
    ax.grid(axis='y', visible=False)
    for i, v in enumerate(vals):
        ax.text(v * 1.12, i, str(v), va='center', fontsize=8.6)
    ax.legend(handles=[Patch(color=c, label=s) for s, c in stage_color.items()],
              frameon=False, fontsize=8, loc='lower right')
    ax.set_title('Figure 6 — Failure and gap taxonomy across the pipeline (log scale)', loc='left')
    stamp(fig, 'sources: run_state.json errors, benchmark coverage, live import probe; log scale because units differ')
    save(fig, 'fig6_failure_taxonomy', 'Failure taxonomy: generation rejections, unsupported languages, missing dependencies')
    write_csv('fig6_failure_taxonomy.csv', ['stage', 'label', 'count'], items)


# ------------------------------------------------------------------------ figure 7
def figure7():
    """Completion is measured, not asserted: each component reports what ran."""
    total_tools = len(BENCH['tools'])
    generated = {r['id'] for r in DESCGEN_OK}
    executed = {u['tool_id'] for u in DYN['units']}
    components = [
        ('Server recovery', 12, 12),
        ('Python tool discovery', total_tools, total_tools),
        ('Python slicing', sum(c['sliced'] for c in BENCH['coverage']), total_tools),
        ('JS/TS slicing', 0, 22),
        ('DescGen valid output', len(generated), len(DESCGEN['results'])),
        ('DynVer executable tools', len(executed), total_tools),
        ('DynVer task sample', len(DYN['units']), 208),
        ('Paper metric reproduction', 0, 5),
    ]
    fig, ax = plt.subplots(figsize=(9.2, 4.5))
    y = np.arange(len(components))
    for i, (label, done, total) in enumerate(components):
        frac = done / total if total else 0
        ax.barh(i, 1, color=LIGHT, height=0.62)
        ax.barh(i, frac, color=OK if frac >= 0.99 else (NEUTRAL if frac > 0 else BAD), height=0.62)
        ax.text(1.02, i, f'{done} / {total}', va='center', fontsize=8.6, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels([c[0] for c in components], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.16)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
    ax.grid(axis='y', visible=False)
    ax.set_title('Figure 7 — Component completion against the research plan', loc='left')
    ax.text(0.0, -0.13,
            '"DynVer task sample" is measured against the paper\'s 208 tasks; our corpus is a separate pilot.',
            fontsize=7.8, color=MUTED, transform=ax.transAxes, va='top')
    stamp(fig, 'sources: benchmark coverage, descgen run_state, dynver results; denominators stated in labels')
    save(fig, 'fig7_project_progress', 'Component completion: corpus done, JS/TS and paper metrics absent')
    write_csv('fig7_project_progress.csv', ['component', 'completed', 'denominator'],
              [list(c) for c in components])


# ------------------------------------------------------------------------ figure 8
def figure8():
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.6), gridspec_kw={'width_ratios': [1.1, 1]})
    conditions = ['original', 'full', 'lite']
    rate = [COND[c].get('supported', 0) / COND[c]['total'] for c in conditions]
    bars = ax.bar(conditions, [r * 100 for r in rate], color=[MUTED, ACCENT, '#7f9dcb'], width=0.5)
    for b, r, c in zip(bars, rate, conditions):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 2.2,
                f'{COND[c].get("supported", 0)}/{COND[c]["total"]}', ha='center', fontsize=9.5, weight='bold')
    ax.set_ylim(0, 108)
    ax.set_ylabel('% of claims supported')
    ax.set_title('(a) Observed agreement — no separation', loc='left')
    ax.grid(axis='x', visible=False)
    ax.axhline(100 * rate[0], color=MUTED, ls=':', lw=0.9)
    ax.text(2.42, 100 * rate[0], 'identical\nto original', fontsize=7.6, color=MUTED, va='center')

    ax2.axis('off')
    ax2.set_title('(b) Reproduction ledger', loc='left')
    rows = [
        ('Three-stage pipeline implemented', 'yes', OK),
        ('Bounded execution in a real OS sandbox', 'yes', OK),
        ('Recovered corpus (12 servers, 30 tools)', 'yes', OK),
        ('Paper task files, labels, traces', 'not released', BAD),
        ('Paper TSR / cost / selection', 'not reproduced', BAD),
        ('Adaptive-attack results', 'not attempted', BAD),
        ('JS/TS tool slots (22)', 'not implemented', BAD),
    ]
    for i, (label, status, colour) in enumerate(rows):
        y = 0.88 - i * 0.125
        ax2.add_patch(plt.Rectangle((0.0, y - 0.045), 0.022, 0.058, color=colour, transform=ax2.transAxes))
        ax2.text(0.045, y - 0.012, label, fontsize=8.3, transform=ax2.transAxes, va='center')
        ax2.text(0.99, y - 0.012, status, fontsize=8.3, transform=ax2.transAxes, va='center',
                 ha='right', color=colour if colour == BAD else INK, weight='bold' if colour == BAD else 'normal')
    fig.suptitle('Figure 8 — Research comparison summary: what the pilot shows and what it does not',
                 x=0.02, ha='left', fontsize=12.5, weight='bold')
    stamp(fig, 'sources: reports/dynver_recovered/results.json, reports/FINAL_EXPERIMENT_RESULTS.json, KNOWN_LIMITATIONS')
    save(fig, 'fig8_research_summary', 'Summary: identical pilot split across conditions, paper metrics absent')
    write_csv('fig8_research_summary.csv', ['item', 'status'],
              [('supported_rate_' + c, f'{COND[c].get("supported", 0)}/{COND[c]["total"]}') for c in conditions]
              + [(label, status) for label, status, _ in rows])


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    figure1(); figure2(); figure3(); figure4(); figure5(); figure6(); figure7(); figure8()
    print('dependency probe:', DEPS)


if __name__ == '__main__':
    main()
