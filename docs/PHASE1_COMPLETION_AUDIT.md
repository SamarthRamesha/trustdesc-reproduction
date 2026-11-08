# Phase 1 completion audit

Audit date: **8 November 2026**, Asia/Kolkata. Independently inspected actual source, tests, manifests, raw working directories, notebook, reports and Git history; did not rely on the earlier completion summary. **Can we honestly claim to have reproduced TRUSTDESC? No.** We can claim a tested bounded reimplementation with controlled synthetic evidence and one real-source static experiment. Original scientific conditions and model-backed outcomes remain unreproduced.

Publication verified: authenticated GitHub reports a private repository on main, first uploaded 123-file tree matches local Git, original commits are accessible and a fresh GitHub clone passes 92 tests on both Python versions plus notebook/repository checks. [GITHUB_PUBLICATION](GITHUB_PUBLICATION.md) records the verified snapshot and subsequent final-head recheck procedure. Publication does not change the scientific conclusion.

## Inspection scope and preserved baseline

Repository began this audit on clean `master`, without remotes, at `e3de3bcd0084a25fedc03c2429e8b2df3700d48c`. Three original commits: `5f23a49` research/reference evidence, `87c733b` implementation/89-test stage, and `e3de3bc` handover/91-test evidence. All remain ancestors of `main`; `master` remains at the original baseline. No history rewrite or source/evidence deletion was performed.

Baseline inventory: **98 tracked files**, **25 Python source files**, **91 test methods**. It includes seven major code packages, 12 existing docs, a 16-cell notebook, 201 numeric reference rows, source/attack/acquisition manifests, saved fixture outputs and small measurement reports. The 239 KiB initial portable archive identifies `e3de3bc`, not the later audited state. Full file names, byte lengths and SHA-256 values are retained in [baseline inventory](../reports/publication_audit/baseline_inventory.json).

Local ignored data at inspection: `data/raw` 88 files / 1,486,735 bytes; `data/interim` 171 / 2,098,462 bytes; `data/processed` 2 / 3,398 bytes; `experiments/runs` 200 / 1,891,709 bytes. These are working files/source extractions/stage outputs, **not counts of benchmark records**. A `.venv` and the original ZIP/checksum/validation companions are outside tracked research evidence. They are not pushed. The supplied private PDF remains outside the repository. Its 17 pages and SHA-256 were rechecked against the fingerprint; §§4–5/pages 7–13 were compared directly for this audit, with the complete existing analysis inspected.

## A. Methodology: exact implementation and classification

| Stage | Implementation files and entry points | Classification | Reason |
|---|---|---|---|
| SliceMin | `src/trustdesc/slicemin/python.py`: `PythonSlicer.__init__`, `entry`, `resolve`, `_graph`, `slice`; `Function`, `BodyCalls`, `dotted`; `scripts/run_slicemin.py` | **Reimplementation with documented differences; partially implemented** | Real AST reachability for a restricted Python subset; optional model rewrite loop. No TypeScript/tree-sitter or automatic dispatch/LLM-entry fallback; completeness unproven |
| SliceMin model debloating | `PythonSlicer.slice(model=...)`; `descgen/prompts.py:DEBLOAT`; `common/models.py:Model`, `ReplayModel`, `HTTPModel` | **Implemented mechanics, simulated semantic decisions locally** | Each node sees its body/call sites; rewrites checked syntactically, graph recomputed and capped. Only replay tests executed; no LLM semantic-equivalence evidence |
| DescGen | `descgen/sanitize.py`: `StripDocstrings.visit`, `names`, `rename_tokens`, `check_mapping`, `sanitize`; `descgen/generate.py`: `prose_paths`, `validate_description`, `generate`; `scripts/run_descgen.py` | **Reimplementation with documented differences; inference simulated locally** | Actual sanitization/claim coverage; contextual model stage and generator implemented. Prompts reconstructed, classifier/generation replies replayed; truth/schema equivalence unproven |
| DynVer | `dynver/verify.py`: `validate_trace`, `filter_description`, `verify`; `sandbox/runner.py`: `ControlledAgent.run`, `DisabledRunner.run`, `Runner`; `scripts/run_dynver.py` | **Partial reimplementation; simulation of planning/judging; controlled execution** | Actual authored fixture function calls and observed errors; semantic decisions hand-authored. No original MCP/LangChain runtime, iterative repair or real untrusted backend |
| Pipeline | `pipeline.py:run_pipeline`; `cli.py:main`, `get_model`, `model_args`; `fixtures.py:DESCRIPTION`, `replay`, `record` | **Working bounded engineering pipeline** | Saves slice/draft/verification/state/audits, refuses stale directories and preserves completed stages on failure. Does not imply scientific reproduction |

None of the three complete stages is classified as a faithful reproduction. Components can contain both implemented mechanics and simulated semantic steps; calling the entire pipeline “only a mock” would also omit the actual parsing, transformations and controlled function execution.

## B. Scientific fidelity and identified deviations

Primary scientific source: Ye, Zhang, Jia and Hu, *TRUSTDESC: Preventing Tool Poisoning in LLM Applications via Trusted Description Generation*, arXiv:2604.07536v1, 8 April 2026, 17 pages; fingerprint `c0aed54402c07dc9420b908339fddfbed8eb40a2c316910489d0da28426c8cb4`. [PAPER_ANALYSIS](PAPER_ANALYSIS.md) supplies page/section/table detail; this table records the implementation-level gaps found in the audited state.

| Paper requirement / location | Actual implementation / deviation |
|---|---|
| Source-grounded descriptions; threat assumptions (§3.1 p.5) | Three-stage evidence flow preserved. No malware detection or production client-side trust gate; source availability and benign runtime assumptions cannot be certified by our code |
| Python + TypeScript/tree-sitter (§4.1 pp.7–8) | Built-in Python AST only; TypeScript not implemented, class methods/closures/higher-order/dynamic targets unresolved; no arbitrary alias or re-export resolution |
| Entry patterns + LLM fallback (§4.1.1 p.7) | Decorator and some explicit registrations; ambiguity fails. Dispatch and heuristic/LLM fallback absent; reviewed override used on real source. Paper prose is itself ambiguous about dispatcher versus selected callee |
| DFS/caller/callsite graph (§4.1.2) | Ordinary local functions/import aliases traversed; every observed site recorded. Library vs unresolved is not confidently distinguished, so both are labeled external-or-unresolved. Module-level classes/imports/assignments conservatively retained, preventing minimality claims |
| Concrete-context LLM debloating | Optional node-level engine exists, but default mode explicitly static-only. Model rewrites preserve signatures/decorators/return annotations unlike Figure 6's signature simplification; no semantic proof. Iteration cap 3 by default is ours; actual model inference not run |
| Mitigate explicit malicious artifacts (§4.2 pp.8–9) | Prompt treats inputs as untrusted and comments/docstrings are removed. No independent production prompt-injection detector implementing the paper's assumed external defense |
| Identifier normalization/classifier | Real 20-character token normalization; collisions fail. Contextual auxiliary classifier is a reconstructed JSON stage tested with replay. Behavior-bearing strings retained, and renamed attributes/imports may not execute equivalently; no transformed source executes |
| Summary/functionality/schema | Structure implemented with added claim IDs/target coverage. This is an engineering traceability extension; not full JSON-schema validation, source-signature equivalence or truth certification |
| DynVer executable tasks (§4.3 p.9) | Tasks are natural-language agent objectives. Coverage validation and bounded loop exist; local tasks/plans/agent actions are replayed, not generated by real LLMs. Exactly two fixed authored tools are callable |
| LangChain tested tool set/logs | Replaced by own bounded controlled agent; no generic MCP protocol/server lifecycle. Logs are real for fixtures but not authenticated external-runtime traces. No wall-clock killer for arbitrary tools exists; those cannot be loaded |
| Judge/refinement | JSON judge interface exists; verdicts replayed. One-pass filtering, no automatic corrected-argument rewrite or original iterative stopping rule. Added inconclusive state for environment failures. Structural schema fields remain uncertified even when prose is removed |
| Lite mode | Correctly omits only refined functionality list. It does not skip SliceMin/DynVer. Our evidence claim metadata is also omitted from lite's rendered view |
| Source sampling/Table 1 (§5 pp.9–10) | 12 links/counts transcribed. No original sample seed/commits/52-tool list. One current external source acquired; not the original snapshot. Other eleven not downloaded |
| 208 tasks (§5.1) | None obtained. Paper creates four/tool (two original/two generated), excludes tool names and manually judges traces. Our eight synthetic tasks and one five-claim replay scenario are not substitutes |
| Generation models/settings | Paper: Claude-4.5-Sonnet, Gemini-3-Flash, GPT-5.2, gpt-oss-120b; .2 temperature/default reasoning; commercial models via OpenRouter, open model on four RTX PRO 6000 Blackwell GPUs. IDs/versions missing; none run. HTTP interface defaults .2; optional Qwen is a different unrun model |
| Agent configuration | Original task executor is Gemini-3-Flash ReAct across generated-description models. Our default is synthetic replay, not four execution models or a Gemini agent |
| Prompts/dependencies | Exact author prompts and lockfiles unavailable. Ours are inline versioned prompt constants and audited source hashes. Core stdlib/no runtime packages; framework/serving configuration not original |
| Baselines | Original/full/lite condition names are accepted by metric tooling; they were not evaluated on the paper benchmark. 50% degraded-tool selection is a reference, not an implemented trained baseline. StruQ/SecAlign/DataSentinel are discussed related defenses, not reproduced experiments here |
| Metrics | TSR requires reviewed target invocation AND objective achievement; overhead uses common-success original/lite/full tasks. Our ratio-of-means is explicit because aggregation details are missing. Token/cost fields validated, not measured original values; arbitrary description-quality/risk scores are not invented |
| Q3–Q5 variants/attacks | No original degraded implementations, seven-attack regeneration or 15-iteration adaptive loop executed. Table 7 measures trigger-text removal, not proven end-to-end ASR. Exact Figure 7 trajectory not fabricated |
| Results and uncertainty | 201 numeric reference entries and metadata/attack manifests are published-paper values; original-condition measured/difference cells blank. No statistical original reproduction, attack-defense improvement or security guarantee. 4.3% is relative improvement (~3.6 percentage points), not +4.3 points |

Additional unresolved limits: syntactic rewrite checks cannot establish preservation; static file/byte bounds do not fully bound adversarial parser complexity; task planning/judging may share model biases; finite tests cannot exclude conditional behavior; schema descriptions are covered but technical defaults/types/enum values are not behaviorally certified. Metadata names and executable literals remain possible semantic manipulation channels. See LIMITATIONS for the broader critique and printed narrative/table inconsistencies.

## C. Dataset and benchmark audit

| Resource | Source / author release? | Actually obtained / format / counts | Labels/preprocessing/category | Faithful reproduction suitability |
|---|---|---|---|---|
| Original 208 tasks / 52 tools | Paper §5.1; author-constructed benchmark, no authenticated release obtained | **No records**; exact text/IDs/commits absent | Original labels/logs unavailable; no preprocessing possible | Blocked; cannot rerun original TSR |
| `paper_servers.json` | PDF Table 1 hyperlink annotations; not released task data | 12 JSON metadata entries, selected counts sum to 52 | Printed stars/categories/languages; commit/license/selected-tool fields null for original benchmark | Source pool only; not selected implementations |
| `paper_attacks.json` | PDF Table 7 links to Invariant/Chord examples | 7 JSON link/report entries, not seven executed experiments | Five explicit/two implicit, blocked values are **reported**, measured null | Starting source list only |
| `paper_fingerprint.json` | Supplied scientific paper | One metadata/hash object, 17-page fingerprint | Original paper identity; private PDF excluded | Supports version tracing, not benchmark recovery |
| `acquired_sources.json` + ignored archive | Public paper-linked arxiv server, not TRUSTDESC author implementation | One 490,822-byte ZIP at `572e301bb3198962c025d5ed5e14becb86868daa`; Apache-2.0 checked; 31 source Python files analyzed | External snapshot, checksum/license; selective text extraction + AST, no imports/execution; current list has 19 entries | Unknown paper revision; useful static case only |
| `tests/fixtures/tasks.jsonl` | Newly authored project data; **not author-released** | 8 JSONL rows, 2 tools/groups | All labels null; whitespace normalization/dedup; 8 remain, 0 removed; evaluation split | Synthetic engineering checks only |
| `fixtures.py` replay | Newly authored expected responses | One 5-claim scenario, 4 executable tasks, 5 actual fixture calls | Three supported, one refuted, one nonverifiable expected verdict; semantic choices scripted | Simulation, no LLM accuracy measurement |
| Unit-test source/log/metric fixtures | Newly authored in tests | Dynamically constructed cases, not a research corpus | Expected assertions and failure cases; no dataset-size claim | Tests only, not real attack observations |
| Optional Qwen model | Public Qwen model card; not TRUSTDESC benchmark | Config/adapter only; weights **not obtained/run** | Different model; explicit download opt-in, fixed short revision/full resolved config commit at load | Lower-compute exploration only |

`dataset/prepare.py:prepare` validates exact fields, known origins, source/license/version presence, boolean-or-null labels, duplicate IDs/content conflicts and deterministic normalized output hashes. Origin strings/booleans do not authenticate authorship or define a threat taxonomy. Optional seeded server-group splitting is our extension, not a paper split. Current synthetic label semantics are intentionally unused; success labels for TSR are separate explicit human-reviewed booleans. No author labels were fabricated.

## D. Executed experiments and reproducibility

Hardware: user's MacBook Air M3/16GB context; observed `arm64`, macOS 26.6. Saved report metadata records Python/platform; no GPU used. Exact wall times depend on host state. No paid/model inference, external account integration or third-party source execution occurred.

| Executed work | Configuration / inputs / model | Command and outputs | Measured outcome and reproducibility |
|---|---|---|---|
| Synthetic pipeline timing | `configs/experiments.json`, seed 42, 20 repeats, static fixture + `ReplayModel` | `python scripts/run_local_experiments.py`; `local_experiments.json`, `local_example/*`, ignored raw runs | Original median 8.529 ms, min/max 8.344/9.630 ms, peak traced Python 202,061 bytes, 0 API calls/$0 paid. Real safe calls; semantic replay. Decisions/config/data reproducible; time/native memory not equivalent to paper |
| Controlled end-to-end fixture | `DESCRIPTION`/`replay`, fixed `apply_formula` built-in | `PYTHONPATH=src python -m trustdesc demo --output FRESH`; stage JSON | Five claims; false missing-prefix claim refuted from actual error, internal claim removed, others supported on tested cases. Planner/judge truth decisions simulated. No original TSR |
| Synthetic task preparation | 8 authored JSONL rows, default evaluation-only | `prepare_dataset.py ...`; manifest + normalized JSONL | 8 unknown labels preserved, 0 duplicates. Exact hashes/statistics deterministic |
| Public-source static check | Pinned current arxiv archive, reviewed `handle_search` override, no model | `run_public_static.py --archive ...`; `public_static_experiment.json` | 31 Python files, 23 functions, 35 resolved/194 unresolved call sites, 19 exposed list entries; saved wall .153 s. Counts/hash reproducible with source/version; no completeness claim |
| Notebook portable CPU | Baseline source copy, no downloads/GPU/account | `python3 -I -S scripts/validate_notebook.py --execute-portable` | 10 cells compile, 5 portable cells execute, tests/data/demo/timing. Actual Colab/upload/GPU/export unexecuted |
| Original-source validation recheck | Preserved `e3de3bc` copy / two Python versions | `python3 -I -S scripts/run_tests.py`; `/opt/homebrew/bin/python3.11 -I -S scripts/run_tests.py` | 91/91 on both; audit logs added separately |
| Fresh package installation / fix regression | Fresh Python 3.13 venv, setuptools80.9/wheel0.45.1; no runtime deps | `pip install --no-build-isolation --no-deps COPY`; installed `trustdesc demo` from `/private/tmp` | Baseline install succeeds, demo fails due checkout-only fixture. Fix bundles inert source text; reinstalled CLI demo succeeds. Source suite now92 |
| Archive round-trip | Original ZIP / `PORTABLE_MANIFEST.json` | `validate_package.py` and extracted stdlib-only test commands | Original 98 tracked-file hashes verified; initial snapshot/commit consistent. Updated archive checked separately after final audited commit |

Saved original experiment provenance names `87c733b` with dirty tree. Recomputing the exact documented source/config/fixture hash from `e3de3bc` yields **the same** `fd3789bbbf66ca850271202c4ee925798a7c1bc1a851f1ce3a56f6b2b0876ba4`; source content is recoverable despite the earlier Git anchor. Raw repeated runs are ignored; one example is tracked. Audit repeats execute in copies and do not replace historical timing evidence. [Evidence index](../reports/README.md) distinguishes publications from measurements.

Not executed: original descriptions/full/lite benchmark, any of the four original generation models, real contextual LLM classifier, original LangChain/MCP agent, real isolated verification, degraded-tool comparisons, seven-attack prevention runs, adaptive attack optimization, GPU/model downloads/inference. No estimated result is substituted.

## E. Test audit

Actual baseline commands, from a Git-exported `e3de3bc` source copy:

```sh
python3 -I -S scripts/run_tests.py
/opt/homebrew/bin/python3.11 -I -S scripts/run_tests.py
python3 -I -S scripts/validate_notebook.py --execute-portable
```

Baseline: **91 run / 91 pass / 0 failures / 0 errors / 0 skips** on Python 3.13.9 and 3.11.14. `-I -S` excludes user site/PYTHONPATH, demonstrating core standard-library operation with each script's explicit source bootstrap. New regression `tests/integration/test_cli.py:CLITests.test_demo_works_without_checkout_and_fixture_matches` checks package-resource parity and a simulated independent install location. Current suite: **92 run / 92 pass / zero failures/errors/skips** on both versions. Actual wheel-installed CLI demo also succeeds outside the checkout. See `reports/publication_audit/*checks.json` and raw `.txt` logs. The original test runner's `command` field is a fixed recipe; the audit records the **actual command separately** rather than confusing it with interpreter flags.

Coverage: reachable helper chains, aliases/cycles, missing/malformed source, ambiguous entries and rewrite syntax; docstring removal/name collisions/structured response errors/provider gates/timeouts; task coverage, malformed logs, nonverifiability/inconclusive/environment errors, blocked actions and step limits; data provenance/missing labels/dedup; reviewed TSR/intersection overhead; end-to-end/partial/stale output and CLI resources. HTTP transport is mocked; environment/timeout/backend failures are controlled cases. No coverage-percentage tool was run, and no numerical line/branch coverage is claimed. No stress/security proof, TypeScript coverage, actual model quality, arbitrary MCP behavior or original benchmark correctness follows from the test count. Missing features are not counted as skipped tests.

## F. Security and publication audit

Static source is read/AST-parsed only. Rewritten source never runs. `ControlledAgent` invokes only two fixed authored built-ins (`sandbox/fixture_tools.py:invoke`, `apply_formula`, `normalize_name`) and does not accept module paths/callables. Those trusted fixture functions execute on the host. `DisabledRunner` blocks unknown implementations. A backend-name string or trace schema cannot authenticate a future external sandbox.

Subprocesses are used by **trusted project scripts** to run local tests, Git metadata commands, project CLI and optional user-enabled pip/model entry points. Notebook portable validation invokes trusted script subprocesses. They are process boundaries, **not containment against hostile code**. No generic untrusted subprocess runner exists. Venv is dependency separation. Docker/Podman/Colima were absent at initial inspection; `sandbox-exec` presence was not validated/adopted. `docker_review_plan` only returns flags; no container probes/images/VM installation occurred. Actual isolation remains unvalidated and real third-party execution disabled.

Provider calls require explicit construction; remote HTTP additionally requires HTTPS/key/remote+paid gates, with redirects/proxies disabled. Flags do not replace user spending/data-transmission authorization. No keys used in audit. The GPU adapter opts into public download, disables custom remote model code and uses safetensors, but remains unrun and not a security boundary for hostile server code.

Publication checks inspect all intended files plus reachable historical blobs for high-signal GitHub/AWS/service keys, private-key material, credential URLs and literal credential assignments; results are redacted to path/type, never secret values. Manual inventory review found no tracked real credentials, private account configuration, external raw datasets, environments or large generated archives. Largest original tracked file is a ~106KB authored PNG; small reports/fixtures are deliberately retained. Pattern scanning is not a formal no-secrets guarantee. Historical absolute local file paths in a small notebook validation log are harmless provenance, not credentials; existing evidence/history is preserved and published only privately.

`.gitignore` now covers `.env` variants while retaining `.env.example`, venv variants, caches/checkpoints, key/credential file patterns, raw/interim/processed data, repeated runs, ZIP/wheel/archive/log outputs. No restricted/unlicensed external bytes are distributed. Original paper remains external; one acquired public source archive is local ignored data. LICENSE reserves rights; private repository publication does not silently impose an open-source license. Public visibility or broader licensing needs a separate explicit user/rights-holder decision.

## G. Colab audit

Notebook: 16 cells, **10 code cells**, nbformat4.5, no prefilled outputs/execution counts, 5 `portable` tags. Order: Python/disk/GPU inspection; explicit checksum/manual ZIP upload; safe member/hash validation and fresh extraction; path/runtime configuration; tests; synthetic data; demo; 20-run timing; optional GPU packages/model; result export. Dependency files: core stdlib, optional torch2.9.0/transformers4.57.1/huggingface-hub0.36.0/safetensors0.6.2. Direct pins are not a fully resolved CUDA lockfile.

Model: optional Qwen2.5-Coder-1.5B-Instruct, fixed observed revision prefix2e1fd39, full config commit recorded on successful load, FP16/eager attention, seed42, temperature.2, input4096/new2048 caps. No weights acquired/inference executed. A T4 is an exploratory target, not a tested guarantee or original gpt-oss equivalence; GPU/driver/package compatibility and free availability must be checked by the student. Core CPU track requires no GPU or network after project upload. Original paper does not provide precision/peak-memory/serving-stack details sufficient to certify a substitute.

Checkpoint files persist per completed stage and failure state; fresh run directories prevent stale success. Colab disk is ephemeral: user must manually upload the verified archive, select runtime/download opt-in, install/restart if needed, inspect JSON/source/trace grounding, download result ZIPs and restore reviewed checkpoints after disconnect. There is no automatic Drive/account connection. Export excludes model caches/credentials/raw unrelated runtime files; actual browser upload/export has not been validated. `run_local_experiments.py` writes curated report filenames; use a copy/new clone for new evidence, as this audit does. No hidden original dataset acquisition or secure MCP execution exists in notebook cells.

## H. Fresh-environment and archive reproducibility

See [FRESH_ENVIRONMENT_SETUP](FRESH_ENVIRONMENT_SETUP.md) for copy/paste clone/install/test/data/demo commands. Fresh Python3.13 venv + pinned build tools successfully built/installed a wheel. Baseline installed demo failure was reproduced and fixed in `4dd21f46fd108b5483a837f44bd0411ca5ed6418`; package data is byte-identical to the original source fixture and never executed. Source tests work without installed third-party dependencies. `pip check`, console-script behavior, notebook compilation and deterministic task hashes are part of publication validation.

Old archives are historical snapshots, not stale claims of current code. The `e3de3bc` ZIP was verified against its 98-file manifest; audited packaging creates a **separate new ZIP** after the intended state is committed cleanly. It includes tracked code/config/tests/notebook/docs/small evidence and a commit/hash manifest, while excluding Git history, private PDF, raw external source, secrets, models, caches/venv and ignored runs. GitHub carries history; ZIP users get a snapshot. New archive hashes and commit identity are checked against the pushed state; final remote verification confirms private visibility, main branch/head, complete file tree and original ancestry. No release/CI/spending-dependent automation is needed to run these checks.

Reproducibility means matching code/config/data/semantic expectations, not bit-identical timings or ephemeral absolute paths. Model-backed/paper/GPU experiments cannot be reproduced from unavailable inputs by following more setup commands. No critical supported-workflow source is missing; unresolved research resources are explicit.

## I. Final status and decisions requiring the user

| Status | Scope |
|---|---|
| Complete | Bounded source inspection, research/reference documentation, synthetic core workflow, dataset tooling, original91 recheck/current92 tests, package regression fix, CPU notebook validation, fresh install, private-publication preparation and evidence preservation |
| Partially complete | Python SliceMin coverage, DescGen/DynVer semantic implementation validation, input-schema verification, exact DynVer refinement and independent portability beyond tested versions |
| Incomplete | TypeScript/automatic dispatch/fallback, generic MCP/LangChain backend, original full/lite benchmark, Q3–Q5 reproduction, actual GPU run |
| Blocked / external resources | Authenticated original artifact/prompts/task/selected-tool/model details, source snapshot/labels and appropriate original-model infrastructure |
| Requires approval | Paid/API inference/private-source transmission, installing/using a real hostile-code execution environment, author-contact messages, public visibility or an open-source license change |
| Authorized in this task | A **new private** repository under authenticated SamarthRamesha, preserving history and publishing audited project files. Exact-name collision was checked through authenticated CLI/API; existing repositories must never be repurposed |

No, we cannot honestly claim a complete TRUSTDESC reproduction. The defensible claim is a working bounded reimplementation, explicit scientific gaps, actual controlled execution/static evidence, and an independently inspectable private research repository. [NEXT_STEPS](NEXT_STEPS.md) gives the dependency-ordered path to genuine original-condition evaluation; [PROJECT_HANDOVER](PROJECT_HANDOVER.md) is the central continuation document.
