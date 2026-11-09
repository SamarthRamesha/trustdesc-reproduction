# Limitations and reproducibility

- Original 52-tool/208-task release, labels, traces and exact prompts not recovered.
- Original generation models and fixed Gemini-3-Flash task agent replaced by explicitly named free local model.
- Python AST subset; TypeScript, unrestricted dynamic dispatch and proof of slicing equivalence unavailable.
- Full external MCP transport is gated by a validated immutable-image backend; the separate macOS boundary supports offline Python source observations only.
- Finite authored fixture observations and automated oracles do not establish original human-reviewed TSR.
- Q3 degraded-tool competition, Q4 seven original attacks and Q5 adaptive naming experiments lack authenticated experimental artifacts.

## Honest execution status

Actual execution environment, hardware, dependencies and code hashes are in environment.json, installed_packages.txt and EXPERIMENT_MANIFEST.json. Read the delivery validation evidence for which tests actually ran on the developer host. No real Colab T4 execution is claimed unless a future run manifest records it. A CPU path uses a smaller model and records that substitution; it may be slow or fail structured-generation checks. A local-model download or inference failure does not become a scripted response. Baseline fixture evaluation can proceed independently of failed DescGen/DynVer stages.

## Reproducibility scope

Fixed immutable source/model revisions, resource SHA-256, seeds, per-request prompts/raw outputs and hash-bound checkpoints make identity auditable. CUDA/PyTorch sampling is not guaranteed bit-identical across hardware/versions. Direct dependencies are pinned; the installed full transitive environment is captured, not claimed to be a universal cross-platform lock. Cache files are integrity checked; partial/corrupt resource files are quarantined and acquired again. Output exports use a registered-file allowlist and secret-pattern checks. Model weights, private PDF, user files and external caches are excluded.

The threat model assumes accessible source and no overtly malicious runtime implementation. Finite tests do not certify safety, absence of malicious code, or universal semantic equivalence. Containers share the host kernel and are not a VM. Current container integration and T4 inference require validation on their actual infrastructure. Ordinary fixture execution is never described as an untrusted-code sandbox.
