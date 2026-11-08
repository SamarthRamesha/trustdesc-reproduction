# Colab handover — final MacBook preparation complete

Open **[TRUSTDESC_FULL_REPRODUCTION.ipynb](../notebooks/colab/TRUSTDESC_FULL_REPRODUCTION.ipynb)**. It is the single primary Part 2 entry point. Use the final **TRUSTDESC_COLAB_READY.zip** plus its own SHA-256 companion, or clone the private repository's validated `main`. The older notebook/archive remain historical evidence and should not be substituted when resuming a new-workflow run.

Follow notebook sections **1–16 in order**. The complete standalone operator reference is [COLAB_EXPERIMENT_GUIDE](COLAB_EXPERIMENT_GUIDE.md); no further MacBook preparation prompt is needed.

## Runtime and credentials

| Profile | Select | Executable work | Credentials / limits |
|---|---|---|---|
| A | CPU | Tests, eight synthetic tasks/two tools, SliceMin, full fixture/replay pipeline, 24 original/lite/full records, review, metrics, plots/export | None with project ZIP upload; no paid API/model inference |
| B | T4 or compatible CUDA GPU | Explicitly add `qwen-small`, enable public downloads, then real controlled model-backed stages | Public Qwen 1.5B; conservative 8 GiB free GPU/host RAM gates; not an original paper model |
| C | High-memory GPU and RAM | Explicitly select `qwen-large` 7B or another configured capacity-appropriate option | 7B gate: 24 GiB GPU/20 GiB host RAM; estimates, not validated guarantees; no silent fallback |
| D | Explicit original display-name endpoint configuration | Claude-4.5-Sonnet, Gemini-3-Flash, GPT-5.2, gpt-oss-120b interfaces; actual configured source/fixture analysis | Exact IDs/endpoint/access supplied by operator; paper .2/default reasoning preserved. Original gpt-oss used four RTX PRO 6000 Blackwell GPUs; single Colab GPU equivalence not claimed |

Capacity is inspected automatically, but models never change silently. Default selected model is **replay**, with no inference. Actual GPU/CUDA package installation, real Colab GUI operations and live model inference were not validated on the Mac. Failures/unavailable configurations are recorded while other feasible work continues.

Private Git clone optionally needs a read-only GitHub token (`TRUSTDESC_GITHUB_TOKEN` Colab Secret/hidden input). ZIP upload needs no credential. Remote potentially paid models use `TRUSTDESC_API_KEY`, explicit exact-configuration typed confirmation and persistent request caps. The confirmation shows selected tools/data transmission and estimates only when verified rates exist. Keys never go in configuration, logs or exports. Public local model downloads require a separate opt-in. No Drive mount, ChatGPT-account connection or personal file upload is necessary.

## Exact execution order

1. Inspect Python/RAM/disk/GPU/CUDA/runtime.
2. Upload/checksum-verify the prepared project ZIP, or authenticate/clone private main.
3. Optionally restore your own previous result ZIP/checksum to a fresh folder.
4. Edit the **one central settings cell**: models, profile, IDs/endpoints, caps, data choice and optional flags.
5. Install selected dependencies, inspect actual versions and run software tests without overwriting historical reports.
6. Acquire/validate synthetic or supplied resources and prepare source text; the pinned public arxiv snapshot is optional/static-only.
7. For selected HTTP models only, inspect transmission/cost scope and explicitly confirm each exact configuration; supply key securely.
8. Create a unique run, or choose/confirm a detected compatible resume. Changed source/data/code/model/config/runtime rejects reuse.
9. Run actual SliceMin; retain slices, call graph/warnings and unresolved sites. Unvalidated TypeScript is unavailable.
10. Run actual DescGen. Live models do real inference; replay is labeled. Save inputs/prompts/sanitization/raw safe responses/schema/validation/failures. Optional real-model debloating is configured centrally.
11. Run actual DynVer planning/judging and controlled fixture execution. Unknown MCP source remains disabled; Colab is not a sandbox.
12. Run all available original/lite/full task conditions with their actual condition descriptions; save predictions/traces/latency/tokens/actual cost/errors/checkpoints.
13. **Perform human review** of task/target invocation/objective evidence using the UI or matching CSV template. Do not use model self-assessment. Missing reviews remain missing.
14. Generate measured tables/plots and report. TSR requires both target invocation and objective achievement with complete eligible condition coverage. Overhead uses three-way successful-task overlap. Missing values are never plotted as zero.
15. Run final export: it refreshes analysis and downloads **TRUSTDESC_COLAB_RESULTS.zip** and **.sha256**.
16. Stop preparation. Send those result files and repository URL to Codex for Part 3, without Google account/session access.

## Resources and truthful limits

The final bounded recovery sweep did not obtain an authenticated author implementation, exact 52 tools/revisions, 208 tasks, prompts or labels; see evidence ledger and `reports/colab_preparation/final_resource_discovery.json`. Do not manufacture them. The new workflow includes eight synthetic tasks, optional current paper-linked source and explicitly reconstructed model-generated tasks. Provenance/source/config/dataset/code/prompt hashes and model identifiers are exported.

A supplied genuine benchmark can activate the implemented bundle contract in `configs/original_benchmark_contract.json`, with provenance and actual 52/208 records. It never changes arbitrary external code to a host-executable backend. Original LangChain/MCP execution, exact author/model conditions and isolation remain unavoidable external limitations, not hidden notebook TODOs. This notebook's filename or successful CPU run does not establish full scientific reproduction.

## Checkpointing and result handover

Per-stage/tool/task state and immutable attempt results use configuration/data/source/model/prompt/code/runtime binding and checksums. Completed compatible work is reused without new model calls. Interrupted work is not complete. Explicit failures are preserved unless retried. Export before a Colab session disappears; local storage is ephemeral. An in-flight API request may already be billed and an incomplete stage may repeat calls after explicit resume—no exactly-once billing guarantee is made.

Results include all required JSON/CSV/Markdown reports, raw safe request/response/trace records, intermediate slices/descriptions/verification, human review evidence, metrics/plots/errors, manifests/hashes and reproduction gaps. Only registered writer outputs are exported; API credentials, model caches, unrelated/personal runtime files and environments are excluded. A SHA-256 member manifest makes the export independently inspectable for Part 3.

Local validation evidence is under `reports/colab_preparation/`; current tests cover checkpoint/resume, partial failures, invalid-provider continuation, evidence-bound reviews, condition differences, export whitelist/redaction/checksums and restore. CPU notebook execution leaves success metrics unreviewed, as no human experiment annotation was performed during validation.
