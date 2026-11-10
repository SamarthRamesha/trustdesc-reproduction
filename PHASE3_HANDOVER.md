# Phase 3 handover

Updated 2026-11-09T14:27:56.676171+00:00.

## What you receive

1. A working Apple Silicon pipeline (`src/trustdesc`) with SliceMin, DescGen and DynVer stages.
2. A recovered, provenance-tracked corpus of 12 real MCP servers and 30 sliced Python tools.
3. Real model-produced descriptions and every raw model call, including rejected outputs.
4. A bounded three-tool pilot across original/full/lite conditions.
5. Preserved earlier evidence: authored fixtures, public-example study, startup investigation.
6. Honest reports separating paper values, our measurements and unknowns.

## Reproduce

```sh
python3.11 -m venv .venv && .venv/bin/python -m pip install -r requirements-apple-lock.txt
.venv/bin/python -m unittest discover -s tests -t .
.venv/bin/python scripts/discover_recovered_tools.py
.venv/bin/python scripts/build_recovered_benchmark.py
.venv/bin/python scripts/run_recovered_descgen.py --workspace reports/recovered_descgen
.venv/bin/python scripts/run_pilot_3tools.py --no-plan
.venv/bin/python scripts/report_recovered_dataset.py
.venv/bin/python scripts/report_recovered_experiments.py
.venv/bin/python scripts/run_dynver_recovered.py
.venv/bin/python scripts/report_dynver.py
.venv/bin/python scripts/report_final.py
```

The recovered clones are not committed (third-party licenses); re-clone the URLs in `SOURCE_PROVENANCE.json` at the recorded commits to rebuild `data/raw/`.

## Recommended next steps

1. Add TypeScript parsing to reach the remaining 22 tool slots.
2. Build a validated isolated runner so DynVer can execute real tools.
3. Request the authors' bundle using the prepared message in `MISSING_RESEARCH_MATERIALS.md`.
4. Re-run with a larger model if a paid API is authorized.

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
