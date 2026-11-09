# Original dataset acquisition report

Generated 2026-11-09T14:24:22.189369+00:00. **No original TRUSTDESC benchmark record was recovered.**

## 1. What the paper actually releases

- Table 1 (p.9) names 12 public MCP servers, their language, category and the number of tools selected (total 52) — locations and counts only, **not** tool names, revisions or code.
- §5 states 208 tasks were generated (4 per tool, 2 from the original and 2 from the generated description) and that success required **manual** trace inspection. No task text, prompt, label or trace is published.
- No data-availability statement, artifact link, code release or supplementary bundle appears in the arXiv abstract, HTML full text or PDF of arXiv:2604.07536v1.

## 2. Artifact investigation (all evidence in `reports/original_dataset/artifact_probe.json`)

| Endpoint | Observed | Meaning |
|---|---|---|
| `/r/ae-trustdesc-13A6` | HTTP 200, SPA shell only | landing page loads, repository data does not |
| `/api/repo/ae-trustdesc-13A6` | HTTP 401 `{"error":"not_connected"}` | no repository bound to the id |
| `/api/repo/ae-trustdesc-13A6/files` | HTTP 410 `{"error":"repository_expired"}` | anonymous bundle expired |
| `/api/repo/ae-trustdesc-13A6/zip` | HTTP 410 `{"error":"repository_expired"}` | archive expired |
| Wayback availability API | `archived_snapshots: {}` | never captured |
| Wayback CDX prefix query | timed out / empty | no historical capture |
| GitHub repository search `trustdesc` | 1 result = this reproduction repo | no authors' release |
| `hengkai-ye.github.io` | HTTP 404 | no author project page |

No authentication bypass, credential use or access-control circumvention was attempted. The artifact is unavailable because it expired, not because access was refused.

## 3. What was instead recovered (labelled `independently_collected`)

All 12 paper-named public server repositories were cloned at a pinned commit. Every selected Python tool was then statically discovered and sliced by SliceMin.

| Server | Paper | Commit | License (first line) | Tools discovered (py/js+ts) | Tools sliced |
|---|---|---|---|---|---|
| excel-mcp-server | 5 Python | `1e6af4e06338` | MIT License | 48 / 0 | 5 |
| markdownify-mcp | 5 TypeScript | `024f97cea9a9` | MIT License | 0 / 11 | 0 |
| mysql_mcp_server | 1 Python | `943ce8381637` | MIT License | 3 / 0 | 1 |
| arxiv-mcp-server | 4 Python | `572e301bb319` | Apache License | 19 / 0 | 4 |
| paper-search-mcp | 5 Python | `cab1b5cc276a` | MIT License | 74 / 0 | 5 |
| filesystem | 5 TypeScript | `36380287ed3b` | The MCP project is undergoing a licensing transi | 0 / 16 | 0 |
| context7 | 2 TypeScript | `2111b92614fb` | The MIT License (MIT) | 0 / 42 | 0 |
| wikipedia-mcp | 5 Python | `88579193daa4` | MIT License | 11 / 0 | 5 |
| yfinance-mcp | 5 Python | `d5fe3253d03c` | MIT License | 15 / 0 | 5 |
| travel-planner-mcp | 5 TypeScript | `cfec0e4e8233` | MIT License | 0 / 5 | 0 |
| healthcare-mcp | 5 TypeScript | `1c4c40c3bb63` | MIT License | 0 / 11 | 0 |
| imagesorcery-mcp | 5 TypeScript | `2f77957a0671` | MIT License | 17 / 0 | 5 |

Selected tools: **30** (the paper's per-server counts). Sliced: **30**. The remaining 22 of the paper's 52 tools are JavaScript/TypeScript, which the current implementation does not parse.

Tool identity is a **deterministic prefix of static discovery order**, not the authors' random sample (seed never released). Exact tool identity therefore cannot match the paper.

## 4. What remains impossible

Exact reproduction of Q1 TSR (208 tasks × 3 description conditions × 4 generation models), Q2 cost, Q3 tool-quality selection, Q4 TPA blocking and Q5 adaptive attacks all require author records that are not public. They are reported as **not recovered**, never as measured.

A conservative author request is prepared in `MISSING_RESEARCH_MATERIALS.md`; it has **not** been sent and requires user approval.
