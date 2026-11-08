# TRUSTDESC paper analysis

Primary source: Ye, Zhang, Jia and Hu, **TRUSTDESC: Preventing Tool Poisoning in LLM Applications via Trusted Description Generation**, arXiv:2604.07536v1, 8 April 2026. [Versioned record](https://arxiv.org/abs/2604.07536v1). All page numbers below refer to the supplied PDF's printed pages. Read all 17 pages, including four reference pages; visually checked Figures 5–7 and Tables 1–7. PDF SHA-256: `c0aed54402c07dc9420b908339fddfbed8eb40a2c316910489d0da28426c8cb4`. PDF metadata and page count, rather than the inaccurate initial `file` page estimate, identify this version. Local extraction is a reading aid, not a replacement scientific source.

## Problem and scope (§§1–3, pp. 1–6)

LLM agents select tools and prepare arguments from names, descriptions and input schemas, without inspecting implementations. Explicit tool poisoning inserts instructions into metadata; implicit poisoning exaggerates capabilities or quality to bias selection without an overtly malicious instruction. Detecting instructions alone does not establish description–implementation consistency.

The proposed defense replaces developer descriptions with descriptions inferred from accessible source. It is an installation-time description generation pipeline, followed by ordinary agent use of the generated descriptions. It is not a general per-call malware detector, trust classifier, permission engine or MCP firewall.

The adversary publishes tools and controls descriptions and semantics-bearing code artifacts, including names, comments and docstrings. Source availability and **absence of overtly malicious runtime implementation** are assumptions (§3.1, p. 5). Closed-source/remote implementations and malicious runtime code are outside scope. The paper assumes effective existing detection of explicit malicious instructions. These assumptions are research limitations, not properties our software can certify. Our capstone's broader behavioral defense must eventually address additional threats separately.

## SliceMin (§4.1, pp. 6–8)

1. Identify a tool's exposed entry using decorator registration (`@tool`, `@mcp.tool`, including name overrides), explicit `registerTool` calls, or dispatch on tool name. If patterns fail, an LLM examines regions around name occurrences. There is an ambiguity in the prose: the dispatcher is described as the entry in an example, while the registration-pattern bullet identifies the callee in a matched branch. Any reconstruction must state its convention.
2. Parse Python/TypeScript using tree-sitter. DFS constructs a tool-specific call graph. Each node records function body, callers and concrete call sites. Built-in and external library calls are recorded without expanding external code; repeated visits add callers/sites rather than recursing indefinitely.
3. An LLM receives each function with its concrete invocation contexts and removes or rewrites unreachable branches/parameters. Remove an entirely unreachable callee and its edge metadata. Reconnect and emit the refined slice. This is localized LLM-guided call-context debloating, not truncation or lexical retrieval.
4. Figure 4: `search_arxiv` never passes `year` to `search_handler`; year filtering is unreachable for that entry. Figure 6: `create_chart` never exposes optional style customization; replace it with the default style and remove unavailable branches. Slices are reasoning artifacts: rewritten signatures do not justify deploying rewritten tool implementations.

No formal slicing correctness theorem, alias analysis, fixed-point rule, maximum iterations, transformation validation algorithm, exact fallback prompt or full language semantics is supplied. Dynamic dispatch, reflection and higher-order code complicate soundness. LLM rewrites may themselves be wrong.

## DescGen (§4.2, pp. 8–9)

Generate (1) concise summary, (2) supported functionality list and (3) precise input schema from the minimal slice. Strip comments/docstrings; normalize identifiers to at most **20 characters**; use an auxiliary contextual LLM classifier to remove promotional/biased identifier terms. These defenses are complementary. A banned-word list alone is not the classifier in the paper. Normalization is for reasoning; it may collide or change name meaning. Strings that affect behavior must not be casually deleted.

`TRUSTDESCfull` includes all three output components. `TRUSTDESClite` omits only the functionality list from the **refined description**, retaining summary and input schema. Lite is not a version that skips SliceMin or DynVer.

## DynVer (§4.3, p. 9)

Analyze the initial description into statements. Discard statements not meaningfully runtime-verifiable (e.g., internal implementation details). An LLM synthesizes an executable task for each remaining statement. A LangChain agent with the tested tool set plans and executes it, recording tool sequences and results. A separate LLM judging step sees statement, task and log, retains supported claims and refines/removes incorrect ones. The workflow is described as iterative; iteration limits, stopping criterion and exact refinement prompts are missing.

Example: `apply_formula` rejects formulas without `=`. A generated claim that it automatically adds `=` is falsified by executing that case. Correct the input argument description. A failed task due to environment problems, however, is not evidence that a claim is false. Our implementation uses an explicit inconclusive state for such cases (an engineering extension). Finite successful examples cannot prove universal claims or exclude conditional malware.

## Evaluation design (§5, pp. 9–13)

Table 1 links 12 server repositories, lists language/category and counts, not exact selected tools or revisions. Sample 20 Python/TypeScript servers from awesome-mcp-servers' 1,364-entry collection; exclude eight requiring remote/paid access. Evaluate all tools for servers with fewer than five, otherwise randomly sample five. Total 52. Neither sampling seed nor source snapshot is given. See `data/manifests/paper_servers.json` for all paper-linked URLs; its language labels deliberately preserve Table 1 even where repository contents may differ.

Generation models: Claude-4.5-Sonnet, Gemini-3-Flash, GPT-5.2 (via OpenRouter), gpt-oss-120b (local **four RTX PRO 6000 Blackwell GPUs**). Temperature **0.2**, default reasoning effort. Provider model IDs, exact dated versions, hardware precision/serving stack and decoding details are absent. These are generation configurations; task execution uses a Gemini-3-Flash prebuilt ReAct agent, not four different execution agents.

Q1: four tasks/tool, two from original and two from generated descriptions, no tool names in tasks, diverse capabilities; 52 × 4 = 208. This suggests possible generated-description task bias; exact whether one shared task set was reused across all generation models is unclear. Agent runs original/full/lite. Human trace review requires target tool invocation **and** objective achievement. TSR = successful tasks / tasks × 100. It is an indirect accuracy proxy, not ground-truth semantic equivalence. No training, validation or classifier test split is specified.

Q2: one-time generation tokens/dollars/seconds per stage and runtime relative overhead on **tasks successful in all three conditions**; this intersection conditioning must be preserved. Q3: one high-quality tool/server paired separately with three degraded versions (security checks removed, one feature disabled, two disabled), use §5.1 tasks and measure selection of the degraded tool. Exact mutations, order randomization and denominators missing. 50% is the comparison reference, not a trained baseline.

Q4: seven public attacks (five explicit/two implicit); manually inspect whether attack-triggering instructions or biased terms survive regeneration. This is not a measured end-to-end attack success rate or adversarial benchmark of all MCP attacks. Linked attack sources in `paper_attacks.json`.

Q5: Gemini-3-Flash adaptive naming attack on the 12 Q3 tools, 15 iterations; perturb names under the length threshold, regenerate and compete with original implementations. Figure 7 gives a plotted trajectory and text gives range/trend tests, but exact per-iteration numeric data are not printed. We do not manufacture values by reading approximate plot positions.

## Quantitative reference and consistency checks

`reports/published_results.csv` transcribes every numeric cell of Tables 2–6 and textual quantitative findings, with source references, units and blank measured/difference columns. Table 1 metadata and Table 7 attack outcomes have separate manifests. Figure 7's exact trajectory is unavailable; only printed statistics are transcribed. Reported values are never local measured values.

Original TSR is 175/208 = 84.1%; average full 182.5/208 = 87.7%, lite 179.5/208 = 86.3%. Thus full's improvement is approximately **3.6 percentage points**, or **4.3% relative** using counts. The abstract/introduction's 4.3% should not be presented as a percentage-point gain. Average 182.5 is a mean over four models, not a fractional completed task within one run.

Table 2 contradicts the prose “consistently outperform”: gpt-oss lite equals original; GPT-5.2 full is below GPT-5.2 lite. Table 3 has entries of two despite prose saying “less than two.” Preserve table numbers. Intro runtime +4%/+0.2% corresponds to **lite**; full is +0.3% cost/−1.7% latency. Table 4 stages/totals contain rounding/aggregation differences; do not recompute or silently fix printed totals. The §6 counts of 7 no argument descriptions, 19 minimal, 16 complete and 9 with examples need not be mutually exclusive categories.

## Gaps and critique

No exact released code, prompts, 52-tool list, 208 tasks, raw logs, seeds, judge rubric, repetitions, confidence intervals, dependency lockfile or commits were obtained. No original experimental result can currently be reproduced quantitatively. The paper reports 2,377 implementation lines; that is not an available code artifact. The suggested anonymous artifact URL is not embedded in this supplied PDF's text or link annotations; its relationship to this version remains unverified even though the site confirms expiry.

Static over-approximation, uncertain LLM rewrites, insufficient negative tests, conditional behavior, external service dependencies, classifier/judge bias, and circular reliance on LLM reasoning limit guarantees. Cost numbers are historical measurements, not current price quotes. Model/hardware equivalence on a free Colab T4 must not be claimed. No system extension or “improvement” is evaluated here before a genuine model-backed baseline exists.
