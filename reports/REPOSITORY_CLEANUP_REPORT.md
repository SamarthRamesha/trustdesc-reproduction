# Repository cleanup report

Date: 2026-11-10. Baseline: commit `cba9837` on `origin/main`.

Scope: repository hygiene and presentation only. No experiment was rerun, no dataset, result,
figure or conclusion was changed, and no historical file was rewritten. Every deleted path is
regenerable build clutter; everything whose necessity was uncertain was kept.

## 1. Files and directories removed

| Removed | Type | Why it was safe |
|---|---|---|
| `__pycache__/` (14 directories under `src/`, `tests/`, `scripts/`) | Python bytecode caches | Regenerated on import; excluded by `.gitignore`; no evidence content |
| `phase3_handover.zip.sha256` | duplicate checksum file | Byte-identical checksum to the tracked `phase3_handover.sha256`; ignored by Git and not referenced anywhere |
| `phase3_handover.zip` (replaced, not lost) | superseded archive | Rebuilt from the cleaned tree; the previous validated archive remains in Git history at `cba9837` |

No tracked research file, dataset, figure, report, notebook, test or licence was deleted.

## 2. Files retained and why

- **Research evidence (essential):** `data/` (recovered slices, manifests, prompts, synthetic
  datasets), `reports/*.json` / `*.csv` (every recorded experiment output), `reports/dynver_recovered/`,
  `reports/recovered_descgen/`, `reports/new_experiments/`, `reports/pilot_3tools/`,
  `reports/apple_recovery/`, `reports/apple_silicon_delivery/`, `reports/colab_preparation/`.
- **Reproducibility support:** `src/`, `tests/`, `scripts/`, `configs/`, `requirements*.txt`,
  `pyproject.toml`, `SOURCE_PROVENANCE.json`, `ORIGINAL_DATASET_MANIFEST.json`.
- **Figures:** all 15 research figures as PNG + PDF plus the 15 `figure_data/*.csv` sources, and
  the legacy `reports/figures/local_engineering.png`, which is still embedded by
  `reports/PHASE1_REPORT.md` and `reports/COMPARISON.md`.
- **Historical reports:** `PHASE1_REPORT.md`, `PHASE2_COMPLETION_REPORT.md`,
  `reports/DYNVER_REPORT.md`, `reports/FINAL_DELIVERABLE_AUDIT.md` and the phase tables inside
  them keep their original numbers (91/161/165 tests, 8 figures). They are point-in-time
  evidence and were deliberately not rewritten.
- **Logs and executed notebooks:** `reports/notebook_executed_copy.ipynb`,
  `reports/test_output.txt`, `reports/test_python311.txt`, `reports/new_experiments_run.log`,
  `reports/recovered_descgen_run.log` are referenced by `docs/EXPERIMENT_LOG.md` or the
  evidence index and were kept.
- **Licensing and attribution:** `LICENSE`, `NOTICE.md`, `CITATION.cff`, `DATASET_LICENSES.md`,
  pinned public-example licences under `data/`.

## 3. Files reorganised

None. The existing layout already separates implementation (`src/`), tests (`tests/`),
reproducible commands (`scripts/`), inputs (`data/`), experiment records (`experiments/`),
findings (`reports/`, `reports/figures/`) and supporting documentation (`docs/`). Moving files
would have required touching imports, notebooks, report links and the packaging manifest for
no clarity gain, so paths were preserved.

## 4. Documentation improved

- **`README.md`** rewritten as the professional entry point: project description, research
  problem, three-stage architecture table, implementation overview, scope-labelled results
  table, all 15 figures linked with one-line captions, project structure, installation,
  reproduction commands, testing, known limitations and handover link. Badges are static and
  accurate (Python 3.11, 207 tests, paper benchmark not released); no CI badge is claimed.
- **`FINAL_PROJECT_STATUS.md`**: baseline commit corrected to `cba9837`, test count 165 → 207,
  the "no attack/poisoning experiments" row replaced with the accurate scope (authored probes
  exist; no defence claim, no adaptive-attack evaluation), and pointers added to the
  robustness reports and figures 9–15.
- **`TEAM_HANDOVER.md`**: updated commit, test count and figure count; added navigation lines
  for the cleanup map and the robustness reports.
- **`METHODOLOGY.md`, `METRICS_REPORT.md`, `PROJECT_STATE.md`, `PHASE3_HANDOVER.md`**: shared
  checkpoint block updated from 165 to 207 tests and 8 to 15 figures. These are live summary
  blocks, not recorded experiment outputs.
- The 0/19 independent injection challenge result, the 12/12 development result and the 14/14
  negation result now appear together, explicitly separated, in the README and status file.
  The original paper's unavailable benchmark limitations remain explicit in the README, status
  file and `docs/LIMITATIONS.md`.

## 5. `.gitignore` changes

Added an "Editor and OS clutter" block: `**/.DS_Store`, `*.swp`, `*.swo`, `*~`, `.idea/`,
`.vscode/`, `*.bak`, `*.orig`, `*.tmp`. Existing entries for virtual environments, model
caches, caches, `.env`, archives, logs and the automatic notebook scratch directory were
already correct and were left unchanged.

## 6. Tests and validation results

| Check | Result |
|---|---|
| Full test suite (`unittest discover`) | **207 tests, OK** (5.2 s) |
| Internal Markdown link check across all `.md` files | **0 broken links** |
| Figure existence | 15 research figures as PNG **and** PDF, 15 `figure_data/*.csv` sources, legacy phase-1 PNG present |
| Notebook | Root notebook retained unchanged; executed copy and validation records preserved |
| Secrets scan | No credentials, keys or tokens tracked; `.env.example` only, `.env*` ignored |
| Large files | Largest tracked file is the delivered archive; next largest are recorded JSON/notebook evidence and 300 DPI figures |
| Nested archives | None |
| ZIP CRC (`unzip -t`) and SHA-256 | Pass, see section 8 |

## 7. Final repository structure

```
README.md                 entry point and results
FINAL_PROJECT_STATUS.md   implemented / evaluated / not recoverable
TEAM_HANDOVER.md          continuation guide
PROJECT_STATE.md          current milestone and next action
LICENSE, NOTICE.md, CITATION.cff, DATASET_LICENSES.md
pyproject.toml, requirements*.txt, .gitignore, .env.example
TRUSTDESC_REPRODUCTION.ipynb
src/trustdesc/            implementation (slicemin, descgen, dynver, sandbox, evaluation, ...)
tests/                    unit + integration (207 passing)
scripts/                  acquisition, pipeline, analysis, figures, packaging, validation
data/                     recovered slices, manifests, prompts, synthetic inputs
experiments/              experiment configuration and record
notebooks/colab/          historical Colab entry points
reports/                  21 reports, robustness studies, experiment JSON/CSV, figures/
docs/                     23 supporting documents (architecture, sandbox, limitations, ...)
configs/                  pinned model and run configuration
phase3_handover.zip + .sha256   delivered archive and checksum
```

## 8. Final archive

- Archive: `phase3_handover.zip`, contains source, tests, data, reports, all 15 figures, the
  notebook and handover instructions.
- Nested ZIPs: none. Virtual environments, caches and model weights: excluded.
- Members: **894 files** (893 validated payload files plus the archive directory entry),
  uncompressed 12,897,935 bytes, compressed ~6.0 MB. SHA-256 is in
  `phase3_handover.sha256`; `unzip -t` reported no errors, `shasum -c` passed and
  `scripts/validate_package.py` validated 893 files bound to commit `96a868c`.

## 9. Commit and push

Cleanup commit followed by an archive-rebuild commit, both pushed to `origin/main` without
force. Working tree clean afterwards; full history preserved.

## 10. Deliberately left untouched

| Item | Reason |
|---|---|
| `reports/apple_silicon_delivery/.../delivery_diagnostics/` | Contains files byte-identical to `reports/apple_recovery/`. They belong to a delivered, validated run bundle and may be referenced by its manifests or the archive list; deduplicating risked breaking provenance, so it was preserved. |
| `reports/figure_data/` (5 legacy CSVs) next to `reports/figures/figure_data/` (15) | Both are referenced by historical generation paths; merging would change recorded paths. |
| `reports/test_output.txt`, `reports/test_python311.txt`, `notebook_validation.txt` | Old logs, but referenced as evidence in `docs/EXPERIMENT_LOG.md` and `reports/README.md`. |
| `reports/figures/local_engineering.png` | Legacy phase-1 figure, still embedded in two historical reports. |
| `trustdesc_local/` (empty) | Local run workspace path used by reproduction commands; zero bytes, no evidence. |
| Root-level historical reports (`PHASE1_REPORT`, `PHASE2_COMPLETION_REPORT`, `FINAL_PROJECT_COMPLETION_REPORT`, `FAILURE_ANALYSIS`, ...) | Each records a distinct point-in-time result; consolidation would destroy provenance. |
| `model_cache/`, `.venv/`, `model_download.log` | Ignored local runtime state; deleting the environment would break reproduction for the next person. |

## Honest summary

The repository now has one clear entry point, current and scope-labelled numbers, no build
clutter, zero broken internal links and an intact evidence trail. Nothing was removed to make
the tree look smaller: the only deletions were bytecode caches, a duplicate checksum and the
superseded archive copy. The scientific position is unchanged, including the negative 0/19
injection challenge result.
