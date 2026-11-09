# TRUSTDESC reproduction — capstone Phase 1

**Part 2 starts here: [TRUSTDESC_FULL_REPRODUCTION.ipynb](notebooks/colab/TRUSTDESC_FULL_REPRODUCTION.ipynb).** Open it in Google Colab, upload the final **TRUSTDESC_COLAB_READY.zip** and its checksum (or clone private main), and execute sections **1–16**. Start with CPU/no credentials, or explicitly select T4 + `qwen-small` for an alternative-model experiment. See [Colab handover](docs/COLAB_HANDOVER.md) and the [complete operator guide](docs/COLAB_EXPERIMENT_GUIDE.md). The final MacBook preparation task ends here; no further preparation prompt is needed.

The notebook orchestrates the existing modules across two controlled tools/eight synthetic tasks and all three original/lite/full conditions, with optional pinned public-source analysis and real-model stages, human review, resumable checkpoints, measured reports/plots and complete result export. Default replay produces 24 task records and withholds TSR until explicit human review. Paid models require secure keys and configuration-specific confirmation. Unknown MCP source never executes on the Colab host. Filename/CPU success does **not** establish full scientific reproduction.

**Start here:** [Central project handover](docs/PROJECT_HANDOVER.md), [completion audit](docs/PHASE1_COMPLETION_AUDIT.md), and [fresh setup](docs/FRESH_ENVIRONMENT_SETUP.md). This is a private research repository on `main`, with preserved original history. **119 tests currently pass** on Python 3.13.9 and 3.11.14. Historical Phase 1/publication reports preserve the independently verified 91/92-test snapshots; final Colab preparation evidence is in `reports/colab_preparation/final/`.

[GitHub publication verification](docs/GITHUB_PUBLICATION.md) records authenticated visibility/head/tree checks and tests from a fresh GitHub clone. Scientific reproduction remains incomplete.

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

## Research motivation and architecture

The paper is Ye, Zhang, Jia and Hu, [*TRUSTDESC: Preventing Tool Poisoning in LLM Applications via Trusted Description Generation*](https://arxiv.org/abs/2604.07536v1), 8 April 2026, arXiv v1. Agents rely on developer metadata for selection and arguments; explicit instructions or benign-looking capability exaggerations can manipulate them. TRUSTDESC addresses the description–implementation gap. It assumes source access and no overtly malicious runtime code; broader malware/trust policy is later capstone work.

The three-stage flow is `source → SliceMin → DescGen → DynVer → full/lite description + evidence`. SliceMin traverses reachable functions and optionally debloats using concrete call contexts. DescGen sanitizes source artifacts and generates summary, functionalities and input schema. DynVer plans tasks, records observations and filters claims using a judge interface. Local semantic decisions are replayed; fixed authored function calls and static transformations are real. Lite removes the refined functionality list only. Unknown-source execution is disabled, and no final trust decision is implied.

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

For a fresh private clone and an installed console command:

```sh
git clone --branch main https://github.com/SamarthRamesha/trustdesc-reproduction.git
cd trustdesc-reproduction
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps .
.venv/bin/python -m pip check
.venv/bin/trustdesc demo --output experiments/runs/installed-fixture-001
```

The installed demo now bundles inert synthetic source as package data and works outside the checkout. The audit found and fixed the original checkout-only fixture dependency; no algorithm was redesigned. Authentication must already grant access to this private repository; do not put tokens in URLs.

Tests and experiment scripts write standard report filenames. Run new checks/experiments in a **fresh clone/copy** to preserve earlier evidence, then store reviewed new outputs under distinct names. The independent publication checks follow that practice.

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

Use [Colab handover](docs/COLAB_HANDOVER.md) with the new primary `notebooks/colab/TRUSTDESC_FULL_REPRODUCTION.ipynb`. The older `phase1_handover.ipynb` remains historical. CPU replay works without GPU. Optional Qwen inference is an alternative, locally unrun GPU setting; the paper's gpt-oss-120b used four RTX PRO 6000 Blackwell GPUs. No free-T4 equivalence is claimed.

## Main blockers

The user-suggested anonymous artifact reports expiry; connection to this PDF remains unverified. Exact original prompts, 52 tool IDs/commits, 208 task texts, labels/logs and dated model identifiers were not obtained. The original source pool is **not** the original benchmark dataset. Original conditions require artifact recovery, licensed pinned source acquisition, a validated isolated runtime, and separately authorized model access. See [evidence ledger](docs/EVIDENCE_LEDGER.md) for discovery attempts and [limitations](docs/LIMITATIONS.md) for what the current software cannot establish.

The original Phase 1 snapshot was local only. This audit extends it into [the private GitHub repository](https://github.com/SamarthRamesha/trustdesc-reproduction), preserving all earlier commits. The portable ZIP excludes the virtual environment, `.git`, raw external data, private PDF and secrets. Create a **new, separately named** audited ZIP with `scripts/package_project.py --output ../trustdesc-audited-phase1.zip` after committing changes; retain the original archive as historical evidence.

## Repository map and continuation

| Path | Purpose |
|---|---|
| `src/trustdesc/` | SliceMin, DescGen, DynVer, models, runner, dataset, evaluation and CLI |
| `tests/` | Unit/integration tests and labeled synthetic fixtures |
| `configs/` | Default/paper model references and experiment settings |
| `data/manifests/` | Paper/source/attack provenance; [availability guide](data/README.md) |
| `scripts/` | Component runners, tests, acquisition, experiments, publication audit and packaging |
| `notebooks/colab/` | Independent CPU workflow and optional unrun GPU track |
| `reports/` | Preserved initial evidence and new publication checks; [index](reports/README.md) |
| `docs/` | Scientific analysis, decisions, audit, setup, security, roadmap and handover |
| `experiments/` | Layout guide; repeated raw outputs stay in ignored `runs/` |

`requirements.txt` has no runtime packages; build tools are pinned separately. `configs/default.json` and `models.json` document defaults rather than configuring every CLI automatically; experiment/small-model scripts read their named configs.

Next milestones are artifact/benchmark recovery, pinned licensed snapshots, parser coverage, validated isolated MCP/LangChain execution, explicitly authorized original-model access and human-reviewed original/full/lite evaluation. Extensions follow a measured baseline. See [NEXT_STEPS](docs/NEXT_STEPS.md) for prerequisites and evidence requirements.

The repository stays **private** and [LICENSE](LICENSE) reserves rights; no open-source grant was chosen on the user's behalf. Third-party materials retain their own rights, described in [NOTICE](NOTICE.md). Public visibility or licensing changes require explicit approval. Portable archives are separate commit-identified snapshots, while GitHub preserves history. Read the completion audit for current scientific status; earlier reports remain historical evidence.
