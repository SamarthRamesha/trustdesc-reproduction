# Phase 3 handover

Start with PHASE2_COMPLETION_REPORT.md and validation_report.json. The experiment fingerprint is `1f199a7054d887162fbe7487fc9e0fdafb3b8185463eed302d6c8f6e42df2f32`. Original Phase 2 scientific completion is blocked by the evidence below; Phase 3 must not assume it is complete.

- Original 52-tool/208-task release, labels, traces and exact prompts not recovered.
- Original generation models and fixed Gemini-3-Flash task agent replaced by explicitly named free local model.
- Python AST subset; TypeScript, unrestricted dynamic dispatch and proof of slicing equivalence unavailable.
- Full external MCP transport is gated by a validated immutable-image backend; the separate macOS boundary supports offline Python source observations only.
- Finite authored fixture observations and automated oracles do not establish original human-reviewed TSR.
- Q3 degraded-tool competition, Q4 seven original attacks and Q5 adaptive naming experiments lack authenticated experimental artifacts.

## Package inventory

- results.json, metrics.csv and task_results.csv: measured or missing observations with explicit scope.
- dataset_manifest.json, acquisition_report.json, source_hashes.json: dataset/source identity, licenses and acquisition errors.
- model_manifest.json, prompt_manifest.json, config.json, environment.json, installed_packages.txt: model/settings/prompts/runtime.
- slices/, static_results.json, description_results.json and tool_verification.json: source reachability, drafts, tasks, decisions and refinement history.
- execution_traces.jsonl, calls/, checkpoints/: actual events, raw model outputs, errors and recoverable stage records.
- reproduction_source/: exact project source/configuration needed to rerun; no model weights or external caches.
- artifact_hashes.json: complete member hashes; the outer archive also has an independent .sha256 sidecar.

## Resume and extend

Rerun the unchanged notebook in the same runtime to reuse successful hash-bound checkpoints and retry failed stages. New source/model/runtime settings create a separate run. Local checkpoints persist under the notebook workspace. Optional Colab disk is ephemeral; download its ZIP before discarding the VM. Restore with trustdesc.experiments.export.restore_results(archive, expected_sha256, destination) to inspect the run evidence.

Recover and authenticate original tool/task/prompt/label/trace artifacts before original-benchmark evaluation. Verify rights and license before redistribution. Supply a reviewed immutable container image/source attestation on a Linux Docker host, validate probes and actual integration, then enable the external adapter. Unknown source must never execute outside a validated isolation boundary. Keep the task agent fixed while comparing generator models. Perform original human trace review separately from the fixture oracle. Record exact mutations/tasks for Q3–Q5 before computing attack or selection rates.
