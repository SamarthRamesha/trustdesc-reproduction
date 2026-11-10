# TRUSTDESC: independent reproduction and robustness study

![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![Tests](https://img.shields.io/badge/tests-207%20passing-brightgreen)
![Benchmark](https://img.shields.io/badge/paper%20benchmark-not%20released-lightgrey)

An independent, auditable implementation of the three TRUSTDESC stages from
[Ye et al., *TRUSTDESC: Preventing Tool Poisoning in LLM Applications via Trusted
Description Generation*](https://arxiv.org/abs/2604.07536v1), plus a set of deliberately
adversarial experiments that test how far the implementation's claims actually reach.

**The original scientific reproduction remains incomplete.** The paper's authenticated
52-tool / 208-task identities, snapshots, task texts, prompts, labels and traces were never
released, so no task-success rate, cost or quality-selection number from the paper can be
reproduced. Everything measured here is labelled as authored fixtures, independently
collected data or synthetic probes, and is never presented as the paper's benchmark result.

Start here:

| Document | Purpose |
|---|---|
| [FINAL_PROJECT_STATUS.md](FINAL_PROJECT_STATUS.md) | What is implemented, evaluated, not implemented and not recoverable |
| [TEAM_HANDOVER.md](TEAM_HANDOVER.md) | How to continue the project, file by file |
| [reports/PROJECT_SUMMARY.md](reports/PROJECT_SUMMARY.md) | Plain-language overview of findings |
| [docs/LIMITATIONS.md](docs/LIMITATIONS.md) and [reports/KNOWN_LIMITATIONS.md](reports/KNOWN_LIMITATIONS.md) | Explicit scope of every claim |
| [reports/figures/FIGURE_INDEX.md](reports/figures/FIGURE_INDEX.md) | All 15 figures with their source data |

## Research problem

Tool descriptions are the interface between an LLM agent and a third-party tool, and they
are attacker-controlled. A malicious server can describe a benign-looking tool while
instructing the model to read secrets, exfiltrate data or ignore the user. TRUSTDESC attacks
that problem in three stages: it recovers what a tool actually does from source, generates a
trusted description from that behaviour, and verifies the generated claims by executing the
real tool. This repository asks a narrower, checkable question: **can that pipeline be built
and measured honestly on the material that is actually available, and do its security
components survive contact with data they were not tuned on?**

## TRUSTDESC three-stage architecture

| Stage | Idea in the paper | This implementation |
|---|---|---|
| **SliceMin** | Slice minimal source needed to describe a tool | Import-free Python AST registration detection, call-graph slicing, cross-file reachability, aliases, nested calls, dispatcher patterns, source spans and hashes |
| **DescGen** | Generate a description from the slice, not from the server's prose | Real local model generation with slice-grounded prompting, structured output, mechanical validation, source attribution and resumable state |
| **DynVer** | Verify description claims by executing the tool | Bounded agent actions inside macOS Seatbelt, real observations, model judging, negation-aware claim checks, supported/refuted/inconclusive filtering, bounded correction and retesting |

A matched evaluation compares Original, lite and full description conditions on identical
tasks with one fixed task agent and exact trace oracles.

## Implementation overview

- **Local only.** MLX on Apple Silicon with a pinned 4-bit Qwen3-4B-Instruct-2507; a PyTorch
  adapter supports MPS and CPU. No paid inference, no API keys, no model downloads at test
  time. Model identity is fixed across conditions and recorded in manifests.
- **Sandboxed execution.** Deny-by-default Seatbelt policy: scratch-only writes, no network,
  process denial, resource limits, isolation canaries that must pass before any experiment.
  A failed execution can never produce a `supported` verdict.
- **Provenance first.** Every run binds code, dataset, prompts, model, configuration and
  runtime; source identities are pinned commits and Git blobs, with licenses recorded.
- **Failures are kept.** Rejected generations, failed checkpoints and inconclusive verdicts
  are preserved rather than overwritten or retried into a cleaner-looking result.

## Key measured results

Canonical numbers, regenerated from recorded evidence by `scripts/analyze_statistics.py`
and `scripts/generate_figures.py`. Datasets and experiments are reported separately and are
never pooled into a single detection rate.

| Measurement | Value | Scope |
|---|---|---|
| Paper MCP servers recovered | 12 / 12 at pinned commits | independently collected |
| Python tool slots sliced | 30 / 30 | deterministic discovery order, not the paper's sample |
| TypeScript/JavaScript slots unsupported | 22 | gap, not a result |
| Valid descriptions | 10 / 28 = 35.7% (Wilson 95% 20.7–54.2%) | local 4-bit model |
| Rejections | 8 generation deadline, 7 identifier normalisation, 2 token cap, 1 schema | recorded |
| Claims generated | 88 (6–11 per description) | |
| Sandboxed executions | 18 (3 tools × 3 conditions × 2 tasks) | underpowered pilot |
| Verdicts | 12 supported, 6 refuted, 0 inconclusive | file-existence claims only |
| Per-condition result | 4 supported of 6 in every condition; no separation observed | 6 units per condition |
| Matched-task comparison | 3/3/3 consistent across conditions | 3 valid tasks |
| Poisoning detection | TP 5, FN 1, TN 3, FP 0 after negation correction (6/6 eligible) | 9 eligible authored cases |
| **Injection screen, development set** | **12/12** (TP 12, FP 0, TN 8, FN 0; 3 ambiguous excluded) | 20 authored synthetic cases, rules tuned on this set |
| **Injection screen, independent challenge set** | **TP 0, FP 1, TN 7, FN 19 — recall 0/19, FPR 1/8** | 30 unseen descriptions written after the rules were frozen |
| **Negation-aware layer, controlled probes** | **14/14 match pre-registered verdicts** (2 supported, 4 refuted, 4 inconclusive, 4 deferred) | 14 new probes; two defects found and fixed |
| Automated tests | 207 passing | software validation, not experimental labels |
| Task success rate | **not computed** | paper benchmark never released |

**The 0/19 result is the most important number here.** A static keyword screen that scored
perfectly on its own development set caught none of 19 independently worded attacks,
including all 4 indirect attacks, and raised one false positive on a benign audit-logging
description. It is reported as a negative result, not patched with new patterns after the
fact. The 12/12 development figure must never be quoted as general detection effectiveness.

## Research figures

All 15 figures are generated from recorded evidence, as 300 DPI PNG and vector PDF, with the
exact plotted values written to `reports/figures/figure_data/*.csv`.
See [reports/figures/FIGURE_INDEX.md](reports/figures/FIGURE_INDEX.md) for source data and
captions.

| # | Figure | Shows |
|---|---|---|
| 1 | [Dataset coverage](reports/figures/fig1_dataset_coverage.png) | 12/12 servers, 30 Python slots, 22 JS/TS slots unsupported |
| 2 | [DescGen yield](reports/figures/fig2_descgen_yield.png) | 10 valid of 28 attempts and the rejection categories |
| 3 | [DynVer verdicts](reports/figures/fig3_dynver_verdicts.png) | Verdict split per condition with sample sizes |
| 4 | [Three-condition comparison](reports/figures/fig4_condition_comparison.png) | The identical 4/2 split, annotated non-significant |
| 5 | [Execution coverage](reports/figures/fig5_execution_coverage.png) | 18 real process outcomes |
| 6 | [Failure taxonomy](reports/figures/fig6_failure_taxonomy.png) | Generation, language, dependency, shim and benchmark gaps |
| 7 | [Component completion](reports/figures/fig7_project_progress.png) | Completion per component with explicit denominators |
| 8 | [Research summary](reports/figures/fig8_research_summary.png) | Supported rate by condition beside the reproduction ledger |
| 9 | [Matched-task comparison](reports/figures/fig9_matched_comparison.png) | 3 valid tasks × 3 conditions, no separation |
| 10 | [Poisoning detection](reports/figures/fig10_poisoning_detection.png) | TP 5, FN 1, TN 3, FP 0 over 9 eligible cases |
| 11 | [Negation-aware re-judging](reports/figures/fig11_judge_reliability.png) | Corrected S1 verdict and probe behaviour |
| 12 | [Static injection screening](reports/figures/fig12_injection_detection.png) | Development set: TP 12, FP 0, TN 8, FN 0 |
| 13 | [Injection screen, challenge set](reports/figures/fig13_injection_robustness.png) | TP 0, FP 1, TN 7, FN 19 on unseen cases |
| 14 | [Negation layer robustness](reports/figures/fig14_negation_robustness.png) | 14/14 pre-registered probes, 4 deferrals |
| 15 | [Detector error analysis](reports/figures/fig15_detector_error_analysis.png) | Development 12/12 vs challenge 0/19, kept separate |

## Project structure

```
README.md, FINAL_PROJECT_STATUS.md, TEAM_HANDOVER.md   entry points and handover
src/trustdesc/            implementation: slicemin, descgen, dynver, sandbox, evaluation, dataset
tests/                    unit and integration tests (207 passing)
scripts/                  every reproducible command: acquisition, slicing, generation, DynVer,
                          analysis, figures, packaging, validation
data/                     recovered slices, manifests, prompts, synthetic and experiment inputs
experiments/              experiment configuration and records
notebooks/                Colab entry points (root notebook is the self-contained local run)
reports/                  findings, methodology, limitations, robustness studies
reports/figures/          15 figures (PNG + PDF) with figure_data/*.csv sources
docs/                     supporting documentation, architecture, sandbox, reproduction status
configs/                  pinned model and run configuration
```

Generated archives (`phase3_handover.zip`), virtual environments, model caches and raw run
directories are ignored; the archive is force-added because it is the delivered artefact.

## Installation

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-apple.txt   # Apple Silicon / MLX
# or: -r requirements-colab.txt on Linux/Colab, -r requirements.txt for the minimal set
```

No API keys are required. Model weights are downloaded once from public sources on first use
and cached outside the repository.

## Reproduction commands

```sh
# Full local pipeline (slicing, description generation, sandboxed verification, reports, ZIP)
PYTHONPATH=src .venv/bin/python scripts/run_local_reproduction.py --workspace trustdesc_local

# Component by component
PYTHONPATH=src .venv/bin/python scripts/run_slicemin.py
PYTHONPATH=src .venv/bin/python scripts/run_recovered_descgen.py
PYTHONPATH=src .venv/bin/python scripts/run_dynver_recovered.py
PYTHONPATH=src .venv/bin/python scripts/report_dynver.py

# Analysis and figures (recorded data only; no executions, no model calls)
.venv/bin/python scripts/analyze_statistics.py
.venv/bin/python scripts/generate_figures.py
.venv/bin/python scripts/analyze_new_experiments.py
.venv/bin/python scripts/analyze_final_experiments.py
.venv/bin/python scripts/analyze_robustness.py

# Package and validate the handover archive
PYTHONPATH=src .venv/bin/python scripts/package_project.py --output phase3_handover.zip
PYTHONPATH=src .venv/bin/python scripts/validate_package.py
```

The primary GUI-free entry point is the notebook: open
[TRUSTDESC_REPRODUCTION.ipynb](TRUSTDESC_REPRODUCTION.ipynb) and choose **Run All**. It
embeds and verifies its source, builds an environment, qualifies a real quantized model,
runs the pipeline and exports a checksummed archive. Historical Colab entry points remain
under [notebooks/colab](notebooks/colab) and are not superseded by the local notebook.

## Testing

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -t .
python3 scripts/check_python_startup.py --context terminal --output startup-check.json
```

207 tests pass. They are software validation, not experimental labels: they show the code
behaves as recorded, not that the research claims are true. The robustness tests pin the
recorded 0/1/7/19 challenge outcome so a rule change cannot silently rewrite the finding.

## Known limitations

- **No paper benchmark, no task success rate.** The original artefact returns HTTP 410 and
  was never archived; tool identities are a deterministic prefix of discovery order because
  the authors' sampling seed was never released. These tools are not the paper's benchmark.
- **Underpowered pilot.** 6 units per condition from 3 tools, unpaired, single judge. No
  significance, equivalence or reproduction claim is made.
- **Screening does not generalise.** Keyword screening detects literal attack shapes only
  (0/19 on paraphrased attacks). It is experimental and is not wired into the pipeline as a
  defence; no security claim rests on it.
- **Negation checks are narrow.** The layer handles negation and exception-scope deferral
  for file-existence claims; it does not validate arbitrary semantic claims.
- **Sandbox scope.** Offline Python source execution under Seatbelt, not a full MCP
  transport. No adversarial sandbox-escape testing was performed.
- **Language and shim gaps.** 22 JS/TS slots are unsupported outright and most sliced tools
  cannot be executed for lack of adapter shims.
- **Single author, English, small authored sets.** All challenge and probe data are
  first-party; no population-level precision or recall estimate is possible.

## Team handover

[TEAM_HANDOVER.md](TEAM_HANDOVER.md) is the continuation guide: current state, what is
verified, what is unproven, where every artefact lives, and the exact next actions. The
delivered archive `phase3_handover.zip` contains source, tests, data, reports, all 15 figures
and the notebook, with a SHA-256 checksum in `phase3_handover.sha256`.

Citing this work: see [CITATION.cff](CITATION.cff). The original paper must be cited
separately; this repository is a bounded reproduction study, not the paper's artefact.
