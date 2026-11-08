# Capstone review preparation

## A concise opening explanation

Our capstone studies whether combining semantic and behavioral verification can improve trust decisions for third-party AI tools. My Phase 1 responsibility is the TRUSTDESC baseline. It replaces potentially misleading descriptions with descriptions inferred from source, then checks behavioral claims using execution. I read the complete paper, traced its evaluation sources, built a bounded modular reimplementation and validated the local engineering workflow. Exact original artifacts and model experiments remain missing, so I distinguish implementation progress from successful scientific reproduction.

## Questions faculty may ask

**What vulnerability does TRUSTDESC address?** An agent sees what a tool claims to do and may choose it based on that claim. Explicit poisoning inserts commands into descriptions; implicit poisoning exaggerates capability or quality to bias selection. TRUSTDESC tries to align descriptions with code rather than merely detecting suspicious words.

**Why select this paper?** It directly links source-grounded semantics and observed behavior, making it a useful baseline for our hybrid capstone. It gives three identifiable components and concrete downstream evaluation measures. It also exposes assumptions our broader defense must revisit.

**Does TRUSTDESC prove a tool is safe?** No. The paper assumes no overtly malicious runtime code and accessible source. Finite verification tasks cannot rule out hidden conditional behavior. Our output explicitly says trust is not assessed; a future policy/security layer must consume the evidence.

**How does SliceMin work?** Identify the exposed entry, traverse locally reachable functions while recording callers and call sites, then ask an LLM to remove code unreachable under those contexts and rebuild the graph. Our parser is Python AST rather than tree-sitter, with documented scope limits. Static-only mode does not claim debloating.

**Why isn't retrieving functions by keyword enough?** A keyword cannot establish whether a helper is reachable or whether an optional feature is available through this entry. The paper's example never passes an optional year/style argument, so the helper's full capability must not be advertised by the tool.

**Do your slices always include all relevant code?** No. We resolve ordinary top-level functions and imports but report unresolved calls and unsupported methods/closures/dynamic patterns. The pinned real-source experiment has 194 unresolved call sites. That is evidence of a limitation, not something to hide behind a claim of completeness.

**How do you handle code-based prompt injection?** Strip comments/docstrings, normalize names to 20 characters, and call a contextual semantic identifier filter before description generation. Preserve behavior-bearing strings, which remain an untrusted channel. Reject name collisions. Prompts and model responses are audited; structural validation does not establish semantic truth.

**What does DescGen output?** A concise summary, supported functionality list and input schema. We add explicit claim IDs/paths for traceability. The exact author prompts were unavailable, so ours are reconstructed and versioned.

**What does DynVer actually verify?** A planner makes one task per claim or marks it nonverifiable. An agent calls tools and records observations; a judging step assesses support/refutation. We retain supported prose and explain the other outcomes. Our local semantic stages are replayed; the fixed fixture function executions themselves are real.

**Why distinguish inconclusive from false?** A missing dependency or disabled sandbox cannot refute a tool's functionality. It means we lack evidence. Our conservative supported output omits such claims but preserves an inconclusive decision for explanation.

**What is full versus lite?** Full keeps summary, functionalities and schema after refinement. Lite omits the functionality list only. It still follows verification; it is not a cheaper unverified pipeline.

**What dataset did you use?** Eight newly authored synthetic tasks for engineering validation, plus one pinned public source snapshot for static analysis only. The original benchmark's exact 52 selected tools and 208 task records were not recovered. Twelve source links are not the benchmark. No missing labels were invented.

**What was the real-source result?** We acquired the paper-linked arxiv server at commit `572e301bb3198962c025d5ed5e14becb86868daa`, recorded its archive checksum/license, parsed 31 Python files and traversed 23 functions from a reviewed search-handler entry. The current source exposes 19 tool-list entries, showing why a current checkout cannot silently substitute for the paper's unknown revision. No third-party code ran.

**What tests passed?** The saved reports show 91 tests with zero failures/errors/skips on Python 3.13.9 and Python 3.11. Cases include call cycles/import aliases/ambiguity, malformed LLM responses, unsupported claims, provider timeouts, missing dependencies, malformed traces, blocked tool requests, data provenance and partial pipeline failure. Five portable notebook cells also ran locally.

**What experimental results can you defend?** Actual fixture call traces, expected claim filtering, eight valid synthetic records, repeated local engineering timings/allocations, and static source coverage/drift observations. We cannot defend a reproduced 87.7% TSR, a model generation price, or an attack-defense improvement. Published versus measured values are separated.

**What does the paper's 4.3% improvement mean?** Relative improvement from 175 to 182.5 average successful tasks, roughly 3.6 percentage points in TSR. It is not +4.3 percentage points. 182.5 is a four-model average, not a fractional success in a single run.

**Why didn't you execute real MCP servers?** Unknown implementations are untrusted. There was no validated container/VM boundary. A Python subprocess/venv/timeout is insufficient. Our controlled runner accepts only two authored built-ins and cannot import arbitrary code. Static analysis of downloaded text does not execute it.

**What is the Colab package for?** CPU cells reproduce engineering checks. Optional GPU cells try a small public model with recorded version/settings and strict output handling. They are not original-model equivalents and were not run locally. Original gpt-oss-120b used four RTX PRO 6000 Blackwell GPUs, so a free T4 cannot be assumed equivalent.

**How will team integration work?** Security contributes reviewed threat cases/source evidence; data contributes pinned licensed artifacts/tasks/manifests; XAI consumes claim-level reasons/traces. Our code provides evidence interfaces, not an arbitrary hybrid score. The final trust policy and production gateway are later team work.

**What should happen next?** Recover authenticated author artifacts, obtain exact snapshots/tasks/prompts and model IDs, implement/validate isolated MCP execution, then run reviewed original/full/lite evaluations. After that, test extensions such as conditional-behavior tasks and explanation policies against a model-backed baseline. No improvement claim comes before evidence.
