# TRUSTDESC reproduction — capstone Phase 1

A working, tested **bounded reimplementation**, with explicit reproduction gaps. It is not the authors' code or a quantitatively successful reproduction. See [Phase 1 report](reports/PHASE1_REPORT.md) and [component status](docs/REPRODUCTION_STATUS.md).

The project supports **Hybrid Semantic-Behavioral Trust Verification for Third-Party AI Agent Tools**, concentrating on the TRUSTDESC research baseline. It does not implement the entire team's two-year system or a production trust gateway.

## What is available

- Complete analysis of the supplied 17-page arXiv:2604.07536v1 paper, evidence ledger, 12 server source links, seven attack example links and 201 quantitative reference entries.
- Import-free Python static reachability with helper/alias traversal, provenance, and optional per-function model-guided debloating. Static-only mode is clearly marked; TypeScript and dispatch fallback remain gaps.
- DescGen code sanitization, contextual model identifier filtering, structured description generation and claim coverage validation.
- DynVer task planning, bounded agent interface, trace checks, LLM judge interface, claim filtering, full/lite outputs and explicit uncertainty.
- A controlled runner for two newly authored synthetic tools. **Unknown source cannot execute through the CLI.** The controlled runner is not a sandbox.
- Task acquisition/preparation tools, reviewed-result TSR/overhead calculation, unit/integration tests, saved fixture evidence and optional Colab inference handover.
- One pinned public arxiv-mcp-server snapshot acquired for static inspection only; its source drift and unresolved calls are recorded in `reports/public_static_experiment.json`. External source bytes stay excluded from the portable ZIP.

No paid API calls, credentials, personal account connections, third-party tool execution or model downloads were used during local implementation.

## Run locally

From this directory, using Python 3.11+ (validated locally on Python 3.13.9):

```sh
python3 -m venv .venv
PYTHONPATH=src .venv/bin/python scripts/run_tests.py
PYTHONPATH=src .venv/bin/python -m trustdesc demo --output experiments/runs/my-first-fixture
.venv/bin/python scripts/run_local_experiments.py
.venv/bin/python scripts/prepare_dataset.py tests/fixtures/tasks.jsonl --output data/processed/synthetic
```

Core operation needs no `pip install`. Existing `.venv` can be reused. Each pipeline run requires a **fresh** output directory, preventing stale verification evidence after a failed rerun. `demo` uses hand-authored model responses and actually calls our safe fixture functions; it performs no model inference. All fixture data is labeled synthetic. Do not compare its execution time or decisions with paper TSR/model cost.

Static-only analysis of reviewed Python source:

```sh
.venv/bin/python scripts/run_slicemin.py tests/fixtures apply_formula --output experiments/runs/slice.json
```

Input source is parsed as text, never imported. Read warnings: unresolved/dynamic calls, class methods and unsupported registrations prevent sound coverage. Ambiguous/missing entries fail. `--entry module:function` is a reviewed override, not automatic dispatch inference.

Model-backed stage interfaces:

```sh
PYTHONPATH=src .venv/bin/python -m trustdesc describe --help
PYTHONPATH=src .venv/bin/python -m trustdesc verify --help
```

Supply a replay file or an explicit HTTP endpoint/model. Remote calls additionally require `--allow-remote --allow-paid` and `TRUSTDESC_API_KEY`; do not enable these without authorizing cost and source transmission. Literal loopback HTTP is supported without credentials for an already configured local model. Credentials are not loaded automatically from `.env`. No API endpoint/model ID is inferred from untrusted tool metadata. `verify` defaults to disabled execution; arbitrary MCP tools need a new isolated backend, not a CLI switch.

## Read and continue

Start with [review preparation](docs/REVIEW_PREPARATION.md), then [paper analysis](docs/PAPER_ANALYSIS.md), [methodology](docs/METHODOLOGY.md), [architecture](docs/ARCHITECTURE.md), [data analysis](docs/DATASET_ANALYSIS.md) and [decisions](docs/IMPLEMENTATION_DECISIONS.md). [Tests](reports/test_results.json), [local timing evidence](reports/local_experiments.json), [published reference values](reports/published_results.csv) and [comparison status](reports/COMPARISON.md) preserve the distinction between engineering checks and scientific results.

Use [Colab handover](docs/COLAB_HANDOVER.md) with `notebooks/colab/phase1_handover.ipynb`. CPU replay works without GPU. Optional Qwen 1.5B inference is a different, unrun experimental setting; the paper's gpt-oss-120b was served on four RTX PRO 6000 Blackwell GPUs. No free-T4 equivalence is claimed.

## Main blockers

The user-suggested anonymous artifact reports expiry; connection to this PDF remains unverified. Exact original prompts, 52 tool IDs/commits, 208 task texts, labels/logs and dated model identifiers were not obtained. The original source pool is **not** the original benchmark dataset. Original conditions require artifact recovery, licensed pinned source acquisition, a validated isolated runtime, and separately authorized model access. See [evidence ledger](docs/EVIDENCE_LEDGER.md) for discovery attempts and [limitations](docs/LIMITATIONS.md) for what the current software cannot establish.

Git is local only; nothing was pushed or published. The portable ZIP excludes the virtual environment, `.git`, raw external data, private PDF and secrets. Run `scripts/package_project.py` to regenerate it after committing changes.
