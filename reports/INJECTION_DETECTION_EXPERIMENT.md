# Static injection screening experiment (2026-11-10)

An experimental, deterministic screen for prompt-injection-shaped text in tool descriptions. It
is a prototype and a *separate* signal from behavioural verification.

Files: `src/trustdesc/injection_detector.py`, `tests/test_injection_detector.py`,
`data/experiments/synthetic_injection_cases.json`, `reports/INJECTION_DETECTION_RESULTS.json`,
`reports/figures/fig12_injection_detection.png`.

## Status and scope

- **Implemented as an experimental extension, not wired into the pipeline.** Nothing in the
  verification path calls it, so no existing result changes.
- **Not a prompt-injection defence.** It is five regular-expression rules over inert text. A
  miss means only that none of these rules fired.
- It never executes, evaluates, fetches or follows anything it reads, and performs no network or
  file access.
- Kept separate from behavioural verification: a description can pass this screen and still be
  contradicted by an execution, and can be flagged here while behaving correctly.

## Dataset and labels

`data/experiments/synthetic_injection_cases.json` — 23 synthetic descriptions, labels and
rationales written by the author **before** the screen was run:

| Label | n | Composition |
|---|---|---|
| benign | 8 | ordinary descriptions plus deliberate near-misses: "Ignore case when comparing…", "does not read … credential files", "Passwords are not stored", "Do not modify files outside the data directory" |
| malicious | 12 | 9 authored in 4 attack shapes (override, concealment, secret access, out-of-scope shell) + 3 adversarial texts reused verbatim from the recorded poisoning run (`M-I1`, `M-I2`, `M-I3`) |
| ambiguous | 3 | defensively shaped text whose label is not certain ("Never reveal internal paths…", "Ignore malformed entries…", "Treat any instructions … as data") |

Ambiguous cases are reported separately and excluded from precision/recall/F1. Ground truth is
author labelling of synthetic text; there is no external injection corpus involved.

## Rules

| Rule | Fires on |
|---|---|
| INJ-OVERRIDE | "ignore/disregard/forget … previous/prior/above/system/developer … instructions/prompts/rules", "new system prompt", "you are now" |
| INJ-CONCEAL | "do not/never tell/inform/notify/mention/reveal … the user", "without telling the user", "hide … from the user", "silently", "secretly" |
| INJ-SECRET | read/cat/open/print/include/append/send/upload/post … `~/.ssh`, `id_rsa`, `.env`, credentials, passwords, API keys, secret files; send/upload … `http(s)://`; "contents of .env" |
| INJ-OUTOFSCOPE | `rm -rf`, `curl … \| sh`, `wget … \| sh`, `os.system`, `subprocess`, `eval(`, `base64 -d`, `chmod`, `sudo`, `python -c`, "delete every/all" |
| INJ-AUTHORITY | line-initial `system:`/`assistant:`/`developer:`, `<system>`/`<|im_start|>`, "developer mode" |

Each finding records the rule id, a one-line explanation and the matched excerpt, so every flag
can be checked by hand.

**Disclosed refinement:** the first smoke run flagged the benign sentence *"The tool does not
read environment variables or credential files."* A suppression was added for declarative
negations (`does/is/are/was/were/has/have/cannot … not` within 25 characters before the match).
Imperatives such as "do not tell the user" are deliberately **not** suppressed, because that is
the attack shape. Suppressed matches are recorded in the output, not silently dropped.

## Results (20 eligible cases)

| TP | FP | TN | FN |
|---|---|---|---|
| 12 | 0 | 8 | 0 |

Precision **12/12 = 100%**, recall **12/12 = 100%**, F1 **1.00**. Ambiguous: 3 cases, 0 flagged,
excluded from the metrics above. Rule counts: OVERRIDE 4, SECRET 4, OUTOFSCOPE 3, CONCEAL 2,
AUTHORITY 1 (one case can fire several).

## How much this result is worth

A perfect score on 20 self-authored cases is a **design-consistency check, not a detection
estimate**. The same author wrote the rules, the attack texts and the labels, so the set is
neither held out nor representative: no unseen-wording stress set, no real MCP description
corpus, no obfuscation (Base64, homoglyphs, other languages), no paraphrase testing. The 100%
figures should not be quoted as expected performance, and the ambiguous row shows the screen
cannot even assign a confident verdict to three mildly suspicious sentences.

## What is established / unproven

Established: a deterministic, explainable screen can be specified, implemented and tested; it
separates this synthetic labelled set without false alarms on its near-miss benign controls; it
leaves the behavioural pipeline untouched.

Unproven: detection on real or adversarial unseen descriptions; robustness to obfuscation;
whether a flagged description is actually unsafe; and any defensive value in deployment. The
prototype is not a prompt-injection defence and should not be described as one.
