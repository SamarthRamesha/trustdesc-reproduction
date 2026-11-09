# Final project completion report

Updated 2026-11-09 16:18 IST.

**Engineering delivery: working Apple Silicon pipeline, validated local notebook and evidence handover. Original Phase 2 scientific reproduction: INCOMPLETE.**

Repository: https://github.com/SamarthRamesha/trustdesc-reproduction . Algorithm implementation commit: `4a3239bfc85b48c3167cfce623169e750a0227ff`. Existing history and branch `main` are preserved; no force push, license change or repository-visibility change is used. The delivery agent verifies publication separately and provides a receipt alongside the archive.

## What was actually executed

The primary notebook ran in an actual Jupyter kernel using a fresh Python 3.11 environment installed from the pinned Apple dependency lock. All five primary code cells executed, plus one validation workspace-setting cell. Cached model assets were independently rehashed before loading. No scripted semantic model replaced real inference.

Final main run: `automatic-93589e7e9672adf4a537`. Experiment fingerprint: `1f199a7054d887162fbe7487fc9e0fdafb3b8185463eed302d6c8f6e42df2f32`.

Hardware: Apple M3, 16 GiB unified memory. Model: `mlx-community/Qwen3-4B-Instruct-2507-4bit`, immutable revision `50d427756c6b1b2fe0c0a10f67fbda1fc8e82c1b`, MLX 0.32.4 / MLX-LM 0.28.3. The model passed arithmetic, structured-JSON and exact-action qualification. A single resident model was reused across roles; the public supplement loaded the same model only after the main worker exited. Observed main worker peak RSS: 1.99 GiB; peak recorded MLX allocation: 3.01 GiB. These are different memory views, not additive totals or guarantees for arbitrary source sizes.

### Matched authored-fixture observations

| Condition | Observed attempts | Exact tool objectives | Agent completed | Fixture oracle rate |
|---|---|---|---|---|
| original | 8/8 | 6/8 | 7/8 | 75.0% |
| lite | 8/8 | 6/8 | 6/8 | 75.0% |
| full | 8/8 | 6/8 | 3/8 | 75.0% |

These eight authored tasks and two pure authored tools are not the original 208 tasks or 52 tools. The oracle checks requested call arguments and observed results/errors. It can record an achieved tool objective even when the agent fails to finish its response; completion counts are shown separately. It can also reject a semantically equivalent plan that changes the requested literal arguments. These are not human-reviewed paper TSR values. No effectiveness or improvement conclusion is drawn from the small fixture set.

### Separate public example observations

The pinned MIT MCP Python SDK `add` example is a public external example, not an authenticated paper-selected tool. Only its unchanged function signature/body is executed after removing its registration decorator. Execution is offline under validated macOS Seatbelt; it is not a full MCP server or HTTP transport.

| Condition | Observed / expected | Exact source-body objectives | Rate |
|---|---|---|---|
| original | 4/4 | 4 | 100.0% |
| lite | 4/4 | 4 | 100.0% |
| full | 4/4 | 4 | 100.0% |

These four independently authored arithmetic cases are reported separately and are not pooled with the main fixtures. The same task-agent model, revision and settings are held fixed within each three-condition study.

## Implementation delivered

- SliceMin: import-free Python registration detection, cross-file reachability/aliases, supported nested and self/cls methods, dispatcher patterns, dependency context, source spans/hashes and unresolved-call reports. Unrelated module startup/metadata is excluded with recorded omissions. LLM debloat proposals remain unproven reasoning artifacts and are not deployed as rewritten tools.
- DescGen: actual local generation and contextual identifier filtering; comment/docstring removal and collision-checked 20-character normalization; source attribution and static argument/required/simple-type checks; return, exception, mutation and possible-side-effect syntax evidence. Model-generated claim text is retained; bookkeeping and collection-container repairs add no semantic claims.
- DynVer: actual model plans, actual calls and traces, supported/refuted/inconclusive judgments, bounded correction/retesting and claim removal. Actual exception types and structured final answers are retained. Judging receives recorded tool observations without agent-written final prose.
- Models: native MLX 4-bit loading with immutable asset verification, Python startup gates, worker wall/RSS supervision, explicit unload/termination, raw prompts/responses and failure tracebacks. MPS/CPU support exists in the PyTorch adapter; those alternative model/device paths were not requalified in this delivery after the user requested one-model validation.
- Reproduction: self-contained primary notebook, fresh local environment installation, pinned direct and resolved Apple dependencies, acquisition utilities, matched evaluation, hash-bound checkpoints, metrics, graphs, reports and member-verified exports. The handover source rebuilds the primary notebook byte-for-byte in a separately labeled software-only closure check.

## Validation and debugging evidence

- 156 software unit/integration tests pass in the actual notebook run. Software fixtures are explicitly labeled and never counted as research observations.
- Native Terminal and Codex each passed 23 Python-only startup checks; all four outside-read/write/network/process-denial canaries passed in both contexts.
- The pre-main Python abort was caused by the project Seatbelt policy denying `file-read-data /`. A literal root-directory exception and canonical framework executable fixed startup without recursive private-file access. Homebrew installations, SIP and system dyld caches were not modified. See `PYTHON_STARTUP_INVESTIGATION.md` and the saved kernel denial excerpts.
- The missing `.jinja` chat-template asset, bare evidence-array container, structured final-answer rejection and inappropriate agent-prose judge input were diagnosed, repaired and regression-tested. All raw failures and prior runs remain available.
- The first native main run achieved 6/8 exact objectives in each condition. A subsequent run exposed a controller format defect and missing main-condition observations; its public example completed 4/4 in each condition. Runs used for repair and fresh-environment validation are not pooled as independent samples.
- The original CPU and T4 archives were CRC/hash-checked and preserved. The T4 archive records an initial CUDA device-side assertion and repeated use of the failed context. Its underlying first GPU cause cannot be established without missing synchronous traceback/kernel diagnostics and suitable CUDA hardware. Added guards are not represented as a reproduced GPU fix.
- The original reference CSV's CRLF bytes are retained. Its canonical LF copy has identical parsed rows and allows deterministic text-handover notebook reconstruction; this changes no model/experiment algorithm or observation.

## Completion status and remaining limits

| Deliverable | Status | Limit |
|---|---|---|
| Apple Silicon execution | Executed and validated | Observed local workload only |
| Python pipeline and matched available conditions | Executed with provenance | Finite authored fixtures and a separate public example |
| Main notebook and fresh environment | Actual Jupyter execution validated | Public package/model downloads still require network |
| Phase 2 original quantitative reproduction | INCOMPLETE | Original authenticated resources and original models/settings unavailable |
| Phase 3 engineering handover | Produced and integrity-checked | Does not certify Phase 2 scientific completion |

The suggested original artifact API returned HTTP 401 in fresh acquisition. Original 52-tool identities/revisions, 208 task texts, prompts, reviewed labels and traces remain unrecovered. Public MCPTox/MCPSecBench/MCPCorpus references are separate resources. Original paper TSR, attack-success and tool-modification results remain null; Q3–Q5 original experiments are not claimed complete. Published values are reference-only.

The larger pinned arXiv source remains a static reference outside the active task benchmark. Preserved attempts showed the local classifier producing long neutral-name maps and reaching output limits. Its generation was not marked successful or replaced with scripted descriptions. The public example provides the separate measured external source-body alternative.

TypeScript, unrestricted dynamic resolution, proof of slicing equivalence, a validated full external MCP transport and the paper's original task agent are not reproduced. Exact-source attribution and finite LLM judgments do not prove semantic entailment, universal correctness or malware safety. JSON-schema checks cover exposed names, required flags and simple types; they do not fully certify generated schema metadata/nested constraints. Model judge mistakes and rejected refinement candidates remain visible. No original human-review labels were invented.

Local API charges are zero; compute/electricity cost is unknown. No paid API, subscription, private paper upload or private credential upload was used. Model weights/caches, credentials and unrelated personal files are excluded from the handover.

## Reproduce and inspect

Open `TRUSTDESC_REPRODUCTION.ipynb` in local Jupyter and choose Run All. No manual uploads or cell edits are required. The notebook verifies embedded source, installs the local environment, tests Python, qualifies the real model, executes and reports the available studies, and emits a handover with checksums. Successful unchanged checkpoints are reused; changed identities create separate runs. Optional historical Colab notebooks remain in the repository.

Read `PHASE2_COMPLETION_REPORT.md`, `PHASE3_HANDOVER.md`, `DATASET_PROVENANCE.md`, `METHODOLOGY.md`, the per-run manifests, raw calls and traces. `RUN_COMPLETION_REPORT.md` preserves the notebook-generated per-run report; this document adds the delivery-wide audit. The archive includes prior evidence and exact source snapshots. Its SHA-256 is in `phase3_handover.zip.sha256`; all member hashes are verified before delivery.
