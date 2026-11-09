# Recovery and engineering audit

Baseline: `b7a8c8bd15e57254f0bd92bd43d87723535ee9d4`, clean checkout cloned without hardlinks. Existing history, reports, notebooks and archives were retained. The original workspace and Desktop archives were read, not modified. The paper's 17-page PDF matches the repository fingerprint `c0aed54402c07dc9420b908339fddfbed8eb40a2c316910489d0da28426c8cb4`.

## Historical evidence recovered

Three archives were CRC-checked, SHA-256-indexed and inspected. Details are in `reports/apple_recovery/historical_archives.json` and `t4_archive_inventory.json`.

| Evidence | What it actually establishes |
|---|---|
| Previous CPU delivery / real CPU pipeline ZIP | Real Transformers inference was attempted. Eight Original attempts have observable failures and 0/8 exact authored objectives; lite/full observations are unavailable. This is distinct from “nothing executed.” |
| Desktop T4 handover ZIP | Tesla T4, PyTorch 2.9.0+cu126, Qwen2.5-Coder-1.5B fp16 assets loaded. First saved debloat call failed with a CUDA device-side assertion; subsequent calls reused the failed context. All 24 task-condition observations are unavailable. |
| Baseline software suite | 144 tests pass. Scripted software models/replay fixtures validate orchestration only; they are not real DescGen or research labels. |
| Published-value tables | Paper reference values, not local measured results. |

The T4 records do not contain a full synchronous GPU traceback, failing kernel diagnostics, token-bound checks or pre-sampling numeric checks. A specific underlying CUDA cause cannot be established from those records or reproduced on a Mac without CUDA. Later failures are consistent with reuse of an invalid context, but do not identify the first failing operation. No claim is made that Apple startup failures share that cause. The adapter now records complete tracebacks, validates input-token bounds, checks logits before sampling, and refuses reuse after a device-side assertion. These are safeguards, not proof that the original GPU defect was reproduced or solved.

## Component audit and work performed

| Component | Recovered state | Current engineering scope |
|---|---|---|
| Environment | CPU/CUDA only; root notebook chose a Linux CPU wheel index on Mac | Native MLX quantization, explicit MPS/CPU adapters, memory preflight, worker RSS/wall supervision, unload and Python startup gates |
| SliceMin | Restricted Python AST reachability and provenance; unrelated module startup retained as context | Referenced-global closure now removes unrelated transport startup/metadata from the reasoning slice; omissions are recorded. Cross-file aliases/nested/self/cls/dispatcher handling retained. No executable equivalence or unrestricted TypeScript/dynamic resolution claim. |
| DescGen | Actual model interfaces plus separate scripted software validation; real CPU quality poor | Qualified local model; real generation/identifier filtering/source attribution; schema validation; return/exception/mutation/possible-side-effect syntax records. Analysis caveats stay outside the semantic generation payload. |
| DynVer | Agent/planner/judge/filter/refinement implementation with finite fixture execution | Actual model-generated plans, actual tool calls and judged observations; exception types now preserved. Unsupported/inconclusive claims remain excluded. Judge reasoning remains fallible and is preserved for inspection. |
| Isolation | Gated Docker adapter; unavailable on this Mac | Separate macOS Seatbelt offline Python boundary, with startup and outside-read/write/network/process denial probes. It is not a full MCP transport or a VM. |
| Notebook | Root Run-all notebook targeted Colab | Self-contained embedded-source local notebook, fresh venv installation, pinned Apple lock, actual Jupyter execution validation, sequential model use, reports and handover |
| Evaluation | Eight authored tasks, two tools, fixed task-agent design | Actual Original/lite/full observations, exact trace oracles, explicit failures/missing denominators and separate public-example source-body study |

## Native startup and model repair evidence

The 13:54:32 dyld/libignition abort arose in print-only Seatbelt probes. Kernel logs identify denied `file-read-data /`; a literal root-directory permission fixes startup while descendant access stays denied. Native Terminal and Codex each pass 23 startup checks and all isolation canaries. No Homebrew, SIP or system-cache changes were made. See `PYTHON_STARTUP_INVESTIGATION.md`.

The 3B candidate's failed structure/action checks are preserved; it was not accepted merely because its download worked. The single 4B candidate initially lacked its separately stored chat template because `.jinja` assets were omitted. The allowlist/hash validation was repaired and regression-tested. Subsequent structured-output/action protocol failures were retained and fixed by making the requests unambiguous. Qwen3-4B then passed arithmetic, structured JSON and exact whitespace-preserving actions in one monitored process. No further model comparison was performed after the user's instruction.

The first native main run (`automatic-bfb7f182699c8cdf5b15`) generated real descriptions for both authored tools, ran DynVer and all 24 matched attempts: each condition achieved 6/8 exact authored objectives. It demonstrated no improvement. An 8192-token cap blocked the larger public arXiv source; the failed record was retained. The supported cap was raised for subsequent validation within the same monitored model's resource bounds, without silent truncation.

The initial public SDK function-body study completed 4/4 Original observations. Lite/full were unavailable because its summary was not supported; those are missing observations, not a 0% measured success rate. Inspection exposed irrelevant server transport context and misleading judge reasoning. That evidence motivated the SliceMin/context repairs rather than relabeling a failed study as successful. Later runs are reported separately; repetitions for software repair/fresh-environment validation are never pooled as independent samples.

## Scientific status

Original tool/task membership, source snapshots, prompts, labels, traces and original model settings remain unauthenticated/unavailable. A fresh acquisition probe returned HTTP 401 from the suggested artifact API, found no TRUSTDESC repository in the inspected author-group listing, and recorded public external benchmark resources separately. External datasets are not relabeled as the original benchmark. Original human-reviewed TSR, original attack success and Q3–Q5 results remain unavailable.

The final completion report and run manifests state the delivered validation results and remaining limitations. A working notebook and valid handover establish engineering progress, not completion of the paper's quantitative reproduction.
