# Experimental findings

Four questions, answered only from recorded evidence.

## What did we test?

An independent implementation of the three TRUSTDESC stages on a corpus we collected
ourselves:

- **SliceMin** on 30 Python tool entry points from 12 public MCP servers, at pinned commits.
- **DescGen** — a local 4-bit Qwen3-4B — on 28 of those tools.
- **DynVer** — 18 sandboxed executions across 3 tools and 3 description conditions,
  judged claim by claim.

Not tested: the paper's 208-task benchmark, its ground-truth labels, adaptive attacks,
TPA blocking, cost/quality-selection trade-offs. None of that material was available.

## What did we observe?

1. **Slicing generalises.** 30/30 Python tool slots were resolved, 20 through registration
   decorators and 10 through explicit qualified names. Two recovery patterns were enough
   for every Python server in the paper's list.
2. **Generation yield is 35.7%** (10/28). The largest single cause is our own 90-second
   deadline (8 rejections), then our identifier validator (7). Only one rejection was the
   model producing a structurally wrong answer. The bottleneck is our harness, not the
   model's understanding.
3. **Executable verification is possible but adapter-bound.** Real tool bodies ran
   unmodified inside Seatbelt, with network denied and writes confined to scratch. Only one
   of the servers had a shim layer, which capped the experiment at 3 tools.
4. **Claims mostly matched behaviour: 12 supported, 6 refuted.** All refutations cluster:
   `unwatch_topic` accounts for 4 of 6, because the tool reports `Watch not found` where
   even the developer's own text implies a successful removal in a fresh state.
5. **The three description conditions did not separate** — 4 supported / 2 refuted each.

## What did we learn?

- **The measurable part of TRUSTDESC works end to end.** Source → slice → description →
  generated task → sandboxed execution → claim verdict runs without a human in the loop,
  and every step is resumable and auditable.
- **The description is not the only source of failure.** `unwatch_topic` was refuted
  against the *developer's own* description, which means a refutation can indicate a
  genuine documentation defect — the phenomenon the method is designed to find — rather
  than a bad generated description.
- **Our measurement instrument is the weak link.** With 3 tools, 2 tasks per tool and a
  4B task generator, the experiment cannot distinguish "equal quality" from "insensitive
  test". Identical counts across conditions are consistent with both.
- **Sandbox engineering dominates the effort.** Getting real code to run safely took more
  work than the analysis: shims, signature dispatch, dependency access, resource limits.

## What remains unproven?

| Claim | Status |
|---|---|
| TRUSTDESC descriptions are more faithful than developer descriptions | **unproven** — no separation observed, sample too small |
| TRUSTDESC reduces tool-poisoning risk | **unproven** — no attack experiments run |
| The paper's TSR is reproducible | **unproven** — benchmark unreleased, no TSR computed |
| The pipeline generalises beyond Python | **unproven** — 22 JS/TS slots unsliced |
| Results hold at scale | **unproven** — 3 tools, 18 units, one server |

## The one-paragraph version

We built and ran a bounded reproduction of TRUSTDESC on a corpus we recovered ourselves.
Every stage executed on real code, and 18 sandboxed tool invocations produced 12 supported
and 6 refuted description claims. The refutations concentrate on a single tool whose
behaviour contradicts even its own developer text, which is the failure mode the method
targets. The three description conditions produced identical counts, so the pilot neither
confirms nor refutes the paper's central claim; with 6 units per condition and a 4B task
generator, it was not powered to. What the project does establish is that the pipeline is
implementable, auditable and honest about its own limits — and it documents exactly which
measurements would be needed to turn the pilot into evidence.
