# Project state

Updated 2026-11-09T14:27:56.676171+00:00.

## Current milestone

Recovered real MCP source integrated; SliceMin and real-model DescGen executed; bounded three-tool pilot delivered. Original quantitative reproduction remains impossible (authors released nothing; artifact expired).

## Completed

- 12/12 paper servers cloned at pinned commits with licenses and tree hashes.
- 30/30 Python tools sliced with resolved entries.
- 10 valid local-model descriptions from 28 attempts; all failures preserved with diagnostics.
- Pilot on 3 tools across original/full/lite; DynVer execution documented as blocked.
- 161 software tests pass; earlier evidence preserved unchanged.

## Last successful experiment

`reports/recovered_descgen/` (DescGen pass) and `reports/pilot_3tools/pilot.json` (pilot).

## Sandboxed DynVer (new)

DynVer now executes real recovered tool bodies inside the macOS Seatbelt boundary.
18 tasks ran across `watch_topic`, `list_watches`, `unwatch_topic` under three description
conditions; each condition produced 4 supported / 2 refuted claims, so conditions did not
separate on this task set. Evidence: `reports/dynver_recovered/results.json`,
`reports/DYNVER_REPORT.md`. Remaining: adapter shims for the other servers.

## Known blockers

Original tasks/labels/prompts unrecovered; TypeScript unsupported; third-party execution gated; 4B model limits structural yield.

## Next exact action

Resume the corpus pass with an extended input cap for the two size-rejected tools, or add TypeScript slicing; exact reproduction awaits the authors' bundle.

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
