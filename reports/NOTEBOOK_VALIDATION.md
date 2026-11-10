# Notebook validation

Notebook: `TRUSTDESC_REPRODUCTION.ipynb` (12 cells, 6 code). Validated 2026-11-10.

## Structural checks — passed

| Check | Result |
|---|---|
| Valid `nbformat` JSON | yes, `nbformat.validate` passes |
| Cell order coherent | yes: intro → environment → historical note → recovered corpus → DynVer → figures → limitations |
| Imports available in the project venv | yes (`nbclient`, `ipykernel`, `nbformat`, `matplotlib`) |
| Referenced repository paths exist | 18/18 quoted paths resolve from the repository root |
| Relative paths | all paths are repository-relative; the notebook must be launched from the repo root |
| Hidden dependence on an earlier session | removed — the previous cell restored an embedded source snapshot, which would have overwritten newer evidence files |
| Expensive work re-run silently | no — the recovered-corpus cell is guarded, and the DynVer cell reuses the recorded run unless `TRUSTDESC_RUN_DYNVER=1` |

## What was actually executed

A copy of the notebook was executed **in a fresh kernel** with one cell neutralised (the
recovered DescGen/DynVer driver, whose run is already complete and which loads the 4-bit
model). Result: **5 code cells executed, 0 errors**. The executed copy with its real outputs
is kept as `reports/notebook_executed_copy.ipynb` (display images stripped to keep it small).

| Cell | Executed | Outcome |
|---|---|---|
| 1 · Environment check | yes | interpreter and 7 required paths verified |
| 2 · Historical artefacts present | yes | `reports/local_experiments.json` and `reports/COMPARISON.md` located |
| 3 · Recovered corpus driver | **no — neutralised** | loads the local model and re-enters resumable DescGen/DynVer; the run is already complete |
| 4 · DynVer | yes | reused the recorded 18 units instead of re-executing |
| 5 · Figures and statistics | yes | regenerated `STATISTICAL_RESULTS.json` and all 8 figures |

## What was not verified

- The recovered-corpus driver cell (cell 3) was not executed here. It was executed
  individually in earlier sessions; its outputs are the files under
  `reports/recovered_descgen/` and `reports/dynver_recovered/`.
- The notebook was not run end to end on a machine other than this Apple Silicon host.
- No cell was tested on Linux or Windows. The Seatbelt cell is macOS-only by design.

## Changes made for reproducibility

1. Removed the embedded source-snapshot restore. It wrote repository files from a stale
   archive, which would silently revert documentation and evidence. The checked-out
   repository is now the single source of truth.
2. Made the historical synthetic pipeline opt-in instead of implicit.
3. Added a sample-size and non-claim statement at the end, so a reader cannot mistake the
   pilot counts for a reproduced task success rate.
