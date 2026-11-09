# TRUSTDESC reproduction

[**Open the automatic notebook in Google Colab**](https://colab.research.google.com/github/SamarthRamesha/trustdesc-reproduction/blob/main/TRUSTDESC_REPRODUCTION.ipynb) · [View the notebook](TRUSTDESC_REPRODUCTION.ipynb)

TRUSTDESC generates tool descriptions from implementation evidence to reduce tool poisoning. This repository independently implements the SliceMin → DescGen → DynVer pipeline from [Ye et al., arXiv:2604.07536v1](https://arxiv.org/abs/2604.07536v1). The primary deliverable is the root **TRUSTDESC_REPRODUCTION.ipynb**.

## Run it

1. Open the Colab link above.
2. Select **Runtime → Change runtime type → Python 3 → T4 GPU → Save**.
3. Select **Runtime → Run all**.
4. Read the completion report and download **phase3_handover.zip**, its SHA-256 sidecar, and the individual reports linked in the final cell.

No manual uploads, API keys, configuration edits, terminal commands or review spreadsheets are required. The notebook acquires and validates a fixed project snapshot, installs pinned dependencies, checks hardware, downloads free local model weights and public resources, and writes checkpoints and evidence automatically. Internet access is required. If no compatible GPU is present, it uses a smaller CPU model and records the substitution; CPU execution can be substantially slower. Model/resource failures are diagnosed and independent stages continue without fabricated observations.

## What actually runs

| Stage | Implementation | Important limit |
|---|---|---|
| SliceMin | Import-free Python AST reachability; decorator/explicit/dispatcher registrations; supported cross-file imports, aliases, nested functions and self/cls methods; source spans/hashes | Independent Python subset, not author tree-sitter code; dynamic calls remain unresolved; semantic debloat proposals are preserved but not accepted without equivalence evidence |
| DescGen | Actual pinned local model; comment/docstring removal; 20-character identifier normalization; contextual filtering; description generation; mechanical exact-prose claim records; checked source references and interface | Reconstructed prompts; model attribution and simple signature checks are not proofs of entailment |
| DynVer | Generated verification tasks, real authored-tool execution, separate model judging, supported/refuted/inconclusive decisions, bounded correction and retesting | Default observations are two authored pure fixtures; not external server execution or universal safety certification |
| Evaluation | Same eight authored tasks and **fixed task agent** for original/lite/full; exact trace oracles, per-tool/aggregate metrics, failure analysis and common-success overhead | Fixture oracle success is separate from original human-reviewed paper TSR |
| External MCP backend | Immutable local Docker image, offline stdio JSON-RPC, initialize/list/call, resource/time/output limits, probes and cleanup | Explicitly gated; no pulls, host mounts or credentials; normal Colab lacks Docker; actual container integration remains unvalidated |

On a compatible T4 the free generation/task model is **Qwen2.5-Coder-1.5B-Instruct** at an immutable commit. CPU uses **Qwen2.5-Coder-0.5B-Instruct**, also pinned. These are independent model substitutions, not the paper's four generation models or fixed Gemini-3-Flash task agent. No paid endpoint is configured. Local API charges are zero; compute cost is unknown. Raw prompts, responses, tokens, timings, model asset hashes and environment versions are retained.

**Lite** removes the functionality list from the refined full description. It does not skip SliceMin or DynVer. Unsupported/inconclusive prose is removed; structural schema fields receive limited static checks and are not universally behavior-certified.

## Scientific status

**Phase 2 scientific reproduction remains incomplete.** The original 52 tool identities/revisions, 208 task texts, prompts, reviewed labels, execution traces and exact experimental snapshots have not been recovered/authenticated. A fresh acquisition ledger checks the suggested anonymous artifact, author group and public datasets. MCPTox, MCPSecBench and MCPCorpus are identified as external resources. A pinned arxiv-mcp-server snapshot is analyzed statically. Neither those resources nor our authored fixtures are relabeled as the paper's benchmark.

Published paper values remain reference-only in reports/published_results.csv; local results never substitute for them. Original human-reviewed TSR, adaptive attack success and tool-modification rates remain null without necessary observations. The original Q3–Q5 experiments are explicitly outside the measured fixture run. Model-generation failures, unavailable descriptions and missing observations stay visible; model failure never silently switches to scripted semantic replay.

The notebook finishes with an organized package even when essential evidence is missing. **Pipeline finished** and **Phase 2 complete** are separate states. Read PHASE2_COMPLETION_REPORT.md inside the generated ZIP.

## Outputs

The handover contains all seven requested reports: PHASE2_COMPLETION_REPORT.md, PHASE3_HANDOVER.md, METHODOLOGY.md, DATASET_PROVENANCE.md, EXPERIMENT_RESULTS.md, LIMITATIONS_AND_REPRODUCIBILITY.md and REPRODUCTION_INSTRUCTIONS.md. It also includes experiment/dataset/model/prompt manifests, source hashes, configuration, results JSON/CSVs, original/generated comparisons, slices/reachability, verification plans/decisions/rounds, execution traces, raw model call records, checkpoints, a chart, software checks and artifact integrity validation. Exact project source/configuration/tests are included for continuation. Weights, caches, private PDF, credentials and unrelated files are excluded. Unlicensed external datasets are referenced, not redistributed.

Successful checkpoints are bound to configuration, dataset, source, model, prompts and runtime identity. Rerun unchanged cells in the same VM to reuse completed work and retry failed stages. Changed identities use another run directory. Colab disk is ephemeral: download the ZIP before discarding the VM. The bootstrap checks every runtime module against embedded hashes and a fixed Git revision; it does not run moving main.

## Validation and development

Core software uses Python >=3.11 with the standard library. Inference dependencies are pinned in requirements-colab.txt and torch 2.9.0 is selected automatically by the notebook; full installed versions are exported. This is a direct dependency lock plus per-run resolved environment, not a universal transitive CUDA lock.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -t .
PYTHONPATH=src python3 scripts/validate_reproduction_notebook.py --execute-fixture --output /tmp/trustdesc-validation
```

Delivery validation records distinguish local software tests, real CPU inference and a real Colab T4 session. **No T4 or real-container validation is claimed from local tests.** See docs/VALIDATION_AND_LIMITATIONS.md and reports/reproduction_delivery/ for the actual checks performed.

The earlier notebooks, runs, reports and commits remain intact. docs/HISTORICAL_README_PHASE1.md preserves the previous README. docs/IMPLEMENTATION_AUDIT_2026_11_09.md records the inspected baseline. docs/PAPER_ANALYSIS.md retains the detailed paper reading. Earlier upload/review instructions describe the historical workflow; the root automatic notebook supersedes them. Existing review-based evaluation remains available separately and is not auto-populated with invented human judgments.

LICENSE and NOTICE.md retain the existing project rights and third-party notices. No license or repository visibility change is made by this delivery.
