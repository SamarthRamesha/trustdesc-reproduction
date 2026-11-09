# Known limitations

Generated 2026-11-09T14:24:22.101360+00:00.

| Limitation | Effect |
|---|---|
| Original artifact expired; no code/data release | exact 52-tool/208-task reproduction impossible |
| No recovered tasks, labels or traces | TSR, Q3, Q4, Q5 not computable |
| Current HEAD, not paper revisions | tool sets may differ from the evaluated snapshot |
| Deterministic prefix selection | tool identity differs from the authors' random sample |
| TypeScript/JavaScript unsupported | 22 of 52 tool slots not sliceable |
| Static-only slicing | over-approximate; external/class/reflection calls unresolved |
| No debloating applied | unreachable-branch removal not exercised on real tools |
| Third-party execution gated | DynVer cannot produce behavioural verdicts; pilot stops at planning |
| 4B local model | not equivalent to the paper's frontier models; valid-structure yield is low |
| 4096-token input cap in this pass | two tools rejected purely on slice size |
| Local weights unpriced | cost comparison impossible |
| Software tests ≠ research labels | 161 passing tests validate code, not accuracy |
