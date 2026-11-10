# Team handover

Everything below is the state of the repository **today** (commit noted at the end of
`PROJECT_STATE.md`). Read this before touching the code.

## What this project is, in plain language

TRUSTDESC is a research idea: instead of trusting a tool's marketing description, you
slice the tool's real source code, generate a description from that code, and then
*test* the claims in the description by running real tasks against the tool.

This repository is our independent implementation of that idea, plus an honest account of
how much of the original paper we could actually reproduce. The paper's own artifact was
taken offline, so we rebuilt the corpus from the 12 public MCP servers the paper names.

## The three stages

| Stage | What it does | Where the code is |
|---|---|---|
| **SliceMin** | Parses a tool's Python source and extracts the minimal set of functions reachable from the tool's entry point (plus call edges and unresolved calls). | `src/trustdesc/slicemin/`, `scripts/build_recovered_benchmark.py` |
| **DescGen** | Asks the local model to write a structured description (summary, functionalities, input schema, per-text claims) grounded in the slice, then validates it mechanically. | `src/trustdesc/descgen/`, `scripts/run_recovered_descgen.py` |
| **DynVer** | Turns the description into tasks, executes the real tool body inside an OS sandbox, and judges each claim against the recorded observation. | `src/trustdesc/dynver/`, `src/trustdesc/sandbox/seatbelt.py`, `scripts/run_dynver_recovered.py` |

## What is implemented and working

- **Corpus**: all 12 paper servers cloned at pinned commits, license recorded, provenance in
  `SOURCE_PROVENANCE.json`.
- **Slicing**: 30 Python tools sliced, every entry resolved (20 by registration pattern,
  10 by explicit qualified name). Slices are in `data/recovered_slices/`.
- **Description generation**: real local model (`Qwen3-4B-Instruct-2507-4bit`, MLX), 10 valid
  descriptions out of 28 attempts. Every rejection and raw response is preserved.
- **Sandboxed execution**: macOS Seatbelt boundary with deny-by-default policy, scratch-only
  writes, network denied, CPU/size/process limits and RSS supervision. Canary probes must pass
  before any external source runs.
- **DynVer experiment**: 18 tasks executed across 3 real tools × 3 description conditions.

## What is *not* done

- The paper's 52-tool / 208-task benchmark is **not** reproduced. Those files were never
  released and the anonymous artifact returns HTTP 410.
- 22 of the 52 tool slots are JavaScript/TypeScript and are **not** sliced.
- Only `arxiv-mcp-server` has an adapter shim layer, so only its tools can execute so far.
- No task success rate (TSR) is claimed anywhere. There are no original tasks or labels.

## Install and run (Apple Silicon, local only)

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-apple-lock.txt

# 1. tests
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -t .

# 2. corpus (needs the clones described in SOURCE_PROVENANCE.json)
PYTHONPATH=src .venv/bin/python scripts/discover_recovered_tools.py
PYTHONPATH=src .venv/bin/python scripts/build_recovered_benchmark.py

# 3. descriptions (resumable; appends to reports/recovered_descgen/run_state.json)
PYTHONPATH=src .venv/bin/python scripts/run_recovered_descgen.py --workspace reports/recovered_descgen

# 4. sandboxed verification (resumable)
PYTHONPATH=src .venv/bin/python scripts/run_dynver_recovered.py

# 5. reports
PYTHONPATH=src .venv/bin/python scripts/report_recovered_dataset.py
PYTHONPATH=src .venv/bin/python scripts/report_recovered_experiments.py
PYTHONPATH=src .venv/bin/python scripts/report_dynver.py
PYTHONPATH=src .venv/bin/python scripts/report_final.py
```

The notebook `TRUSTDESC_REPRODUCTION.ipynb` runs the same stages on a local kernel; its last
cell is the recovered-corpus driver.

## Where the evidence lives

| Path | Contents |
|---|---|
| `reports/recovered_descgen/run_state.json` | Per-tool result, status, error diagnostics |
| `reports/recovered_descgen/model_calls.json` | Every prompt, raw reply, token count |
| `reports/recovered_descgen/drafts/` | Latest draft per tool |
| `reports/dynver_recovered/results.json` | Every executed task: verdict, observation, policy hash |
| `reports/dynver_recovered/run_state.json` | Resumable checkpoint for DynVer |
| `reports/pilot_3tools/pilot.json` | Three conditions per pilot tool |
| `reports/FINAL_EXPERIMENT_RESULTS.{json,csv}` | Machine-readable summary |
| `reports/DYNVER_REPORT.md` | Sandboxed execution report |
| `reports/KNOWN_LIMITATIONS.md` | Everything we cannot claim |

## How to resume interrupted runs

Both long runs append to a state file after **every** tool or task:

- DescGen: re-running `run_recovered_descgen.py --workspace reports/recovered_descgen`
  continues; completed records are kept, nothing is regenerated.
- DynVer: `run_dynver_recovered.py` skips any `(tool, condition, task)` already in
  `reports/dynver_recovered/run_state.json`.

If a run dies mid-write, the state file is still valid JSON because each write is a full
dump of the accumulated state.

## What can legitimately be presented at review

Say this:

- We independently implemented all three TRUSTDESC stages and ran them on real recovered
  MCP tool source.
- Slicing covered 30/30 Python tools of the 12 named servers; 22 JS/TS slots are out of scope.
- Real local-model generation produced 10 valid structured descriptions out of 28 attempts,
  with every failure preserved.
- Sandboxed execution produced 18 real observations across three tools and three description
  conditions; each condition gave 4 supported and 2 refuted claims, so on this small task set
  the conditions did not separate.
- The paper's TSR, cost, quality-selection, TPA-blocking and adaptive-attack results are
  **not** reproduced and are never presented as ours.

Do not say we reproduced the paper's benchmark, and do not quote a task success rate.

## Remaining work, by teammate

| Task | Suggested owner | Starting point |
|---|---|---|
| TypeScript/JavaScript tool discovery and slicing (22 slots) | teammate comfortable with tree-sitter or ts-morph | `scripts/build_recovered_benchmark.py`, mirror the Python path in `src/trustdesc/slicemin/python.py` |
| Adapter shims for the remaining servers (excel, yfinance, wikipedia, paper-search, mysql, imagesorcery) | whoever wants the DynVer corpus to grow | copy the pattern in `src/trustdesc/dynver/recovered.py` (`SHIMS`) |
| Larger task sets per tool and a second judge model | experiment owner | `scripts/run_dynver_recovered.py` (`TASK_SYSTEM`, `JUDGE_SYSTEM`) |
| Statistical analysis of the DynVer verdicts | data owner | `reports/DYNVER_RESULTS.csv` |
| Author request for the original bundle | project lead | `MISSING_RESEARCH_MATERIALS.md` (message prepared, not sent) |
| Notebook polish and screenshots for the review | presentation owner | `TRUSTDESC_REPRODUCTION.ipynb` |

## Rules we followed and you should keep

- Never fabricate a record, label, trace or result.
- Label material as original / recovered / independently collected / reconstructed / synthetic.
- Preserve failed generations: they are evidence.
- Keep third-party source out of git; record commits and licenses instead.
