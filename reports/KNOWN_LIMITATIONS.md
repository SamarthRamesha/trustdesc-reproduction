# Known limitations

Generated 2026-11-09T14:27:56.676171+00:00.

| Limitation | Effect |
|---|---|
| Original artifact expired; no code/data release | exact 52-tool/208-task reproduction impossible |
| No recovered tasks, labels or traces | TSR, Q3, Q4, Q5 not computable |
| Current HEAD, not paper revisions | tool sets may differ from the evaluated snapshot |
| Deterministic prefix selection | tool identity differs from the authors' random sample |
| TypeScript/JavaScript unsupported | 22 of 52 tool slots not sliceable |
| Static-only slicing | over-approximate; external/class/reflection calls unresolved |
| No debloating applied | unreachable-branch removal not exercised on real tools |
| Third-party execution gated | DynVer cannot produce behavioural verdicts; pilot stops at planning |
| 4B local model | not equivalent to the paper's frontier models; valid-structure yield is low |
| 4096-token input cap in this pass | two tools rejected purely on slice size |
| Local weights unpriced | cost comparison impossible |
| Software tests ≠ research labels | 161 passing tests validate code, not accuracy |

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
