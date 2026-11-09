# Missing research materials

Generated 2026-11-09T14:24:22.189369+00:00.

| Material | Status | Consequence |
|---|---|---|
| Original tool implementations (selected 52) | NOT RECOVERED | Artifact expired; no code release. Public server repos cloned instead at current HEAD. |
| Original MCP server identities | PARTIALLY RECOVERED (paper Table 1) | 12 server repositories named and cloned; the paper's 20-server sampling frame was not. |
| Original source revisions/commits | NOT RECOVERED | Never published; current HEAD pinned. |
| Original tool descriptions | NOT RECOVERED | Descriptions exist in live repositories, but the specific paper-revision text is unknown. |
| Original task definitions (208) | NOT RECOVERED | LLM-generated then manually reviewed; unreleased. |
| Task-to-tool mappings | NOT RECOVERED | Unreleased. |
| Original 208 task records | NOT CONFIRMED AS A RELEASABLE FILE | Count confirmed from §5 text only. |
| Original prompts | NOT RECOVERED | Paper describes stages, not prompt text. |
| Original model configurations | PARTIALLY RECOVERED (paper text) | Model display names, temperature 0.2 and provider named; IDs, versions and serving stack absent. |
| Ground-truth labels | NOT RECOVERED | Manual human trace review; no label file. |
| Execution traces | NOT RECOVERED | Unreleased. |
| Evaluation scripts | NOT RECOVERED | Unreleased. |
| Metric definitions | RECOVERED FROM PAPER TEXT | TSR and the Q2 relative overhead definitions are stated. |
| Tool-quality experiment materials | NOT RECOVERED | Degradation strategies described qualitatively; mutations, ordering and denominators absent. |
| Adaptive-attack materials | NOT RECOVERED | Only a plotted trajectory and trend statistics are printed. |
| Artifact bundle (anonymous.4open.science) | EXPIRED | HTTP 410 repository_expired; no Wayback capture. |

## Prepared author request (not sent)

> Subject: Request for the TRUSTDESC evaluation bundle (arXiv:2604.07536)
>
> Dear Dr. Ye and co-authors,
>
> We are independently reimplementing TRUSTDESC and would like to evaluate it against your original benchmark. The anonymous artifact (ae-trustdesc-13A6) now returns `repository_expired`, and no code or data release is linked from the paper.
>
> Could you share: (1) the 52 selected tools with their server and commit, (2) the 208 task texts and their tool mappings, (3) the prompt templates for SliceMin/DescGen/DynVer, (4) the model identifiers and settings, and (5) the reviewed labels or evaluation scripts?
>
> We will cite the paper and keep your provenance labels intact.

**This message has not been sent. Sending requires explicit user approval.**

## Alternatives already pursued

- All 12 paper-named public servers cloned and pinned (see `SOURCE_PROVENANCE.json`).
- Static discovery and SliceMin coverage measured on the Python subset.
- Real local model descriptions generated for the recovered slices (see `METRICS_REPORT.md`).
- Exact reproduction remains marked incomplete; no value is fabricated to fill a gap.
