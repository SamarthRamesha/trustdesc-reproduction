# DynVer: sandboxed execution on real recovered tools

Backend: **macOS Seatbelt** (`sandbox-exec`), deny-by-default policy, writes only to a per-run scratch directory, network denied, CPU/file-size/process limits, RSS supervision. Isolation canary probes passed on this machine before any source ran: `True`.

## Conditions and verdicts

| Condition | Supported | Refuted | Inconclusive | Total |
|---|---|---|---|---|
| original | 4 | 2 | 0 | 6 |
| full | 4 | 2 | 0 | 6 |
| lite | 4 | 2 | 0 | 6 |

## Measured outcome

Each of the three conditions produced the same split: 4/6 supported tasks. The descriptions differ, but on this three-tool slice the sandboxed tasks did not separate them. That is a null result, not a failing pipeline: it is the honest outcome of a small task set with a 4B task generator.

## How execution works

Recovered tool bodies are adapters over external SDKs, so the harness strips module-level imports and supplies explicit, recorded shims for the transport only (for `arxiv-mcp-server`, `mcp.types.TextContent`, `Settings` and the two network helpers that raise). Real `python-dateutil` code runs, the real body runs unmodified, and every observation is a real process result with captured stdout, stderr, exit status, peak RSS and a policy hash.

Claims that depend on a shimmed adapter are classified `inconclusive` by rule and never `supported`.

## Reproduce

```sh
.venv/bin/python scripts/run_dynver_recovered.py
.venv/bin/python scripts/report_dynver.py
```

State is appended after every unit, so an interrupted run resumes where it stopped.

## Limits

- Three tools, one server, 18 tasks total: `arxiv-mcp-server` subscription bookkeeping.
- Other servers need their own shim layer before they can run.
- This is not the paper’s 208-task benchmark and its TSR is not reproduced.

## Checkpoint 2026-11-10 — canonical numbers

Use these figures everywhere; they are generated from recorded evidence by
`scripts/analyze_statistics.py` and `scripts/generate_figures.py`.

| Measurement | Value |
|---|---|
| Paper servers recovered | 12 / 12 at pinned commits |
| Python tool slots sliced | 30 / 30 |
| TypeScript/JavaScript slots unsupported | 22 |
| Valid descriptions | 10 / 28 = 35.7% (Wilson 95% 20.7–54.2%) |
| Rejections | 8 generation deadline, 7 identifier normalisation, 2 token cap, 1 schema |
| Claims generated | 88 (6–11 per description) |
| Sandboxed executions | 18 (3 tools x 3 conditions x 2 tasks) |
| Verdicts | 12 supported, 6 refuted, 0 inconclusive |
| Per condition | 4 supported of 6 in each; no separation observed |
| Task success rate | not computed — the paper benchmark was never released |
| Automated tests | 165 passing |

Artefacts: `reports/figures/FIGURE_INDEX.md` (8 figures),
`reports/STATISTICAL_ANALYSIS.md`, `reports/STATISTICAL_RESULTS.json`,
`reports/EXPERIMENTAL_FINDINGS.md`, `reports/PROJECT_SUMMARY.md`, `TEAM_HANDOVER.md`.

Do not describe the comparison as significant, equivalent, or as a reproduction of the
paper's benchmark. The pilot has 6 units per condition from 3 tools.
