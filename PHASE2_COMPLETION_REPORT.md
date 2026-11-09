# Phase 2 completion report

Updated 2026-11-09T14:27:56.676171+00:00.

## Status: engineering complete, original quantitative reproduction impossible

- Recovered all 12 paper-named public servers at pinned commits, with licenses and tree hashes.
- SliceMin sliced 30 Python tools; every entry resolved (20 by registration pattern, 10 by explicit qualified name).
- Real local MLX DescGen produced 10 valid descriptions from 28 attempts in this pass (35.7%).
- Bounded pilot carried 3 tools across original/full/lite conditions with real descriptions; DynVer execution is gated and recorded as blocked.
- 161 software tests pass; all earlier evidence (fixtures, public example, startup investigation) is preserved.

## What is not complete

Q1 TSR, Q2 cost, Q3 quality selection, Q4 TPA blocking and Q5 adaptive attacks cannot be evaluated without author records. No value is fabricated for them.

## Evidence

- `reports/FINAL_EXPERIMENT_RESULTS.json`, `reports/FINAL_EXPERIMENT_RESULTS.csv`
- `reports/FINAL_EXPERIMENT_ANALYSIS.md`, `reports/DATASET_PROVENANCE.md`, `reports/KNOWN_LIMITATIONS.md`
- `reports/recovered_descgen/` (run state, every raw model call, drafts)
- `reports/pilot_3tools/pilot.json`, `data/recovered_slices/`, `data/manifests/recovered_benchmark.json`
- `ORIGINAL_DATASET_*`, `SOURCE_PROVENANCE.json`, `DATASET_*`, `MISSING_RESEARCH_MATERIALS.md`
