> **Current entry point (2026-11-09):** [root automatic notebook](../TRUSTDESC_REPRODUCTION.ipynb) supersedes the historical upload/configuration workflow below. See [current validation and limitations](VALIDATION_AND_LIMITATIONS.md). The historical evidence is preserved.

# Methodology and fidelity boundaries

Scientific basis: supplied paper §§4–5, pp.6–13; see PAPER_ANALYSIS for version and exact procedure. This document describes **our implementation**, including differences.

## SliceMin

Read `.py` files under an explicit root with file/byte limits, reject symlinks and parse with Python AST. Index top-level named functions and ordinary imports. Decorator and explicit registration patterns resolve a unique entry, or require a reviewed override. DFS visits reachable locally resolved callees once and records every observed caller/callsite; external and unresolved calls remain visible. Module-level imports, constants and classes are retained conservatively as context, so the output is not guaranteed minimal.

In static-only mode, no debloating is claimed. When a model is explicitly supplied, each node receives its body, all incoming call sites and whether it is externally callable. A reconstructed prompt asks for call-context pruning while preserving entry constraints. Parse each returned function, reject changes to its name/signature/registration/return annotation, record before/after/reason and mark equivalence unproven. Rebuild reachability; stop when unchanged or after a configurable cap. Nonconvergence is reported. No rewritten tool code executes.

The implementation uses built-in AST instead of tree-sitter and omits TypeScript, automatic dispatcher recognition and LLM entry fallback. It does not solve arbitrary aliasing, reflection, inheritance, nested-function or higher-order resolution. An unexpanded call is not automatically a safe library call. Syntax-level rewrite checks do not prove semantic equivalence. The offline rewrite unit test uses a manually specified response and validates graph reconnection, not LLM reasoning accuracy.

## DescGen

Remove actual docstrings through AST transformation; unparsing also removes comments. Preserve executable string literals. Truncate identifier tokens to 20 characters and reject collisions instead of silently merging names. An auxiliary model sees sanitized source and the identifier set, returns contextual neutral renames, and is checked for unknown names, invalid identifiers, excessive length and collisions. This path is exercised with synthetic replay; a contextual LLM classifier was not run locally.

Generate summary, functionality strings and JSON input schema using a reconstructed versioned prompt. Require an explicit unique claim targeting every prose field. Reject incomplete/malformed responses. This validates structure, not truth: an unsupported claim can be structurally valid and must still be tested. Inputs/prompts/responses/model identifiers/hashes stay in local audit logs. Full JSON-schema correctness and equivalence to the true MCP signature are not formally certified.

## DynVer

The model maps **every** listed claim to a verifiable task or a reason for nonverifiability. No plan may omit, duplicate or invent a claim. The runner returns ordered tool calls with arguments and observed results/errors. The judge receives the original claim, task and log. Retain only claims judged supported on observed cases. Remove refuted, inconclusive and nonverifiable prose. Preserve decisions and evidence outside the rendered description. Generate lite by omitting only the functionality list from refined full, retaining summary/schema.

Our refinement is one pass of filtering; it does not implement the paper example's free-form argument correction or an unspecified iterative refinement policy. Inconclusive is an explicit engineering extension: timeouts, missing dependencies, disabled backends and empty logs cannot prove a functional claim false. Removal from supported output is not a malware label. Structural schema fields (types/defaults/enums) remain uncertified and are explicitly warned about. A blank verified summary is unusable, rather than filled with invented prose.

`ControlledAgent` implements a bounded plan→call→observe loop, replacing LangChain/MCP only for controlled tests. It can invoke exactly two hardcoded, newly authored fixture functions, without file/network/process access. It never accepts an arbitrary Python callable or imports a research tool. It is **not an isolation boundary**. Unknown source uses `DisabledRunner`. External backend authors must establish trace provenance, isolation, deadlines and cleanup before integration.

## Experimental discipline

Original descriptions, lite and full are paper conditions; lite does not skip verification. TSR needs manually reviewed target invocation **and** objective success, complete expected task coverage and no duplicate results. Unknown labels reject the calculation. Runtime overhead uses the three-way successful-task intersection. Our ratio-of-means choice is documented because the paper omits aggregation details. Costs are unknown unless actually observed; replay makes zero API calls but zero is not a model price estimate.

The local experiment repeats the fixture pipeline with fixed replay responses and seed 42, saves a complete trace example, records Python/source/config hashes and wall times with `tracemalloc`. The Python allocation peak excludes native/GPU allocations and is not RSS. These are our engineering measurements. They supply no published TSR, attack success, semantic quality or security efficacy evidence. All original-condition measured cells remain blank.
