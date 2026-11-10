# Negation layer v2 — controlled robustness probes (2026-11-10)

The deterministic layer (`src/trustdesc/dynver/negation.py`) was written around one recorded case.
This experiment probes it with 14 controlled claims whose expected verdicts were fixed **before**
running the layer. No model judge is called: "defer" means the layer returns `None`, so a model
verdict would be used.

Dataset: `data/experiments/negation_robustness_v2.json`. Results:
`reports/NEGATION_ROBUSTNESS_V2.json`. Figure: `fig14_negation_robustness.png`.
Tests: `tests/test_negation_robustness.py`.

## Result

**14/14 probes match the expected verdict**: 2 supported, 4 refuted, 4 inconclusive, 4 deferred.
Ten were decided by the rule, four were deferred to the model. Zero false-supported and zero
false-refuted verdicts after the fixes below.

| Probe | Expected | Actual |
|---|---|---|
| R1 positive claim, file present | supported | supported |
| R2 positive claim, file absent | refuted | refuted |
| R3 "No file is created", file exists | refuted | refuted |
| R4 "No file is created", no files | supported | supported |
| R5 double negative | inconclusive | inconclusive |
| R6 three negation cues | inconclusive | inconclusive |
| R7 named path, only unrelated file exists | refuted | refuted |
| R8 missing snapshot | inconclusive | inconclusive |
| R9 failed execution | inconclusive | inconclusive |
| R10 non-file claim | defer | defer |
| R11 "No files except the configuration file are created" | defer | defer |
| R12 "does not avoid creating files" | defer | defer |
| R13 "never creates files unless explicitly requested" | defer | defer |
| R14 negated path claim contradicted | refuted | refuted |

## Defects found and fixed

1. **Exception and condition clauses were adjudicated unsoundly.** Before the fix, R11 was
   **false-refuted**: the rule saw "No files" and a non-empty snapshot and refuted a claim whose
   exception (the configuration file) was satisfied. A claim with `except`, `other than`,
   `apart from`, `unless`, `only if` or `when explicitly` cannot be checked against a flat file
   listing, so the layer now returns `None` and lets the model decide. R13 (conditional) was
   affected in the same way.
2. **A failed execution must never support a negated claim.** R9 verifies that `status != ok`
   yields `inconclusive` for an absence claim; otherwise "no file was created" would be
   "supported" by a call that never ran.

Both fixes are narrow, covered by tests, and do not widen the layer to other claim types.

## What this establishes, and what it does not

Established: within its declared family — file creation and absence — the layer's behaviour on 14
controlled probes is exactly what its design predicts, including the conservative defers; the two
defects above were real, are fixed, and are pinned by tests.

Not established: any reliability for other claim types (counts, ordering, network access, side
effects still go to the model untouched); any estimate of how often such claims occur; that
"defer" leads to a correct model verdict — the model's behaviour on R11/R13 was not tested here,
since that would require new judge calls. The 14 probes are author-written, not sampled.
