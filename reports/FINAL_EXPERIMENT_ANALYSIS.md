# Final experiment analysis

Generated 2026-11-09T14:24:22.101360+00:00.

## Bottom line

The independent pipeline ran end to end on real recovered MCP source. SliceMin sliced **30/30** Python tools from the 12 servers named in paper Table 1, and the pinned local model produced **9** structurally valid descriptions out of 26 attempted in this pass.

It did **not** reproduce the paper's benchmark. That is a data-availability limit, not an engineering one: the authors never released the 52-tool list, 208 tasks, prompts, labels or traces, and their anonymous artifact now returns HTTP 410 `repository_expired`.

## What was measured

| Quantity | Value |
|---|---|
| Paper servers with recovered public source | 12/12 |
| Python tools selected and sliced | 30 |
| Tool slots in unsupported languages (JS/TS) | 22 |
| DescGen attempted / valid | 26 / 9 |
| Valid-structure rate | 34.6% |
| Bounded pilot tools with three conditions | 3 |
| Task success rate | not computed (no tasks, no labels) |

| Failure type | Count |
|---|---|
| `ModelError` | 17 |

## Bounded pilot

Three tools with successful descriptions were carried to the full condition set (original developer description, TRUSTDESC-full, TRUSTDESC-lite):

| Tool | Source | Slice functions | Conditions | DynVer |
|---|---|---|---|---|
| `watch_topic` | arxiv-mcp-server | 5 | original, full, lite | plan_not_run_session_budget |
| `yfinance_get_ticker_info` | yfinance-mcp | 3 | original, full, lite | plan_not_run_session_budget |
| `set_note` | excel-mcp-server | 1 | original, full, lite | plan_not_run_session_budget |

Execution is gated: this build has no validated isolated runner for arbitrary third-party MCP servers, so no behavioural verdict and no TSR is recorded. Inventing one would be fabrication; the condition descriptions are real and the gap is the execution layer.

## Original vs. our results

| Item | Paper | Ours |
|---|---|---|
| Corpus | 52 tools, 12 servers, specific revisions | 30 Python tools of those 12 servers, current HEAD |
| Tasks | 208, 4 per tool, human-reviewed | 0 recovered; 8 authored fixtures (separate) |
| TSR | 84.1% original / 86.3% lite / 87.7% full | not computable |
| Generation model | Claude-4.5-Sonnet, Gemini-3-Flash, GPT-5.2, gpt-oss-120b | one 4-bit Qwen3-4B locally |
| Cost | $0.013/tool (Gemini-3-Flash) | local weights, unpriced |

## Interpretation

1. The static stage transfers: slicing worked on every selected Python tool, including custom registry decorators and nested factory registrations the paper does not enumerate.
2. The structured generation stage is model-bound. A 4B local model satisfies the claim-coverage, schema-consistency, identifier-normalization and output-budget rules for a minority of real tools; frontier models in the paper were not budget-available and paid APIs were not used.
3. No claim is made that TRUSTDESC does or does not improve task success. That question needs the authors' task set and a reviewable execution environment.
