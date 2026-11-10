# Metrics report

Generated 2026-11-09T14:27:56.641209+00:00.

## Scope

Two separate evidence tracks are kept apart and never pooled:

| Track | Corpus | Tasks | Status |
|---|---|---|---|
| A. Authored fixture software check | 2 authored tools, 8 authored tasks | 8 | executed (earlier run, preserved) |
| B. Recovered public source | 30 Python tools from 12 paper-named servers | 0 | SliceMin + DescGen executed; DynVer blocked |

Track A is a software/agent check. Track B is a real-source supplementary experiment. Neither is the paper's 52-tool / 208-task benchmark.

## Track B: SliceMin on recovered real source

| Metric | Value |
|---|---|
| Tools sliced | 30 |
| Entry via registration pattern | 20 |
| Entry via explicit module-qualified match | 10 |
| Functions retained across slices | 146 |
| Internal call edges | 162 |
| Unresolved (external/unexpanded) calls | 886 |
| Tools in unsupported languages (JavaScript/TypeScript) | 22 |

SliceMin ran static-only: LLM debloating was not applied, so slices are over-approximate.

## Track B: DescGen with the local model

Model: `mlx-community/Qwen3-4B-Instruct-2507-4bit` at revision `50d427756c6b1b2fe0c0a10f67fbda1fc8e82c1b`, MLX 0.32.4 / MLX-LM 0.28.3, temperature 0.2. Qualification: passed.

| Metric | Value |
|---|---|
| Tools attempted | 28 |
| Valid structured descriptions | 10 |
| Rejected by the validator | 18 |
| Valid-structure rate | 35.7% |
| Median seconds per tool | 133.77 |
| Max seconds per tool | 248.9 |

| Server | Generated / attempted |
|---|---|
| arxiv-mcp-server | 3 / 4 |
| excel-mcp-server | 3 / 5 |
| imagesorcery-mcp | 1 / 3 |
| mysql_mcp_server | 1 / 1 |
| paper-search-mcp | 0 / 5 |
| wikipedia-mcp | 0 / 5 |
| yfinance-mcp | 2 / 5 |

## What is deliberately null

| Paper quantity | Our value | Why |
|---|---|---|
| Q1 task success rate (TSR) | — | no recovered task texts or human labels |
| Q2 generation cost / latency | — | paid providers were not used; local weights are unpriced |
| Q3 degraded-tool selection rate | — | no recovered degradation variants or task set |
| Q4 TPA blocking | — | no recovered attack fixtures with author outcomes |
| Q5 adaptive-attack trajectory | — | authors printed only fit statistics, not per-iteration data |

Reference values from the paper (not our measurements): TSR 84.1% original, 86.3% lite, 87.7% full; Gemini-3-Flash generation $0.013 / 25.7 s per tool; adaptive selection 44.7–67.4% over 15 iterations.

## Track A: authored fixture results (preserved, unchanged)

| Condition | Exact tool objectives | Agent completed | Oracle rate |
|---|---|---|---|
| original | 6/8 | 7/8 | 75.0% |
| lite | 6/8 | 6/8 | 75.0% |
| full | 6/8 | 3/8 | 75.0% |

These are eight authored tasks over two authored tools with an exact-trace oracle; they show no measured improvement and are not evidence about the paper's benchmark.

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
