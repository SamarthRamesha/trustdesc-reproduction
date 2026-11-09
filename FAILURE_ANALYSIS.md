# Failure analysis

Generated 2026-11-09T14:24:22.028022+00:00.

Failures are reported as observed. None were retried into a different semantic path, and no scripted description was substituted for model output.

## B1. DescGen structural rejections (real model, recovered source)

| Failure type | Count | Cause |
|---|---|---|
| `ValidationError` | 0 | the generated JSON did not satisfy the claim-coverage rule (every summary, functionality and schema description needs exactly one matching claim) |
| `ModelError` | 17 | output was not the required single JSON object, or the generation deadline/length limit was hit |
| other | 0 | worker or slice lookup issue; see per-tool records |

Raw rejected outputs are preserved in `reports/recovered_descgen/model_calls.json` and `run_state.json`, so the rejection can be audited rather than trusted.

The dominant cause is model capability at the required structure, not an unreachable code path: the same binary passes the qualification suite (arithmetic, structured JSON, exact tool action) and the same validator accepted descriptions for the small authored fixture tools.

## B2. Stage-level blockers

| Blocker | Effect | Mitigation taken |
|---|---|---|
| DynVer needs to execute third-party tool code | no behavioural claim adjudication on recovered tools | stage recorded as blocked; authored-fixture DynVer evidence preserved |
| TypeScript/JavaScript unsupported | 22 of the paper's 52 tool slots cannot be sliced | recorded per server; no substitution |
| Original artifact expired (HTTP 410) | no exact benchmark | independent corpus built and labelled |
| Current HEAD ≠ paper revision | tool sets and code differ from the paper's snapshot | commit pinned and disclosed per server |
| LLM debloating not applied | slices over-approximate; descriptions may mention unreachable logic | `mode: static_only_no_debloating` recorded in every slice |

## B3. Slice quality caveats

- Class and instance method bodies are retained as context but resolved statically only; nested helpers appear as unresolved calls.
- excel-mcp-server slices are small because its tool bodies delegate to helper modules and workspace objects that the resolver does not expand; a description built from them is necessarily thin.
- Unresolved-call counts per tool are recorded, so the reader can see how much behaviour is outside the slice rather than assuming completeness.

## B4. What would change the conclusion

1. Author release of the 52-tool list, 208 tasks, prompts and labels.
2. A validated isolated runner for third-party MCP execution, enabling DynVer on real tools.
3. TypeScript parsing, which would cover the remaining 22 tool slots.
