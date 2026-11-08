# Fresh environment setup

This guide describes supported CPU work. It does not reconstruct the authors' missing benchmark or authorize model charges/untrusted execution. Repository: `https://github.com/SamarthRamesha/trustdesc-reproduction`, default branch `main`, private. Read [completion audit](PHASE1_COMPLETION_AUDIT.md) before interpreting outputs.

## 1. Clone and inspect

Use an account explicitly granted access to this private repository. Do not paste credentials into commands or documents. GitHub CLI authentication or your existing Git credential manager can provide access.

```sh
git clone --branch main https://github.com/SamarthRamesha/trustdesc-reproduction.git
cd trustdesc-reproduction
git status --short
git log -5 --oneline
python3 --version
```

Python **3.11+** is required. CPU checks were run on macOS arm64 with Python **3.13.9** and **3.11.14**. Linux/Windows/Python 3.12 are not separately certified. No GPU, MCP server dependencies, LLM SDK, pandas or pytest is required for the core workflow. The standard-library tests also run with `python3 -I -S scripts/run_tests.py`.

## 2. Create an isolated dependency environment

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps .
.venv/bin/python -m pip check
.venv/bin/trustdesc --help
```

On Windows use `.venv\Scripts\python` and `.venv\Scripts\trustdesc`. The build tools are pinned (`setuptools==80.9.0`, `wheel==0.45.1`); runtime dependencies are empty. Installing them downloads public PyPI packages and requires network access. No credential is required for those packages. A fully offline alternative for repository commands is below. The GPU environment has separate requirements and is not installed here.

The wheel installation and CLI demo from a directory outside the checkout were validated during publication audit. The original package installed but its demo depended on checkout-only fixtures; the audited fix bundles the exact synthetic source as text package data, never imported/executed as a tool module. CLI installed-package and repository behavior now share the same fixture; regression coverage checks equality.

Offline source use needs no build tools/install:

```sh
python3 -m venv .venv
.venv/bin/python scripts/run_tests.py
PYTHONPATH=src .venv/bin/python -m trustdesc --help
```

`PYTHONPATH=src` is needed for `python -m trustdesc` before installation. Script wrappers bootstrap that path themselves. A virtual environment separates dependencies; it is not a security sandbox.

## 3. Run core validation

```sh
.venv/bin/python scripts/run_tests.py
.venv/bin/python scripts/validate_notebook.py
.venv/bin/python scripts/audit_repository.py
```

Current suite: **92 tests**, including the added installed-CLI resource regression. The preserved initial Phase 1 reports contain the historical 91-test result; that result was independently rechecked before adding the test. No failures/errors/skips are expected. `run_tests.py` writes its current results to `reports/test_results.json` / `test_output.txt`. To preserve historical evidence, execute these commands in a fresh clone/copy, review the outputs, and store new evidence under a distinct name rather than committing an accidental overwrite.

`audit_repository.py` checks intended files, Python syntax, JSON/notebook parsing, local Markdown file links, ignore probes and high-signal secret patterns over all reachable Git blobs. It is not a formal guarantee that every possible secret is absent. The script assumes a Git checkout; portable ZIP users can use tests/notebook validation without it. External links and Markdown anchors are not exhaustively network-validated.

## 4. Prepare the included synthetic tasks

```sh
.venv/bin/python scripts/prepare_dataset.py tests/fixtures/tasks.jsonl --output data/processed/synthetic
```

Expected: eight records, two server/tool groups, eight null labels, zero duplicates, evaluation-only split. `manifest.json` records input/output SHA-256 and statistics. Do not replace null labels or present these records as the original 208 tasks. [data/README](../data/README.md) explains external acquisition and restrictions.

## 5. Execute the supported local experiment

```sh
.venv/bin/trustdesc demo --output experiments/runs/fixture-001
.venv/bin/python scripts/run_local_experiments.py
```

Use a new directory name for each pipeline run. Demo invokes fixed, project-authored fixture functions with replayed semantic model responses. Expected: `summary`, `unsafe` and `input` claims supported on cases; `auto_prefix` refuted; `internal` not runtime-verifiable; `trust_decision=not_assessed`. Four task traces include five calls (two negative formula calls share one task). No original-model inference occurs.

Timing script reads `configs/experiments.json` and runs 20 repetitions, writing ignored raw runs plus curated reports. This command overwrites its report filenames, so use a separate clone/copy for a new measured run. Decision structure and normalized data hashes should match; wall time, allocation peaks, paths and timestamps should vary. Original-condition TSR/cost/attack metrics remain unmeasured.

## 6. Static source / generation / verification entry points

```sh
.venv/bin/python scripts/run_slicemin.py tests/fixtures apply_formula --output experiments/runs/slice.json
.venv/bin/python scripts/run_descgen.py --help
.venv/bin/python scripts/run_dynver.py --help
.venv/bin/python scripts/run_evaluation.py --help
```

Static parsing imports no input source. Use reviewed entry overrides for unsupported dispatch. Default `slice` performs no LLM debloating. DescGen requires replay or an explicitly configured provider; remote/paid flags and an explicitly supplied key are separate gates, not present authorization to spend. DynVer CLI uses `DisabledRunner` for unknown source. Do not add a subprocess shortcut to execute an MCP server.

`configs/default.json` and `models.json` document defaults/paper setup; they are not global files automatically loaded by every CLI command. `configs/experiments.json` and `small_model.json` are read by their corresponding scripts. Preserve command-line overrides and model audit logs.

## 7. Colab and packaging

Use [COLAB_HANDOVER](COLAB_HANDOVER.md) and its notebook. CPU cells are validated; GPU downloads/inference remain opt-in and unrun in this audit. A T4 option is an alternative-model experiment, not equivalent to four-GPU gpt-oss-120b. No Google Drive mount or ChatGPT-account access is needed.

From a clean committed checkout:

```sh
.venv/bin/python scripts/package_project.py --output ../trustdesc-audited.zip
.venv/bin/python scripts/validate_package.py ../trustdesc-audited.zip
```

The ZIP contains a source snapshot plus per-file hashes/commit ID; no Git history, environment, raw external data, private paper, model weights or secrets. GitHub preserves commit history. Compare archive `PORTABLE_MANIFEST.json` with the recorded Git commit; do not require a historical ZIP to match a newer commit. The initial `e3de3bc` ZIP is retained as historical evidence; an audited ZIP is produced separately.

## Recovery and known limits

If installation fails, preserve error output; use the offline source workflow and verify Python/build versions before changing code. If a pipeline fails, completed stages and audit logs remain in its fresh directory; do not reuse stale verification output. A new clone is the simplest clean restart. Network failures do not justify disabling TLS/security controls. Original artifacts, original models and isolated MCP execution remain external prerequisites, not missing setup commands hidden in this guide.
