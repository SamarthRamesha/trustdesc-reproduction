# TRUSTDESC in plain language

A summary for a reader who has not read the paper.

## The problem: a tool description is an unverified promise

AI agents increasingly act through tools — search the web, read a file, query a database —
exposed over the Model Context Protocol (MCP). The agent does not see the tool's code. It
sees a name, a JSON schema, and a paragraph of prose, and it decides from that whether to
call the tool and with what arguments.

That makes the description a security surface. A description that says "formats a report"
while the code also uploads the file somewhere is a working attack, and nothing in MCP
checks the prose against the implementation. Even without malice, descriptions drift: they
are written once, the code changes, and the agent is left acting on a stale promise.

## What TRUSTDESC proposes

Stop trusting prose. Derive it from code, then check it against reality — three stages:

1. **SliceMin** — find the tool's entry point in the source, follow its calls, extract the
   minimal set of code that actually runs.
2. **DescGen** — generate the description *from that slice*, so the text can only claim what
   the code can do. Producing structured, per-claim statements rather than free prose makes
   the next stage possible.
3. **DynVer** — turn each claim into a task, execute the real tool, and judge whether the
   observed behaviour matches the claim. A claim the tool contradicts is a description
   defect; a claim the tool confirms is evidence the description is honest.

The output is not "this tool is safe". It is "these specific statements are true of this
specific code, and these are not".

## How our implementation works

- **SliceMin** parses Python with `ast`, resolves the entry point either from a registration
  decorator or from an explicit qualified name, then walks the call graph. It records what it
  could not resolve rather than guessing.
- **DescGen** runs a 4-bit Qwen3-4B locally through MLX. The prompt contains only the slice.
  Output must be valid JSON with schema, functionalities and claims, and it is rejected if
  argument names disagree with the real signature.
- **DynVer** generates tasks from claims, then runs the tool body inside macOS Seatbelt with
  a deny-by-default profile: no network, writes only to a scratch directory, limits on CPU,
  file size and child processes. Before any third-party code runs, four isolation canaries
  must fail to escape.
- **Adapter shims** let a real tool body run without its network transport. Only imports are
  replaced; the body executes unmodified. Any claim that depends on a shim is reported as
  `inconclusive`, never `supported`.

## How our setup differs from the paper's

| | Paper | This project |
|---|---|---|
| Tool corpus | 52 tools, task benchmark of 208 | 30 Python tools we recovered ourselves; 22 JS/TS slots unsupported |
| Source | released artifact | artifact offline (HTTP 410); 12 named servers cloned at pinned commits |
| Task benchmark | 208 authored tasks with labels | our own generated tasks; no labels, no original tasks |
| Ground truth | labelled expectations | sandboxed observation plus a model judge gated by deterministic rules |
| Metric | task success rate, cost, quality selection | claim-level verdicts only; **no TSR computed** |
| Attacks | adaptive attacks, TPA blocking | not attempted |

## What we measured

| Measurement | Result |
|---|---|
| Python tool slots sliced | 30 / 30 |
| Valid descriptions generated | 10 / 28 (35.7%, Wilson 95% 20.7–54.2%) |
| Claims generated | 88 total, 6–11 per description |
| Sandboxed executions | 18 (3 tools × 3 conditions × 2 tasks) |
| Claims supported / refuted | 12 / 6 |
| Developer text vs TRUSTDESC-full vs lite | 4 / 4 / 4 supported of 6 each — no separation |

The refutations are concentrated: four of six land on `unwatch_topic`, which reports
`Watch not found` where even its own developer description implies a successful deletion.
That is a real description/behaviour gap, and it is the kind of thing this method exists to
find — but it rests on one tool.

## What remains incomplete

- **22 TypeScript/JavaScript tool slots** are not sliced; no TS parser is implemented.
- **Five servers have no adapter shim**, so they cannot be executed even though they are sliced.
- **The paper's benchmark, labels and traces were never obtained**, so no comparison with its
  reported task success rate is possible, and none is claimed.
- **The comparison is underpowered**: 6 units per condition from 3 tools. Identical counts
  are not evidence of equivalence, and no significance test is reported.
- **Attacks were not attempted**, so nothing here speaks to poisoning resistance.

## Why the null result is still useful

A pilot that cannot detect a difference is informative when it says so. This one establishes
that the pipeline runs end to end on real code, that sandboxed claim verification produces
localised, interpretable findings, and that the binding constraint is measurement design
(shared tasks, more tools, more units) rather than the idea. Those are exactly the
preconditions a follow-up study needs, and the handover lists them as concrete work packages.

## Where to look next

- Numbers: `reports/STATISTICAL_RESULTS.json`, `reports/STATISTICAL_ANALYSIS.md`
- Figures: `reports/figures/FIGURE_INDEX.md`
- Findings: `reports/EXPERIMENTAL_FINDINGS.md`
- Limits: `reports/KNOWN_LIMITATIONS.md`
- Continuation: `TEAM_HANDOVER.md`
