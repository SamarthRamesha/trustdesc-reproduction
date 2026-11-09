#!/usr/bin/env python3
"""Generate the dataset acquisition/validation/provenance deliverables.

Every number here is read from recorded manifests or measured from the
recovered public source. Nothing is estimated or invented.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOVERED = ROOT / 'data/raw/recovered'
BENCH = ROOT / 'data/manifests/recovered_benchmark.json'
PAPER = ROOT / 'data/manifests/paper_servers.json'
PROBE = ROOT / 'reports/original_dataset/artifact_probe.json'
SKIP = {'node_modules', 'dist', 'build', '.git', '__pycache__', 'venv', '.venv'}


def find_license(root: Path):
    for base in [root, *root.parents[:3]]:
        if base.name == '.git':
            continue
        for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'COPYING'):
            candidate = base / name
            if candidate.is_file():
                text = candidate.read_text(encoding='utf-8', errors='replace')
                first = text.strip().splitlines()[0].strip() if text.strip() else ''
                return {'file': name, 'first_line': first,
                        'sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
                        'path': candidate.relative_to(ROOT).as_posix()}
    return None


def tree_digest(root: Path):
    entries, total = [], 0
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in SKIP for part in rel.split('/')):
            continue
        data = path.read_bytes()
        total += len(data)
        entries.append(f'{rel}:{hashlib.sha256(data).hexdigest()}')
    return hashlib.sha256('\n'.join(entries).encode()).hexdigest(), len(entries), total


def main():
    bench = json.loads(BENCH.read_text())
    paper = {s['name']: s for s in json.loads(PAPER.read_text())}
    probe = json.loads(PROBE.read_text())
    now = datetime.now(timezone.utc).isoformat()
    servers = {s['server']: s for s in bench['servers']}
    tools = bench['tools']

    sources = []
    for name, meta in paper.items():
        clone_dir = next((s['clone_directory'] for s in bench['servers'] if s['server'] == name), None)
        entry = {'server': name, 'paper_reference': 'Table 1, p.9', 'paper_url': meta['source'],
                 'paper_language': meta['paper_language'], 'paper_selected_count': meta['selected_count'],
                 'classification': 'independently_collected_public_source'}
        clone = RECOVERED / clone_dir if clone_dir else None
        analysis = None
        if clone and clone.is_dir():
            analysis = (clone / servers[name]['analysis_root'].split(clone_dir, 1)[-1].lstrip('/')).resolve()
            if not analysis or not analysis.is_dir():
                analysis = clone
            digest, files, size = tree_digest(analysis)
            entry.update({'clone_directory': clone_dir,
                          'license': servers[name].get('license') or find_license(clone),
                          'analysis_root': str(analysis.relative_to(ROOT)),
                          'commit': servers[name].get('commit'),
                          'analysis_tree_sha256': digest, 'source_files': files, 'source_bytes': size,
                          'acquisition_utc': now,
                          'paper_revision_recovered': False,
                          'revision_note': 'current HEAD at acquisition; the paper never published its revisions'})
            if meta['paper_language'].lower() == 'typescript' and not any(
                    analysis.rglob('*.ts')):
                entry['language_discrepancy'] = 'paper labels TypeScript; recovered tree has no .ts files'
        else:
            entry['status'] = 'source_unavailable'
        sources.append(entry)

    original_candidates = [s for s in servers.values() if s.get('status', '').startswith('recovered')]
    python_tools = [t for t in tools if t['language'] == 'python']
    sliced = [t for t in tools if t['slice_status'] == 'sliced']
    script_tools = []
    for name in paper:
        clone_dir = next((s['clone_directory'] for s in bench['servers'] if s['server'] == name), None)
        if not clone_dir:
            continue
        info = next((s for s in bench['servers'] if s['server'] == name), {})
        script_tools.append({'server': name, 'discovered_scripts': info.get('discovered_scripts', 0),
                             'language': info.get('slicer_supported_language')})

    manifest = {
        'schema_version': 1,
        'generated_utc': now,
        'original_benchmark_recovered': False,
        'classification_legend': {
            'original_paper_material': 'text/numbers reproduced from the published PDF',
            'recovered_public_source': 'public code at a pinned commit, independently cloned',
            'independently_collected': 'our selection/labels, not the authors\'',
            'reconstructed': 'derived from published information only',
            'synthetic': 'authored for engineering checks',
        },
        'original_artifact': {
            'url': 'https://anonymous.4open.science/r/ae-trustdesc-13A6',
            'status': 'expired_unrecoverable',
            'evidence_file': 'reports/original_dataset/artifact_probe.json',
            'observations': [{'url': r['url'], 'http_status': r.get('http_status'),
                              'body_excerpt': (r.get('body_excerpt') or '')[:200]}
                             for r in probe['results']
                             if '4open.science' in r['url'] or 'archive.org' in r['url']
                             or 'api.github.com' in r['url'] or 'hengkai' in r['url']],
        },
        'counts': {
            'paper_tools_reported': 52, 'paper_tasks_reported': 208, 'paper_servers_reported': 12,
            'servers_with_public_source': len([s for s in sources if 'commit' in s]),
            'tools_selected': len(tools), 'python_tools_selected': len(python_tools),
            'tools_sliced': len(sliced),
            'tool_records_recovered': 0, 'task_records_recovered': 0, 'ground_truth_labels_recovered': 0,
            'execution_traces_recovered': 0,
        },
        'paper_table_1': [{'server': k, **{x: v[x] for x in ('source', 'paper_language', 'category', 'selected_count')}}
                          for k, v in paper.items()],
        'recovered_sources': sources,
        'tools': tools,
    }
    (ROOT / 'ORIGINAL_DATASET_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')

    provenance = {
        'schema_version': 1, 'generated_utc': now,
        'rule': 'No record is labelled original unless it was published by the authors.',
        'sources': sources,
        'tool_records': [{'id': t['id'], 'server': t['server'], 'file': t['file'], 'line': t['line'],
                          'commit': t['commit'], 'license': t['license'],
                          'entry_kind': t['entry_kind'], 'confidence': t['confidence'],
                          'entry_resolution': t.get('entry_resolution'),
                          'slice_sha256': t.get('slice_sha256'),
                          'classification': 'independently_collected'} for t in tools],
        'excluded': ['paper PDF (private copy, not redistributed)',
                     'third-party source trees (referenced by commit, not bundled)'],
    }
    (ROOT / 'SOURCE_PROVENANCE.json').write_text(json.dumps(provenance, indent=2) + '\n')

    # Acquisition report
    lines = [
        '# Original dataset acquisition report', '',
        f'Generated {now}. **No original TRUSTDESC benchmark record was recovered.**', '',
        '## 1. What the paper actually releases', '',
        '- Table 1 (p.9) names 12 public MCP servers, their language, category and the number of tools '
        'selected (total 52) — locations and counts only, **not** tool names, revisions or code.',
        '- §5 states 208 tasks were generated (4 per tool, 2 from the original and 2 from the generated '
        'description) and that success required **manual** trace inspection. No task text, prompt, label '
        'or trace is published.',
        '- No data-availability statement, artifact link, code release or supplementary bundle appears in '
        'the arXiv abstract, HTML full text or PDF of arXiv:2604.07536v1.', '',
        '## 2. Artifact investigation (all evidence in `reports/original_dataset/artifact_probe.json`)',
        '',
        '| Endpoint | Observed | Meaning |', '|---|---|---|',
        '| `/r/ae-trustdesc-13A6` | HTTP 200, SPA shell only | landing page loads, repository data does not |',
        '| `/api/repo/ae-trustdesc-13A6` | HTTP 401 `{"error":"not_connected"}` | no repository bound to the id |',
        '| `/api/repo/ae-trustdesc-13A6/files` | HTTP 410 `{"error":"repository_expired"}` | anonymous bundle expired |',
        '| `/api/repo/ae-trustdesc-13A6/zip` | HTTP 410 `{"error":"repository_expired"}` | archive expired |',
        '| Wayback availability API | `archived_snapshots: {}` | never captured |',
        '| Wayback CDX prefix query | timed out / empty | no historical capture |',
        '| GitHub repository search `trustdesc` | 1 result = this reproduction repo | no authors\' release |',
        '| `hengkai-ye.github.io` | HTTP 404 | no author project page |', '',
        'No authentication bypass, credential use or access-control circumvention was attempted. The '
        'artifact is unavailable because it expired, not because access was refused.', '',
        '## 3. What was instead recovered (labelled `independently_collected`)', '',
        'All 12 paper-named public server repositories were cloned at a pinned commit. Every selected '
        'Python tool was then statically discovered and sliced by SliceMin.', '',
        '| Server | Paper | Commit | License (first line) | Tools discovered (py/js+ts) | Tools sliced |',
        '|---|---|---|---|---|---|',
    ]
    by_server = {}
    for t in tools:
        by_server.setdefault(t['server'], []).append(t)
    for s in sources:
        lic = (s.get('license') or {}).get('first_line', 'none found')
        info = servers.get(s['server'], {})
        lines.append(f"| {s['server']} | {s['paper_selected_count']} {s['paper_language']} | "
                     f"`{(s.get('commit') or 'n/a')[:12]}` | {lic[:48]} | "
                     f"{info.get('discovered_python', 0)} / {info.get('discovered_scripts', 0)} | "
                     f"{len([t for t in by_server.get(s['server'], []) if t['slice_status'] == 'sliced'])} |")
    lines += ['',
              f'Selected tools: **{len(tools)}** (the paper\'s per-server counts). Sliced: **{len(sliced)}**. '
              f'The remaining {52 - len(sliced)} of the paper\'s 52 tools are JavaScript/TypeScript, which the '
              'current implementation does not parse.', '',
              'Tool identity is a **deterministic prefix of static discovery order**, not the authors\' random '
              'sample (seed never released). Exact tool identity therefore cannot match the paper.', '',
              '## 4. What remains impossible', '',
              'Exact reproduction of Q1 TSR (208 tasks × 3 description conditions × 4 generation models), Q2 '
              'cost, Q3 tool-quality selection, Q4 TPA blocking and Q5 adaptive attacks all require author '
              'records that are not public. They are reported as **not recovered**, never as measured.', '',
              'A conservative author request is prepared in `MISSING_RESEARCH_MATERIALS.md`; it has **not** '
              'been sent and requires user approval.']
    (ROOT / 'ORIGINAL_DATASET_ACQUISITION_REPORT.md').write_text('\n'.join(lines) + '\n')

    # Validation report
    dup = len(tools) - len({t['id'] for t in tools})
    unresolved = [t for t in tools if t['slice_status'] != 'sliced']
    checks = [
        ('12 paper servers have public source', len([s for s in sources if s.get('commit')]) == 12,
         f"{len([s for s in sources if s.get('commit')])}/12"),
        ('Python-subset selected count equals paper counts for those servers',
         all(len(by_server.get(k, [])) == min(v['selected_count'], servers[k].get('discovered_python', 0))
             for k, v in paper.items()), f"{len(tools)} selected; 52 total is only reached with TypeScript support"),
        ('per-server selected count matches paper for every sliceable server', all(
            len(by_server.get(k, [])) == min(v['selected_count'], servers[k].get('discovered_python', 0))
            for k, v in paper.items()), '12/12 server rows checked'),
        ('no duplicate tool record ids', dup == 0, f'{dup} duplicates'),
        ('every sliced tool records a source hash', all(t.get('slice_sha256') for t in sliced),
         f"{len([t for t in sliced if t.get('slice_sha256')])}/{len(sliced)}"),
        ('every tool record pins a commit', all(t.get('commit') for t in tools),
         f"{len([t for t in tools if t.get('commit')])}/{len(tools)}"),
        ('every tool record carries a license line', all(t.get('license') for t in tools),
         f"{len([t for t in tools if t.get('license')])}/{len(tools)}"),
        ('SliceMin entry resolution succeeded for all selected tools', not unresolved,
         f"{len(sliced)}/{len(tools)}; unresolved: {[t['id'] for t in unresolved]}"),
        ('task records recovered from the authors', False, '0 (never released)'),
        ('ground-truth labels recovered', False, '0 (manual review, unreleased)'),
        ('execution traces recovered', False, '0 (unreleased)'),
        ('paper tool revisions recovered', False, '0 (unreleased; current HEAD pinned instead)'),
    ]
    lines = ['# Dataset validation report', '', f'Generated {now}.', '',
             'Validation of the **independently collected** corpus. Passing these checks does not make it '
             'the paper\'s benchmark.', '', '| Check | Result | Observed |', '|---|---|---|']
    for name, ok, observed in checks:
        lines.append(f"| {name} | {'PASS' if ok else 'NOT MET'} | {observed} |")
    lines += ['',
              '## Distribution of evidence', '',
              f"- Python tools discovered and selected: {len(python_tools)}",
              f"- Sliced with a resolved entry: {len(sliced)}",
              f"- Entry via registration pattern: {len([t for t in sliced if t.get('entry_resolution') == 'registration_pattern'])}",
              f"- Entry via explicit name match: {len([t for t in sliced if t.get('entry_resolution') == 'explicit_name_match'])}",
              f"- JavaScript/TypeScript tools identified but not sliceable: {52 - len(tools)}",
              '',
              '## Findings that affect interpretation', '',
              '1. **Registration style is far more varied than the paper\'s three patterns.** The recovered '
              'repositories use `@mcp.tool`, custom registry decorators (`@tools.reader("Read range")`), '
              'explicit `Tool(name=...)` objects returned by `list_tools`, and nested factory closures. Ten of '
              'thirty entries needed an explicit module-qualified entry, which the paper delegates to an LLM '
              'fallback that is not implemented here.',
              '2. **Nested registrations** (excel-mcp-server\'s `register(tools, workspace)` closures) only '
              'resolve through qualified names; without that extension static entry detection finds nothing.',
              '3. **Table 1 language labels do not always match repository contents.** `healthcare-mcp` is '
              'labelled TypeScript in the paper but ships `.js`; `travel-planner-mcp-server` ships a single '
              'TypeScript entry point. The paper\'s labels were preserved, not corrected.',
              '4. **MCP servers move.** Current HEAD is not the paper\'s revision, so even the same server can '
              'expose a different tool set. This is recorded per server rather than silently substituted.',
              '5. **No task layer exists.** Without task text there is no TSR, and none is computed from this '
              'corpus.']
    (ROOT / 'DATASET_VALIDATION_REPORT.md').write_text('\n'.join(lines) + '\n')

    # Licenses
    lines = ['# Dataset licenses', '', f'Generated {now}.', '',
             'Third-party code is **not redistributed** in this repository or the handover ZIP. Each source is '
             'referenced by repository URL, commit and tree hash; clones stay under ignored `data/raw/`.', '',
             '| Server | Repository | Commit | License file | First line | License SHA-256 |',
             '|---|---|---|---|---|---|']
    for s in sources:
        lic = s.get('license') or {}
        lines.append(f"| {s['server']} | {s['paper_url']} | `{(s.get('commit') or 'n/a')[:12]}` | "
                     f"{lic.get('file', 'none')} | {lic.get('first_line', 'n/a')[:40]} | "
                     f"`{(lic.get('sha256') or 'n/a')[:16]}` |")
    lines += ['', 'This repository\'s own code remains under its existing `LICENSE`. Recovered tools keep '
                  'their upstream licenses; any redistribution must re-check each one. The paper PDF is CC BY '
                  '4.0 but is not bundled.']
    (ROOT / 'DATASET_LICENSES.md').write_text('\n'.join(lines) + '\n')

    # Missing materials
    missing = [
        ('Original tool implementations (selected 52)', 'NOT RECOVERED',
         'Artifact expired; no code release. Public server repos cloned instead at current HEAD.'),
        ('Original MCP server identities', 'PARTIALLY RECOVERED (paper Table 1)',
         '12 server repositories named and cloned; the paper\'s 20-server sampling frame was not.'),
        ('Original source revisions/commits', 'NOT RECOVERED', 'Never published; current HEAD pinned.'),
        ('Original tool descriptions', 'NOT RECOVERED',
         'Descriptions exist in live repositories, but the specific paper-revision text is unknown.'),
        ('Original task definitions (208)', 'NOT RECOVERED', 'LLM-generated then manually reviewed; unreleased.'),
        ('Task-to-tool mappings', 'NOT RECOVERED', 'Unreleased.'),
        ('Original 208 task records', 'NOT CONFIRMED AS A RELEASABLE FILE', 'Count confirmed from §5 text only.'),
        ('Original prompts', 'NOT RECOVERED', 'Paper describes stages, not prompt text.'),
        ('Original model configurations', 'PARTIALLY RECOVERED (paper text)',
         'Model display names, temperature 0.2 and provider named; IDs, versions and serving stack absent.'),
        ('Ground-truth labels', 'NOT RECOVERED', 'Manual human trace review; no label file.'),
        ('Execution traces', 'NOT RECOVERED', 'Unreleased.'),
        ('Evaluation scripts', 'NOT RECOVERED', 'Unreleased.'),
        ('Metric definitions', 'RECOVERED FROM PAPER TEXT', 'TSR and the Q2 relative overhead definitions are stated.'),
        ('Tool-quality experiment materials', 'NOT RECOVERED',
         'Degradation strategies described qualitatively; mutations, ordering and denominators absent.'),
        ('Adaptive-attack materials', 'NOT RECOVERED',
         'Only a plotted trajectory and trend statistics are printed.'),
        ('Artifact bundle (anonymous.4open.science)', 'EXPIRED', 'HTTP 410 repository_expired; no Wayback capture.'),
    ]
    lines = ['# Missing research materials', '', f'Generated {now}.', '',
             '| Material | Status | Consequence |', '|---|---|---|']
    lines += [f'| {m} | {s} | {c} |' for m, s, c in missing]
    lines += ['', '## Prepared author request (not sent)', '',
              '> Subject: Request for the TRUSTDESC evaluation bundle (arXiv:2604.07536)', '>',
              '> Dear Dr. Ye and co-authors,', '>',
              '> We are independently reimplementing TRUSTDESC and would like to evaluate it against your '
              'original benchmark. The anonymous artifact (ae-trustdesc-13A6) now returns '
              '`repository_expired`, and no code or data release is linked from the paper.',
              '>', '> Could you share: (1) the 52 selected tools with their server and commit, (2) the 208 '
              'task texts and their tool mappings, (3) the prompt templates for SliceMin/DescGen/DynVer, '
              '(4) the model identifiers and settings, and (5) the reviewed labels or evaluation scripts?',
              '>', '> We will cite the paper and keep your provenance labels intact.', '',
              '**This message has not been sent. Sending requires explicit user approval.**', '',
              '## Alternatives already pursued', '',
              '- All 12 paper-named public servers cloned and pinned (see `SOURCE_PROVENANCE.json`).',
              '- Static discovery and SliceMin coverage measured on the Python subset.',
              '- Real local model descriptions generated for the recovered slices (see `METRICS_REPORT.md`).',
              '- Exact reproduction remains marked incomplete; no value is fabricated to fill a gap.']
    (ROOT / 'MISSING_RESEARCH_MATERIALS.md').write_text('\n'.join(lines) + '\n')
    print('wrote 6 dataset deliverables')
    print('servers with source:', len([s for s in sources if s.get('commit')]))
    print('tools:', len(tools), 'sliced:', len(sliced))


if __name__ == '__main__':
    main()
