# TEAM HANDOVER — TRUSTDESC reproduction

Written for someone who has never opened this repository. Read Sections A–F once, then
go straight to your workstream in Section G.

Last updated at commit `08bd497` (see `git log -1`). Figures: `reports/figures/`.
Numbers: `reports/STATISTICAL_RESULTS.json`. Honest limits: `reports/KNOWN_LIMITATIONS.md`.

---

## A. Executive overview

**The risk.** AI agents can call external tools through the Model Context Protocol (MCP).
The agent decides *whether* and *how* to call a tool by reading that tool's text
description. Whoever writes the description therefore shapes the agent's behaviour. A
malicious or careless author can describe a harmless-sounding tool that quietly does
something else — exfiltrate a file, delete data, call out to the network. Nothing in the
protocol verifies that a description matches the implementation.

**The paper's proposal.** TRUSTDESC (Ye et al., arXiv:2604.07536) proposes to stop trusting
prose and instead (1) extract the *actual code* a tool executes, (2) generate a description
from that code, and (3) *execute* the tool to check the generated claims against real
behaviour.

**What we built.** An independent implementation of those three stages — SliceMin, DescGen,
DynVer — plus the harness needed to run it on real public MCP servers, because the paper's
own artifact is gone (HTTP 410, no archived copy, no author release).

**Where it stands today.**

| Area | State |
|---|---|
| Corpus | 12/12 paper-named servers at pinned commits; 30/30 Python tool slots sliced |
| DescGen | working with local 4-bit Qwen3-4B; 10 valid descriptions from 28 attempts |
| DynVer | real sandboxed execution; 18 units across 3 tools and 3 conditions |
| Result | 12 supported / 6 refuted claims; the three conditions did **not** separate |
| Not done | 22 JS/TS slots, shims for 5 other servers, the paper's 208-task benchmark |
| Tests | 165 automated tests passing |

**Positioning sentence, use it verbatim:**
"We implemented a bounded reproduction of the three-stage TRUSTDESC framework, evaluated it
using recovered real-world MCP tool source, and conducted an initial three-condition
behavioural comparison. The observed pilot results did not distinguish the conditions, and
we identified the coverage and benchmark limitations that motivate further work."

This is **not** an exact or complete reproduction of the paper.

---

## B. Implementation

```
src/trustdesc/
  slicemin/python.py      static analysis, entry resolution, slice extraction
  slicemin/research.py    slice metrics (functions, edges, unresolved calls)
  descgen/generate.py     prompt construction, model calls, validation
  descgen/prompts.py      the two prompt templates
  descgen/sanitize.py     identifier normalisation (source of 7 rejections)
  dynver/verify.py        claim -> task -> verdict orchestration
  dynver/recovered.py     adapter shims + import stripping + sandbox wrapper  ← new
  sandbox/seatbelt.py     macOS sandbox-exec policy, execution, resource limits
  sandbox/runner.py       generic process runner
  pipeline.py             stage wiring used by the CLI
  cli.py                  `python -m trustdesc ...`
```

### SliceMin (`src/trustdesc/slicemin/python.py`)

Parses a recovered Python file with `ast`, finds the tool entry point, then walks the call
graph to collect every function the tool can reach, including transitive helpers, and
records unresolved calls (names it could not bind statically).

Entry resolution handles two real-world patterns found across the 12 servers:

1. **Registration decorator** — `@tools.destroyer` / `@mcp.tool()` style, where the exposed
   name is passed to a registry. 20 of 30 tools use this.
2. **Explicit qualified name** — a module-level function referenced by string. 10 of 30.

Output per tool: `data/recovered_slices/<server>__<tool>.json` with the slice source, entry
name, function list and a SHA-256 of the slice. 146 functions and 162 call edges in total;
886 calls stayed unresolved.

### DescGen (`src/trustdesc/descgen/`)

Sends the slice (capped at 4096 tokens) to a local MLX model and asks for structured JSON:
`summary`, `functionalities`, `input_schema`, and a list of **claims** — short, checkable
statements about behaviour. Temperature 0.2, seed 42, 1600 new tokens, 90-second deadline.
A rejection is recorded, not silently retried into a different configuration: two attempts
per tool maximum, both preserved with raw text in `reports/recovered_descgen/model_calls.json`.

Validation is mechanical: schema shape, argument names against the real signature, and
identifier normalisation. Valid output carries 6–11 claims (88 claims total).

### DynVer (`src/trustdesc/dynver/`)

Turns claims into executable tasks, runs the tool body in a sandbox, and judges each
observation. Two verdict paths:

1. **Deterministic rule first** (`verdict_for` in `recovered.py`): a crashed process, a
   timeout, a non-`ok` observation or a shim-dependent result can only be `refuted` or
   `inconclusive`.
2. **Model judge** only when the observation is `ok`: the judge sees the claim, the task,
   and the recorded output, and answers supported / refuted with a reason.

Crucially, `verdict_for` returns `inconclusive` whenever a claim's truth depends on a
shimmed adapter, so no shimmed path can be reported as `supported`.

### Seatbelt isolation (`src/trustdesc/sandbox/seatbelt.py`)

Every execution runs under `sandbox-exec` with a deny-by-default profile:

- read: only the interpreter, the standard library, explicitly permitted dependency
  directories, and the scratch directory;
- write: scratch only;
- network: denied;
- child processes: denied;
- limits: CPU time, file size, open files, plus RSS supervision from the parent.

Before any third-party source runs, `SeatbeltPython.probe()` exercises four canaries — read
outside, write outside, network connect, spawn child — and requires all four to be denied.
`scripts/run_dynver_recovered.py` refuses to run if the probe fails. The policy hash is
stored with every result so a change in isolation is visible in the evidence.

Two modes: `isolated=True` adds `-S` (no site-packages); `isolated=False` keeps site
packages but exposes only the dependency directory the tool actually needs, passed as an
explicit `extra_reads` entry.

### Adapter shims (`src/trustdesc/dynver/recovered.py`)

Recovered tools are thin adapters over SDKs (`mcp`, `python-dateutil`, `openpyxl`, …). To run
the **real tool body** without pulling in a transport, the harness:

1. strips module-level imports (`strip_imports`),
2. prepends an explicit shim preamble (`SHIMS` / `ARXIV_SHIMS`) that supplies the few names
   the body needs, with network helpers that raise by design,
3. injects a wrapper that installs resource limits, runs the async handler, normalises
   `TextContent` results, and snapshots any files the tool created.

The body itself is never rewritten. `tests/unit/test_recovered_dynver.py` asserts that.

### Experiment runner (`scripts/run_dynver_recovered.py`)

For each (tool, condition, task) it builds and runs the module and appends a full record to
`reports/dynver_recovered/run_state.json`: verdict, reason, seconds, process status,
returncode, observation, sandbox policy hash. Re-running skips completed units.

---

## C. Dataset

| Fact | Value | Where |
|---|---|---|
| Servers recovered | 12 / 12 paper-named | `data/manifests/recovered_benchmark.json`, `SOURCE_PROVENANCE.json` |
| Pinned revisions | one commit per server, recorded | same |
| Licenses | per server | `DATASET_LICENSES.md` |
| Python tool slots | 30 selected, 30 sliced | `data/recovered_slices/` |
| JS/TS slots | 22, **not sliced** | coverage block in the manifest |
| Original paper tasks | 0 recovered | `MISSING_RESEARCH_MATERIALS.md`, `reports/original_dataset/artifact_probe.json` |
| Selection policy | deterministic prefix of static discovery order | manifest `selection_policy` |

Why a deterministic prefix: the paper's sampling seed was never released. Choosing "the
first N in discovery order" is reproducible and disclosable; a random sample would pretend
to a randomness we cannot reproduce.

The 22 unsupported slots belong to five servers whose tools are TypeScript/JavaScript
(`markdownify-mcp`, `filesystem`, `context7`, `travel-planner-mcp`, `healthcare-mcp`).
They are excluded, never estimated.

---

## D. Experimental results

| Measurement | Value | Interval / note |
|---|---|---|
| Description yield | 10 / 28 = 35.7% | Wilson 95% 20.7–54.2% |
| Rejections: deadline | 8 | 44.4% of rejections |
| Rejections: identifier normalisation | 7 | 38.9% |
| Rejections: input over cap | 2 | 11.1% |
| Rejections: schema/arguments | 1 | 5.6% |
| Claims generated | 88 | 6–11 per description, median 8 |
| Sandboxed executions | 18 | 3 tools × 3 conditions × 2 tasks |
| Supported / refuted | 12 / 6 | 0 inconclusive |
| Per condition | 4 / 2 each | Wilson 95% 30.0–90.3% per condition |
| Execution time | median 11.2 s | 206.5 s total |
| Isolation probe | passed | 4 canaries denied |
| Task success rate | **not computed** | paper benchmark unavailable |

Per tool: `watch_topic` 5/6 supported, `list_watches` 5/6, `unwatch_topic` 2/6.

**The null result.** All three conditions gave 4 supported / 2 refuted. But the conditions
generated *different tasks* (`tasks_identical_across_conditions: false`), so this is not a
paired comparison and no test is reported. Identical counts are not evidence of equivalence:
with 6 units per condition, a 20-point true difference is compatible with these data.

**The one signal worth following.** Four of the six refutations are `unwatch_topic`
reporting `Watch not found` where even the developer's own description implies a successful
deletion. That is a genuine description/behaviour gap of exactly the kind the method
targets — but it rests on one tool.

Figures: `reports/figures/FIGURE_INDEX.md` (8 figures, 300 DPI PNG + PDF, source CSVs in
`figure_data/`). Analysis: `reports/STATISTICAL_ANALYSIS.md`,
`reports/EXPERIMENTAL_FINDINGS.md`.

### New experiments (2026-11-10)

Run after the checkpoint and reported separately, never merged with the pilot:

- **Matched-task comparison** — six authored tasks, one execution each, the same observation
  judged against all three descriptions. Three tasks are invalid (the sandbox creates a fresh
  temporary directory per execution, so setup state cannot persist) and are excluded. On the
  three valid tasks all conditions are 3/3 consistent: no separation.
- **Synthetic poisoning detection** — 12 authored cases in four categories, run through the
  implemented path. TP 5, FN 1, TN 3, FP 0 over 9 eligible cases; the 3 injection cases are
  `unsupported` because the pipeline has no injection detector. The single false negative is
  a negation-phrasing judge defect with its recorded reason quoted in the report.

Details and reproduction commands: `reports/NEW_EXPERIMENT_RESULTS.md`. Scripts:
`scripts/run_new_experiments.py`, `scripts/analyze_new_experiments.py`.

### Negation layer and injection screen (2026-11-10)

- **Negation-aware claim layer** (`src/trustdesc/dynver/negation.py`): deterministic adjudication
  of file-existence claims, in front of the model. On the recorded evidence it changes exactly one
  verdict — the inverted S1 claim — moving eligible detection from 5/6 to 6/6 with no new false
  positive. Double negatives, ambiguous wording and missing evidence return `inconclusive`. 15
  tests. Report: `reports/JUDGE_RELIABILITY.md`.
- **Static injection screen** (`src/trustdesc/injection_detector.py`): five explainable regex
  rules over inert description text; **not wired into the pipeline** and not a defence. TP 12,
  FP 0, TN 8, FN 0 on 20 self-authored synthetic cases; 3 ambiguous excluded; perfect score is a
  design-consistency check, not a detection estimate. Report:
  `reports/INJECTION_DETECTION_EXPERIMENT.md`.
- Re-run both analyses with `.venv/bin/python scripts/analyze_final_experiments.py` (recorded
  evidence only; no executions, no model calls).

---

## E. Repository map

```
src/trustdesc/            implementation (see B)
scripts/                  every runnable entry point
  discover_recovered_tools.py    scan clones for tool candidates
  build_recovered_benchmark.py   select + slice + write manifest
  run_recovered_descgen.py       DescGen, resumable
  run_dynver_recovered.py        DynVer, resumable, refuses without isolation probe
  report_recovered_dataset.py    coverage report
  report_recovered_experiments.py DescGen report
  report_dynver.py               DynVer report
  report_final.py                final results JSON/CSV
  generate_figures.py            all 8 figures + figure_data
  analyze_statistics.py          STATISTICAL_RESULTS.json/csv
  package_project.py             build handover zip from a clean tree
  validate_package.py            verify member hashes
data/
  raw/recovered/<server>/  third-party clones (not committed)
  recovered_slices/        one JSON slice per tool
  manifests/               benchmark manifest + provenance
reports/                   evidence, figures, analysis (committed)
tests/                     unit + integration; 165 tests
TRUSTDESC_REPRODUCTION.ipynb   notebook walkthrough
```

---

## F. Setup and commands (macOS Apple Silicon)

```sh
cd <repo root>
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-apple-lock.txt
.venv/bin/python -m pip install matplotlib        # figures only
```

Run the tests (≈9 s, no model, no network):

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -t .
```

Rebuild corpus metadata (requires the clones listed in `SOURCE_PROVENANCE.json`):

```sh
PYTHONPATH=src .venv/bin/python scripts/discover_recovered_tools.py
PYTHONPATH=src .venv/bin/python scripts/build_recovered_benchmark.py
```

DescGen — **expensive** (≈56 min of model time). It resumes; do not restart it:

```sh
PYTHONPATH=src .venv/bin/python scripts/run_recovered_descgen.py --workspace reports/recovered_descgen
```

DynVer — resumes per unit, aborts if isolation fails:

```sh
PYTHONPATH=src .venv/bin/python scripts/run_dynver_recovered.py
```

Regenerate analysis artefacts (cheap, deterministic):

```sh
PYTHONPATH=src .venv/bin/python scripts/report_dynver.py
PYTHONPATH=src .venv/bin/python scripts/analyze_statistics.py
PYTHONPATH=src .venv/bin/python scripts/generate_figures.py
PYTHONPATH=src .venv/bin/python scripts/report_final.py
```

Package and verify:

```sh
git status --porcelain            # must be empty
PYTHONPATH=src .venv/bin/python scripts/package_project.py --output phase3_handover.zip
PYTHONPATH=src .venv/bin/python scripts/validate_package.py phase3_handover.zip
shasum -a 256 phase3_handover.zip
```

Notebook: `jupyter lab TRUSTDESC_REPRODUCTION.ipynb`, run cells top to bottom from the repo
root. See `reports/NOTEBOOK_VALIDATION.md` for what was actually executed.

**Do not** re-run DescGen or DynVer to "refresh" results; they cost time and would append
duplicate evidence.

---

## G. Four workstreams

No names are assigned. Pick one and own it.

### Person 1 — TypeScript / JavaScript support

- **Objective:** slice the 22 unsupported slots so coverage reflects the paper's language mix.
- **Start at:** `src/trustdesc/slicemin/python.py` (mirror its interface),
  `scripts/build_recovered_benchmark.py`, `data/manifests/recovered_benchmark.json`.
- **First commands:** `grep -rn "language" src/trustdesc/slicemin/`, then inspect one clone,
  e.g. `data/raw/recovered/markdownify-mcp/`.
- **Deliverables:** `slicemin/typescript.py`; manifest entries with `language: "typescript"`;
  ≥ 10 sliced TS tools; tests for entry resolution; updated figures 1 and 7.
- **Acceptance:** every TS slot either has a slice with a resolved entry, or is explicitly
  marked unsupported with a reason; no slot silently disappears; test suite still green.
- **Depends on:** nothing.
- **Risk:** TS decorators and framework registration differ from Python; budget time for
  two discovery patterns, as Python needed.
- **Order:** parse one file → resolve one entry → slice one tool → batch → tests → manifest.

### Person 2 — additional MCP adapters

- **Objective:** let DynVer execute more than `arxiv-mcp-server`.
- **Start at:** `src/trustdesc/dynver/recovered.py` (`SHIMS` dict), one server at a time.
- **First commands:** inspect `data/recovered_slices/mysql_mcp_server__execute_sql.json`,
  then add an entry to `SHIMS` and run one unit.
- **Deliverables:** shims for at least two more servers; per-server execution evidence in
  `reports/dynver_recovered/`; shim-dependency flagged on every affected unit.
- **Acceptance:** real tool body unmodified; instance for the tool available; **network
  helpers must raise**; Seatbelt probe still passes; results keep the policy hash.
- **Depends on:** installed packages for those tools (`openpyxl`, `mysql-connector-python`,
  `yfinance`, `opencv-python`). Install into the venv; do not vendor them.
- **Risk:** a shim that quietly performs real I/O would break the fail-closed rule. Any
  shim doing more than supplying types/constants is a design error.
- **Order:** arxiv → excel (stdlib-ish, `openpyxl`) → wikipedia (HTTP, needs a deliberate
  mock) → mysql → yfinance/imagesorcery.

### Person 3 — experimental expansion and statistics

- **Objective:** turn the pilot into something that can support a claim.
- **Start at:** `scripts/run_dynver_recovered.py` (`TASK_SYSTEM`, `JUDGE_SYSTEM`),
  `scripts/analyze_statistics.py`.
- **First commands:** `PYTHONPATH=src .venv/bin/python scripts/run_dynver_recovered.py`
  (confirm it resumes and produces no duplicates), then read `reports/STATISTICAL_RESULTS.json`.
- **Deliverables:** ≥ 10 tools per condition; **one shared task set per tool** so a paired
  test is legitimate; ≥ 90 units per condition; a second judge model; disagreement rate;
  a re-run of `analyze_statistics.py` with paired methods enabled.
- **Acceptance:** paired design documented; no test reported on unpaired cells; figures 3–5
  regenerated; conclusions section updated with what changed.
- **Depends on:** Person 2 (more executables), Person 1 (optional, more tools).
- **Risk:** the null result may persist. That is a finding, not a failure — report it.
- **Order:** shared task set → more tools → scale → second judge → statistics.

### Person 4 — generation yield, methodology and integration

- **Objective:** raise yield and keep the project honest and coherent.
- **Start at:** `src/trustdesc/descgen/sanitize.py` (7 rejections),
  `scripts/run_recovered_descgen.py` (90 s deadline, 4096-token cap), `METHODOLOGY.md`.
- **First commands:** read the 18 failures in `reports/recovered_descgen/run_state.json`,
  then re-run generation **into a new workspace** (`--workspace reports/descgen_v2`) so the
  historical run is preserved.
- **Deliverables:** relaxed identifier rules with tests; higher token cap with measured
  effect; a documented yield comparison; reconciled docs and figures; the author-materials
  request sent only with approval.
- **Acceptance:** old workspace untouched; new numbers traceable; every report agrees with
  `STATISTICAL_RESULTS.json`; `TEAM_HANDOVER.md` current.
- **Depends on:** nothing to start; integrate Persons 1–3 near the end.
- **Risk:** tuning against 28 slices risks overfitting the validator to this corpus. Report
  yield on held-out slices if time allows.
- **Order:** validator → dead-line policy → new run → numbers → docs → integration.

---

## H. Capstone review preparation

### 60-second explanation

"MCP tools are described in prose, and AI agents decide how to use them by reading that
prose. Nothing checks whether the prose is true. TRUSTDESC proposes extracting the code
behind a tool, generating a description from the code, and executing the tool to test the
claims. We implemented all three stages and ran them on 30 real Python tools recovered from
the paper's 12 named servers, because the original artifact is offline. Generation produced
10 valid descriptions from 28 attempts, and sandboxed execution produced 18 real claim
verdicts. The descriptions agreed with behaviour 12 times and disagreed 6 times, with four
of the disagreements concentrated on one tool whose behaviour contradicts even its own
developer text. Comparing developer descriptions against our generated ones showed no
difference at this sample size — which is what a pilot of this size can support."

### 3-minute technical explanation

1. **Recovery** — 12 servers cloned at pinned commits; paper artifact returns 410, so the
   corpus is `independently_collected` and labelled as such everywhere.
2. **SliceMin** — AST call-graph extraction from the tool entry point; two entry patterns
   cover all 30 Python slots; 146 functions, 162 edges, 886 unresolved calls.
3. **DescGen** — local 4-bit Qwen3-4B, structured JSON with per-claim text; mechanical
   validation; every rejection preserved. Yield 35.7%, dominated by our 90-second deadline
   and our own identifier validator.
4. **DynVer** — claims become tasks; tasks run inside `sandbox-exec` with deny-by-default,
   scratch-only writes, no network, resource limits; four isolation canaries must pass or
   the runner aborts. Deterministic rules decide verdicts; the model judge is used only on
   clean observations, and shim-dependent claims can never be `supported`.
5. **Results** — 18 units, 12 supported, 6 refuted. No separation between conditions, and
   the tasks differ across conditions, so no significance test is reported.
6. **Limits** — 22 JS/TS slots unsliced, one server shimmed, paper benchmark and metrics
   unreproduced, 6 units per condition.

### Demonstration sequence (5 minutes)

1. `git log --oneline -5` — show the evidence trail.
2. `open reports/figures/fig1_dataset_coverage.png` and `fig5_execution_coverage.png`.
3. `jq '.execution_backend, .isolation_probe' reports/dynver_recovered/results.json`.
4. Show one raw unit: verdict, seconds, observation text, policy hash.
5. Run the test suite live (≈9 s): `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -t .`
6. `open reports/figures/fig8_research_summary.png` — the ledger of what is and is not reproduced.

### Key findings to state

- Pipeline works end to end, unattended, resumable, auditable.
- Yield 35.7%; the dominant failure is our deadline, then our validator — both fixable.
- 12 supported / 6 refuted; refutations concentrate on `unwatch_topic`.
- Conditions did not separate; the design cannot yet detect a difference.

### Likely questions and defensible answers

| Question | Answer |
|---|---|
| "Did you reproduce the paper?" | No. We reproduced the *method* on our own corpus. The paper's tasks, labels and traces were never released and its artifact is offline. |
| "Why only 18 executions?" | Only one server had a fail-closed adapter shim, and each of its three tools yields 2 tasks per condition. Shims are the gating factor, not the sandbox. |
| "Isn't 4/2 vs 4/2 meaningless?" | Yes as inferential evidence, and we say so. It is a descriptive pilot result; we report no p-value. |
| "How do you know the sandbox held?" | Four canaries are attempted before every run and must all be denied; the runner aborts otherwise. Policy hash is stored per unit. |
| "Are the verdicts just the model's opinion?" | Deterministic rules gate them: crashed/timeout/non-ok/shim-dependent observations cannot be `supported`. The judge only sees clean observations. |
| "Is the corpus legitimate?" | Public servers, pinned commits, licenses recorded, third-party source not redistributed. |
| "What is the strongest result?" | That real description/behaviour gaps were found and localised — 4 of 6 refutations on one tool, against the developer's own text. |
| "What would you do with another month?" | Shared task sets, 10+ tools, 90 units per condition, second judge, TS slicing. |

### Claims that must not be made

- Any task success rate, any "TSR", any cost or latency comparison with the paper.
- "We reproduced the paper's benchmark" or "we validated TRUSTDESC".
- "Generated descriptions are better than developer descriptions" — not observed.
- "The sandbox is a VM / container" — it is a Seatbelt profile plus resource limits.
- "52 tools processed" — 30 Python tools were sliced; 22 slots are unsupported.
- "Statistically equivalent" — identical counts are not equivalence.
- "Attack resistance" or "poisoning mitigation" — no attack experiments were run.
