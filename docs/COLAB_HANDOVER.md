# Independent Colab handover

The notebook is `notebooks/colab/phase1_handover.ipynb`. Use the delivered ZIP and its `.sha256` companion. No Codex connection, Google Drive mount, account integration or private PDF upload is needed. The student opens Colab themselves. Nothing has been uploaded by this implementation session.

## Choose the workload

| Track | Hardware | What it can demonstrate | Validation status |
|---|---|---|---|
| A: core tests/replay/data | CPU, Python 3.11+, no GPU | Engineering mechanics and actual safe fixture traces | Tested locally on Python 3.13.9 and 3.11; portable notebook cells executed locally |
| B: optional small-model inference | CUDA GPU; a 16GB T4 is a reasonable exploratory target, not a guarantee; short capped contexts | Real DescGen inference and optional fixture pipeline with a different 1.5B model | Prepared/compiled; GPU/model install/inference **not run locally** |
| C: original paper settings | Commercial access with separate approval, or paper's four RTX PRO 6000 Blackwell GPUs for gpt-oss-120b | Original-condition evaluation only after recovering exact artifacts | Blocked; no free-Colab equivalence or required per-GPU memory/precision inferred |

TRUSTDESC requires inference, not a training/fine-tuning job. A GPU is unnecessary for track A or an authorized externally hosted model. The paper does not report exact peak memory, precision, model serving stack or needed context lengths. Do not launch gpt-oss-120b locally on the 16GB Mac or assume one free Colab GPU reproduces the paper.

Track B uses [Qwen2.5-Coder-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct), an **alternative** model, not an evaluated TRUSTDESC improvement. Official model card lists Apache-2.0. The observed fixed revision prefix is `2e1fd39`; the adapter records the full resolved configuration commit when loaded. Sources: [official commit history](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct/commits/main), [Transformers 4.57.1](https://pypi.org/project/transformers/4.57.1/), [PyTorch 2.9.0](https://pypi.org/project/torch/2.9.0/). FP16 weights alone are roughly 3GB for 1.5B parameters, but activations, context, CUDA allocations and package/runtime memory add overhead. This arithmetic is an estimate, not a measured peak. Reserve several GB download/cache space and inspect actual GPU/RAM/disk before loading.

## Exact execution order

1. Read REPRODUCTION_STATUS and the notebook introduction. Select CPU runtime for track A. Upload the notebook through Colab's File→Upload notebook.
2. Run runtime inspection; confirm Python >=3.11. For track B, select a CUDA GPU runtime yourself and inspect `nvidia-smi`/available memory. Do not pay for an upgrade without deciding to do so.
3. Run the archive upload cell. Upload only `trustdesc-phase1.zip`, paste its delivered SHA-256 into the expected-hash variable, and verify it. Extraction rejects traversal/links/duplicate members/oversized data and validates all per-file hashes **before project code runs**. No Drive/account mount is used.
4. Run core tests with the notebook's exact command (`python scripts/run_tests.py`). Core runtime has no external dependencies. Check `reports/test_results.json` and zero failures/errors/skips.
5. Run synthetic dataset preparation, then the fixture pipeline into a fresh timestamped directory. Inspect the four execution traces: ordinary acceptance, missing-prefix error, two blocked-function formula errors, and a valid input case. Inspect the false claim's removal. These expectations test mechanics only.
6. Run the 20-repetition engineering timing script. It records raw local runs, one compact example, source/config hashes, platform and Python allocation peaks. GPU is unused in this track.
7. Optionally enable track B by setting `RUN_GPU_EXPERIMENT=True`. This explicitly opts into public model/package downloads in your own Colab runtime. It does not transmit private source or use paid APIs. Install `notebooks/colab/requirements-gpu.txt` **in a fresh runtime**, then restart the runtime if Colab requests it and rerun import/setup cells. The listed direct package versions are pins, not a validated CUDA lockfile; preserve `pip freeze` and GPU/driver details.
8. Run `python scripts/run_small_model.py --allow-download --stage description --output <fresh path>`. This uses only the synthetic fixture. The adapter disables custom remote model code and uses safetensors, FP16, eager attention, temperature .2, seed 42, input cap 4,096 tokens, output cap 2,048. No input is silently truncated. Original paper reasoning setting was default; no equivalence is claimed for Qwen.
9. Inspect `draft.json`, `audit.json`, `run.json`, and any `error.json`. A 1.5B model may fail strict JSON or semantic checks. Failures are experimental observations, not grounds to loosen checks silently. The raw response is retained when a completion was generated. Model-loading failures may leave no inference audit.
10. Optional next experiments, after description inspection: add `--debloat` to exercise actual model-guided SliceMin on the fixture, or `--stage pipeline` for model-planned fixture tasks/judgments. Each is a new fresh directory and a **different setting**. An exhausted context, bad JSON, unsupported schema, blocked action or model error should remain visible; it does not become a successful benchmark run.
11. Export only `reports/` and the current run directory through the notebook's results ZIP cell. Download it to your computer using Colab's `files.download`. Do not export model caches, credentials, arbitrary runtime files or unreviewed third-party data. Store result ZIP alongside its config/source hash.

Equivalent commands from the repository root:

```sh
python scripts/run_tests.py
python scripts/prepare_dataset.py tests/fixtures/tasks.jsonl --output data/processed/synthetic
PYTHONPATH=src python -m trustdesc demo --output experiments/runs/my-fixture-001
python scripts/run_local_experiments.py
# Optional, only in your selected GPU runtime after download opt-in:
python -m pip install -r notebooks/colab/requirements-gpu.txt
python scripts/run_small_model.py --allow-download --stage description --output experiments/runs/qwen-desc-001
```

## Original dataset/model setup

No original author dataset is bundled or silently replaced. Use `data/manifests/paper_servers.json` to identify the source pool; recover exact tool list, commits, tasks and original/full/lite metadata before original evaluation. Check licenses and preserve hashes. Never execute server setup or unknown tool code directly in Colab as if Colab were a validated sandbox. Our real-source Runner remains disabled. Original LangChain/MCP execution and sandbox integration are outstanding implementation work, not hidden notebook setup.

For the optional **static-only** public-source check already run locally, reacquire the pinned archive listed in `data/manifests/acquired_sources.json` with `scripts/acquire_artifact.py`, its exact checksum and Apache-2.0 review note; then run `python scripts/run_public_static.py --archive <downloaded ZIP>`. It extracts inspected Python/license text to a fresh ignored directory and uses AST only. The external archive is not bundled. Its current 19-tool list must not be substituted for the paper's four selected arxiv tools.

`configs/models.json` preserves paper display names and deliberately leaves provider IDs null. Confirm exact model IDs/versions with the selected service and obtain cost/data-transmission approval before use. For an authorized remote HTTP model, supply `TRUSTDESC_API_KEY` explicitly in the **student's own** session and both access flags. Do not print keys, save them to outputs, or include them in ZIPs. No key is required for the optional public Qwen path. The handover does not connect to ChatGPT or borrow account tokens.

## Checkpoints, disconnect recovery and validation

Stage artifacts are independently persisted (`slice.json`, `draft.json`, `verification.json`, `pipeline.json`, `model_audit.json`). Optional model experiment also saves `run.json`, audit and errors. A fresh run directory prevents stale success evidence. Download checkpoints after substantial inference, since free Colab storage is ephemeral. If disconnected, reopen notebook, re-upload the verified project ZIP, recreate environment and re-upload only your own reviewed checkpoints if needed. Run from a new directory; reuse a saved slice/draft with `describe`/`verify` where appropriate rather than pretending a partial stage finished. `verify` still refuses unknown source execution. Reusing responses as replay must be labeled replay, not fresh inference.

CPU validation should match the test suite and fixture decisions; timing should **not** match exactly across machines. For model inference validate config/revision, response shape, source grounding, input constraints and raw traces manually. A script exit code or a supported claim on one case is insufficient to claim scientific reproduction. Preserve unsuccessful runs and schema failures; do not replace them with estimated successes.

## Remaining limits

No actual Colab session, GPU package installation or model inference has been run from this Codex session. Only notebook structure/compilation, portable cells, CPU tests and packaging were validated locally. Free GPU availability/driver compatibility are not guaranteed. Original large-model, paid-provider and hostile-tool experiments remain blocked by the documented missing resources/approval/isolation conditions.
