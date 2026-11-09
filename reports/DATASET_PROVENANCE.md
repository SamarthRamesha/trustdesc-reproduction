# Dataset provenance

Generated 2026-11-09T14:24:22.101360+00:00.

| Class | Content | Location |
|---|---|---|
| Original paper material | Table 1 servers/counts, TSR/cost figures, 7 attack outcomes | quoted in reports only |
| Recovered public source | 12 server repositories, pinned commits, licenses, tree hashes | `SOURCE_PROVENANCE.json`, clones under ignored `data/raw/` |
| Independently collected | our tool selection, slices, descriptions, measurements | `data/manifests/recovered_benchmark.json`, `reports/recovered_descgen/` |
| Reconstructed | prompts (not author text) | `src/trustdesc/descgen/prompts.py`, `reproduction/evidence.py` |
| Synthetic | 8 authored tasks over 2 authored tools | `tests/fixtures/`, `TASK_RESULTS.csv` |

The original artifact is expired (HTTP 410) with no Wayback capture; no original tool list, task, label or trace was recovered or invented. Third-party code is referenced, never redistributed.

See `ORIGINAL_DATASET_ACQUISITION_REPORT.md`, `DATASET_VALIDATION_REPORT.md`, `DATASET_LICENSES.md`.
