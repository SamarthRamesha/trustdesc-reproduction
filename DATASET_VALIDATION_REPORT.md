# Dataset validation report

Generated 2026-11-09T14:24:22.189369+00:00.

Validation of the **independently collected** corpus. Passing these checks does not make it the paper's benchmark.

| Check | Result | Observed |
|---|---|---|
| 12 paper servers have public source | PASS | 12/12 |
| Python-subset selected count equals paper counts for those servers | PASS | 30 selected; 52 total is only reached with TypeScript support |
| per-server selected count matches paper for every sliceable server | PASS | 12/12 server rows checked |
| no duplicate tool record ids | PASS | 0 duplicates |
| every sliced tool records a source hash | PASS | 30/30 |
| every tool record pins a commit | PASS | 30/30 |
| every tool record carries a license line | PASS | 30/30 |
| SliceMin entry resolution succeeded for all selected tools | PASS | 30/30; unresolved: [] |
| task records recovered from the authors | NOT MET | 0 (never released) |
| ground-truth labels recovered | NOT MET | 0 (manual review, unreleased) |
| execution traces recovered | NOT MET | 0 (unreleased) |
| paper tool revisions recovered | NOT MET | 0 (unreleased; current HEAD pinned instead) |

## Distribution of evidence

- Python tools discovered and selected: 30
- Sliced with a resolved entry: 30
- Entry via registration pattern: 20
- Entry via explicit name match: 10
- JavaScript/TypeScript tools identified but not sliceable: 22

## Findings that affect interpretation

1. **Registration style is far more varied than the paper's three patterns.** The recovered repositories use `@mcp.tool`, custom registry decorators (`@tools.reader("Read range")`), explicit `Tool(name=...)` objects returned by `list_tools`, and nested factory closures. Ten of thirty entries needed an explicit module-qualified entry, which the paper delegates to an LLM fallback that is not implemented here.
2. **Nested registrations** (excel-mcp-server's `register(tools, workspace)` closures) only resolve through qualified names; without that extension static entry detection finds nothing.
3. **Table 1 language labels do not always match repository contents.** `healthcare-mcp` is labelled TypeScript in the paper but ships `.js`; `travel-planner-mcp-server` ships a single TypeScript entry point. The paper's labels were preserved, not corrected.
4. **MCP servers move.** Current HEAD is not the paper's revision, so even the same server can expose a different tool set. This is recorded per server rather than silently substituted.
5. **No task layer exists.** Without task text there is no TSR, and none is computed from this corpus.
