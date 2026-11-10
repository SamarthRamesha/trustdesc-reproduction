# Pipeline integration audit (2026-11-10)

Static inspection of the boundaries touched by the negation layer and the injection screen, plus
the tests that exercise them. This is a code-path audit, not a penetration test, and it supports no
security claim beyond the checks listed.

| Check | Method | Result |
|---|---|---|
| Injection screening is never executed inside verification | `grep -rn "injection_detector" src scripts` | imported only by `scripts/analyze_robustness.py` and `scripts/analyze_final_experiments.py`; nothing in `src/trustdesc/pipeline.py` or `dynver` imports it |
| Screening does not execute or evaluate description text | `RULES` are `re.compile` patterns used with `pattern.search(text)`; no `eval`, `exec`, `subprocess`, file or network access in the module | confirmed by reading the module; `test_empty_text`, `test_screen_is_deterministic_and_inert` |
| Descriptions cannot alter the sandbox policy | `dynver/recovered.py` contains no reference to description text; `build_module` uses the slice source only, and `seatbelt.policy(scratch, extra_reads)` derives the SBPL profile from the scratch directory and the interpreter path | confirmed by grep and by reading `build_module` / `policy` |
| Detector cannot be mistaken for a defence | module docstring, report, figure caption and handover all say "prototype, not a defence", and the pipeline does not call it | confirmed by inspection |
| Negation layer cannot override unrelated claims | `adjudicate_claim` returns `None` unless the claim is a file-existence claim; `combine` then keeps the model verdict and records `source='model'` | `test_non_existence_claims_defer_to_the_model`, `test_deferral_cases_really_defer` |
| Missing evidence yields inconclusive | `missing_file_evidence`, `unusable_observation` paths | `test_missing_evidence_is_inconclusive`, R8 |
| Failed execution cannot become supported | `verdict_for` returns refuted/inconclusive for non-`ok` status; the negation layer returns inconclusive before comparing files | `test_failed_call_never_supports_even_a_negated_claim`, R9 |
| Seatbelt probes and existing results unchanged | full test suite; `git status` before commit showed only the two new modules modified and new files added | 193 pre-existing tests still pass; no historical report file touched |

## Findings

1. **No execution path from description text into the sandbox or the detector.** The only consumer
   of description text outside the judge payload is the offline analysis scripts.
2. **The screen has no demonstrated detection value outside its keyword shapes** (see
   `INJECTION_ROBUSTNESS_V2.md`: 0/19 recall on paraphrased attacks). This is a research finding,
   not a code vulnerability, but it means the module must not be presented as protection.
3. **One rule defect found and fixed:** modal prohibitions ("must never read credentials") were
   flagged as secret access. Suppression extended and covered by a test.
4. **One adjudication defect found and fixed:** claims with exception/condition clauses were
   refuted from set complement. They now defer.

## Not done

No adversarial testing of the Seatbelt profile itself was performed in this sprint; the existing
sandbox tests were relied on and still pass. No fuzzing of the regexes, no red-team corpus, no
measurement of judge behaviour on deferred claims.
