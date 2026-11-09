# Implementation audit before the automatic notebook build

Baseline: `e7270af`, main, clean checkout cloned from the user-specified public GitHub remote. No local user edits existed. All historical reports and notebooks are preserved. Repository inventory includes 37 source modules, unit/integration tests, two Colab notebooks, configurations, paper manifests and previous execution/publication evidence.

| Component | Verified baseline | Work for this delivery |
|---|---|---|
| SliceMin | Import-free Python AST traversal; imports, basic aliases, decorator/explicit registrations; no dispatcher, nested or method resolution. Optional unproven model rewrites. | Extend conservative resolver and source evidence. Reject uncertain semantic rewrites; retain limitations. |
| DescGen | Real model interface, stripping, 20-character truncation, contextual identifier classification, exact prose/claim coverage. No claim-to-source evidence or schema consistency gate. | Evidence references, implementation interface validation, logged bounded repair. |
| DynVer | Executable authored tools, model task/judge interfaces; one pass and claim deletion; external execution disabled. | Iterative corrections that must be retested, isolated MCP backend, explicit confidence. |
| Models | Replay default; optional CUDA-only 1.5B Qwen; paid models explicitly gated. | Automatic free pinned local model selection; CPU compatible smaller model; failures never become replay evidence. |
| Evaluation | Original/full/lite and review gate; execution model varies with generation configuration. | Fixed task agent; automatic fixture oracles clearly separated from paper human-reviewed TSR. |
| Notebook | Upload/archive/configuration/review steps; nested path; optional inference. | Root notebook, automatic integrity-checked source bootstrap, ordered Run all, complete output package. |
| Data | Original 52 tools/208 tasks not recovered; one pinned public source inspected statically; eight authored tasks. | Fresh acquisition ledger and pinned external benchmark references; no invented original tasks/labels. |
| Isolation | Disabled backend plus review-only Docker command. | Executable bounded container MCP transport; fail closed when Docker/isolation probes unavailable. No unknown tool execution on the Mac. |

The supplied PDF has 17 pages; SHA-256 and original analysis are retained in the existing paper fingerprint manifest. Reading confirms lite removes only the functionality list after refinement, and task execution is fixed to Gemini-3-Flash while generation models vary (§5). The new free-model experiment differs from this setting. Exact prompts, original tool/task IDs, labels, traces, configurations and artifact authenticity remain unavailable. Phase 2 cannot be certified complete without that evidence. Passing software tests is not research completion.
