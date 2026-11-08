# Experiment and debugging log

All work below occurred on 8 November 2026. Exact UTC timestamps for saved checks/runs are in their JSON records. Client timezone is Asia/Kolkata. No paid models, credentials, personal connections, downloaded server execution or new local model weights were used.

| Check / experiment | Command / method | Actual outcome | Interpretation |
|---|---|---|---|
| Environment/paper | Local file metadata, PDF parser, full page extraction, visual table/figure checks | 17-page arXiv v1 confirmed; source fingerprint saved | Initial file utility's seven-page estimate corrected before implementation |
| Anonymous artifact | Research browser + one interactive public-page load | Service reports expired | Original artifacts not obtained; not proof of official linkage |
| Initial network checks | Public Python URL requests from sandbox | DNS failures for artifact, GitHub and arXiv | Environment restriction, not global resource disappearance |
| Bounded later acquisition | Scoped public-network command, no authentication | Pinned arxiv source downloaded, 490,822 bytes, Apache-2.0 metadata/license inspected | One source snapshot, not original benchmark; raw bytes excluded from Git/ZIP |
| Alternate release search | Public GitHub repository search `trustdesc` | Zero name/description matches | Bounded negative result; not exhaustive code/private/renamed search |
| Early SliceMin/DescGen tests | `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` | 45 passed, 0 failed/error/skipped | Reachability, rewrite constraints, sanitizer and provider failure cases |
| DynVer/data/evaluation integration | Same full test command after additional modules | 85 passed, 0 failed/error/skipped | Fixture calls, negative evidence, missing labels, matched overhead |
| CLI/stale-output/dedup regression | `scripts/run_tests.py` | 89 passed, 0 failed/error/skipped | Added output freshness and conflicting-label safeguards |
| Optional adapter and final core suite | `scripts/run_tests.py` via portable notebook validation | 91 passed, 0 failed/error/skipped | Includes GPU download gate and strict JSON parser; does not run GPU inference |
| Python 3.11 compatibility | `PYTHONPATH=src /opt/homebrew/bin/python3.11 -m unittest discover -s tests -v` | 91 passed, 0 failed/error/skipped | Supports portable CPU runtime claim; output in test_python311.txt |
| Synthetic data preparation | `scripts/prepare_dataset.py tests/fixtures/tasks.jsonl --output data/processed/synthetic` | 8 records, 2 tools, 2 synthetic servers, 8 unknown labels, 0 duplicates | Evaluation-only split; no fabricated author data |
| Synthetic engineering timing | `scripts/run_local_experiments.py`, 20 repetitions | Saved wall times/allocation peaks/config/source hashes and actual fixture logs | Replay is not inference; not paper latency/TSR/security evaluation |
| Real-source static experiment | `scripts/run_public_static.py --archive data/raw/arxiv-public/snapshot.zip` | 31 Python files parsed, 23 reachable functions from reviewed handler, 194 unresolved call sites; current list_tools has 19 entries | Automatic dispatch unsupported; no completeness guarantee; source drift from paper |
| Notebook | `scripts/validate_notebook.py --execute-portable` | 10 code cells compiled; 5 portable cells executed | Upload/GPU/download/export cells not executed; no Colab session connected |

## Debugging and safety regressions

Before the first test run, review caught improper AST list/optional-node comparison in rewrite validation; it was replaced with element-wise dumps and explicit None handling. No failure was hidden or skipped. Later review identified that a failed rerun could leave an old verification file; the pipeline now requires a fresh directory and a regression test covers it. Dataset duplicate-content conflicts now fail instead of silently dropping contradictory labels/provenance. ZIP processing rejects symlinks/traversal and extracts only intended text for public static checks. The public-source script uses a fresh extraction directory to avoid mixing revisions.

No failing test was suppressed. HTTP calls in tests are mocked transport tests; timeout/dependency/sandbox failures are controlled negative cases, not successful real-service runs. Cases not implemented (TypeScript, real isolation, original MCP/LangChain, paid four-model evaluation) are research gaps, **not skipped passing tests**. Optional GPU failures have not been observed because that experiment was not executed.

## Evidence locations

`reports/test_results.json`, `test_output.txt`, `test_python311.txt`, `notebook_validation.txt`, `synthetic_dataset_manifest.json`, `local_experiments.json`, `local_example/`, `public_static_experiment.json`, `public_repository_search.json`, and `figures/local_engineering.png`. Local repeated raw runs are referenced by `raw_run_directory` and ignored by Git; one full example is versioned. External archives/transformed source remain in ignored raw/interim folders and are not in the portable package.
