# Final project status

Checkpoint 2026-11-10. Base commit `08bd497` plus this checkpoint's commit (see `git log -1`).
Every statement below is backed by a file listed in `reports/FINAL_DELIVERABLE_AUDIT.md`.

## Implemented and tested

| Component | Evidence |
|---|---|
| SliceMin for Python: entry resolution (decorator + qualified name), call-graph slice, unresolved-call recording | 30/30 tools sliced; 146 functions, 162 edges; `data/recovered_slices/` |
| DescGen with local 4-bit Qwen3-4B: slice-grounded prompting, structured output, mechanical validation, resumable state | 28 attempts recorded; `reports/recovered_descgen/run_state.json` |
| DynVer with macOS Seatbelt: deny-by-default policy, scratch-only writes, no network, resource limits, isolation canaries | probe passes; `src/trustdesc/sandbox/seatbelt.py` |
| Adapter shims for `arxiv-mcp-server`, real body unmodified | `src/trustdesc/dynver/recovered.py`, `tests/unit/test_recovered_dynver.py` |
| Verdict gating: deterministic rules first, shim-dependent claims never `supported` | `verdict_for`, unit tests |
| Experiment runner: resumable per unit, records policy hash, refuses without isolation | `scripts/run_dynver_recovered.py` |
| Analysis and figures pipeline | `scripts/analyze_statistics.py`, `scripts/generate_figures.py` |
| Automated tests | 165 passing, 8.0 s |
| Notebook | 12 cells; 5 of 6 code cells executed in a fresh kernel with zero errors |

## Implemented but only partially evaluated

| Component | What was evaluated | What was not |
|---|---|---|
| Three-condition comparison | 6 claims per condition, 3 tools | unpaired design, no second judge, far below the ~90 units/condition needed |
| Description quality | 10 valid descriptions, 88 claims | no human review of description faithfulness |
| Execution coverage | 3 tools from 1 server | 5 sliced servers never executed for lack of shims |
| Failure analysis | 18 rejections categorised | no re-measurement after fixing the identified validator issues |

## Not implemented

| Item | Consequence |
|---|---|
| TypeScript / JavaScript slicing | 22 tool slots unrepresented |
| Adapter shims beyond one server | cannot execute most sliced tools |
| Shared task set across conditions | no valid paired comparison |
| Attack / poisoning experiments | no security claim can be made |
| Second judge model | single-judge verdicts |

## Not recoverable with currently available materials

| Item | Reason |
|---|---|
| Paper 208-task benchmark and labels | never released; artifact offline (HTTP 410) |
| Author traces, prompts, revisions | never released |
| Paper TSR, cost, quality-selection results | require the above |
| Adaptive-attack results | require unreleased harness |

## Headline numbers

12/12 servers recovered · 30/30 Python tools sliced · 22 JS/TS slots unsupported ·
10/28 descriptions valid (35.7%, Wilson 95% 20.7–54.2%) · 88 claims ·
18 sandboxed executions · 12 supported, 6 refuted, 0 inconclusive ·
4 supported of 6 in each condition, no separation observed · **no task success rate claimed**.

## New experiments (2026-11-10, after the checkpoint)

| Experiment | Result | Status |
|---|---|---|
| Matched-task comparison (same task, same observation, 3 descriptions) | 3/3/3 consistent, no separation | implemented, evaluated on 3 valid tasks |
| Synthetic poisoning detection (12 cases, 4 categories) | TP 5, FN 1, TN 3, FP 0; 3 injection cases unsupported | implemented, 9 eligible cases only |
| Cross-tool stateful tasks | not possible: fresh temp directory per execution | unsupported by harness |

| Negation-aware claim layer | recorded S1 false negative corrected (5/6 -> 6/6 eligible, no new FP) | implemented, 15 tests; one recorded case exercised it |
| Static injection screen | TP 12, FP 0, TN 8, FN 0 on 20 synthetic cases (3 ambiguous excluded) | experimental, not wired into the pipeline; not a defence |
| Injection screen, independent challenge set | TP 0, FP 1, TN 7, FN 19 on 27 unseen cases (recall 0/19, FPR 1/8) | **fails on paraphrase-level injection**; keyword rules do not generalise |
| Negation layer, controlled probes | 14/14 match verdicts fixed before running; two defects found and fixed | implemented, tested; file-existence claims only |

Details: `reports/NEW_EXPERIMENT_RESULTS.md`, `reports/JUDGE_RELIABILITY.md`,
`reports/INJECTION_DETECTION_EXPERIMENT.md`. These results are **not** merged with the
earlier 18-unit pilot, and no task success rate is derived from them.

## Honest one-line status

A working, tested, auditable implementation of all three TRUSTDESC stages, exercised on a
recovered real-world corpus, with a deliberately underpowered three-condition pilot that
found a localised description/behaviour gap and no difference between conditions.
