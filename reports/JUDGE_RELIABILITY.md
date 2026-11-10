# Negated-claim reliability (2026-11-10)

Scope: the recorded false-supported result from the poisoning experiment, what caused it, and a
narrow deterministic correction with tests. No new executions and no new model calls — the
correction is applied to the recorded evidence and to synthetic probe claims.

Files: `src/trustdesc/dynver/negation.py`, `tests/test_negation_judge.py`,
`reports/NEGATION_TEST_RESULTS.json`, `reports/figures/fig11_judge_reliability.png`.

## The defect

Recorded case `S1-watch-memory-only`:

- claim: *"No file is created by creating a watch."*
- observation: `./watched_topics.json` exists and contains the watch.
- judge verdict: **supported**, reason *"The observation shows that a file named
  './watched_topics.json' is created ... directly supporting the claim that a file is created"*.

The judge dropped the negation. Given the observation, the claim is false, so this was a false
negative for detection. There is no polarity handling anywhere in the path: `verdict_for` only
looks at call status, and `JUDGE_SYSTEM` says nothing about negation.

## The correction

Rather than asking the model to reason more carefully about negation (unverifiable), the narrow
class of claims whose truth is directly checkable — *was this file created?* — is now adjudicated
deterministically, **in front of** the model:

1. `polarity(text)` counts explicit negation cues (`not`, `n't`, `no`, `never`, `without`, `none`,
   `cannot`): 0 → affirmative, 1 → negated, 2 → double negated, ≥3 → ambiguous.
2. `adjudicate_claim` handles two shapes and nothing else: an absence claim ("no file is
   created") checked against the file snapshot, and a named path with a creation verb
   (`writes ./watched_topics.json`). Anything else returns `None`.
3. Double negatives and ambiguous wording return `inconclusive`, never a guess.
4. Missing or unusable evidence (no `files` mapping, non-`ok` call status) returns
   `inconclusive`.
5. `combine` returns the deterministic verdict where it applies, otherwise the model's, and
   records `overrode`, so any report can state how often the layer changed an answer.

Refuting an affirmative existence claim assumes `snapshot()` lists the whole working directory.
That assumption is stated in the module, not hidden.

## Re-evaluation of recorded evidence

| | model judge only | with negation-aware layer |
|---|---|---|
| TP | 5 | **6** |
| FN | 1 | **0** |
| TN | 3 | 3 |
| FP | 0 | 0 |

Exactly **one** of the 12 recorded cases changed verdict (`S1-watch-memory-only`, supported →
refuted), and that was the only case the deterministic layer adjudicated. The other 11 either
carry no file-existence claim (deferred to the model) or were already consistent with the
deterministic rule.

## Tests

`tests/test_negation_judge.py` — 15 tests: positive claim with file present/absent, contradictory
evidence (a different file only), negated wildcard claim with and without files, negated path
claim with file present/absent, double negative → inconclusive, ambiguous wording →
inconclusive, missing evidence → inconclusive, failed call → inconclusive, non-existence claims
deferring to the model, and override bookkeeping. All pass.

## What this establishes, and what it does not

- The recorded false supported verdict is reproducible from the record and is fixable for
  file-existence claims by a deterministic rule that is checked by tests.
- Detection on the same 12 synthetic cases moves from 5/6 to 6/6 eligible poisoned cases with no
  new false positive.

Not established:

- That the model judge is now reliable on negation in general. The layer handles only
  file-existence claims; negated claims about counts, ordering, network access or side effects
  still go to the model unchanged. Exactly one recorded case exercised the new path.
- Any estimate of how often negated claims occur in real descriptions.
- That the deterministic rule is right about files outside the snapshot's directory.
