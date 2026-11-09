# Methodology

Independent reimplementation of TRUSTDESC (Ye, Zhang, Jia, Hu; arXiv:2604.07536v1). This document
states what was implemented, what was measured, and where it departs from the paper. `docs/METHODOLOGY.md`
holds the earlier stage-by-stage analysis; this file covers the full pipeline including the recovered
public-source track added in the current phase.

## 1. Research questions and what can be answered

| Paper question | Required input | Status here |
|---|---|---|
| Q1 description accuracy (TSR) | 208 authored tasks + 52 tools + human labels | **not answerable** — tasks/labels never released |
| Q2 generation cost | paid provider pricing | **not measured** — local weights only, unpriced |
| Q3 tool-quality selection | degraded tool variants + task set | **not answerable** — variants/tasks unreleased |
| Q4 TPA blocking | 7 attack fixtures with author outcomes | **not answerable** — fixtures unreleased |
| Q5 adaptive attacks | 15-iteration trajectory | **not answerable** — only fit statistics printed |

What *is* measured: static slicing coverage and real-model description generation on the paper's own
named public servers, plus the preserved authored-fixture software check.

## 2. Evidence taxonomy

Every record carries exactly one label:

- `original_paper_material` — text or numbers taken from the published PDF.
- `recovered_public_source` — third-party code cloned from the URL the paper names, pinned to a commit.
- `independently_collected` — our selection, ordering or measurement, not the authors'.
- `reconstructed` — derived from published information only.
- `synthetic` — authored for engineering checks.

Labels are never merged. Synthetic or independently collected results are never presented as the
paper's benchmark.

## 3. Pipeline

### 3.1 SliceMin (static, source never executed)

1. **Entry identification.** Four registration styles observed in the wild are handled statically:
   `@mcp.tool`/`@tool` (including `name=` overrides), custom registry decorators
   (`@tools.reader("Read range")`, name = function name), `Tool(name=...)` object literals inside
   `list_tools`, and nested factory closures (qualified `module:outer.inner`). Ten of thirty entries
   needed the explicit qualified form. The paper's LLM fallback for unmatched patterns is **not**
   implemented; unmatched tools are recorded as unresolved instead of guessed.
2. **Call graph.** Python AST DFS from the entry; callees resolved lexically, through import aliases,
   through statically named `self`/`cls` methods, and through single-assignment local aliases. External
   and unresolved calls are recorded, never expanded or invented.
3. **Slice.** Reachable functions plus conservatively retained module context. Class-level and
   reflection-based dispatch remain partial and are reported per slice.
4. **Debloating.** LLM-guided rewriting produces *proposals* only. Nothing is rewritten in the slice
   used for description, because no finite check proves semantic equivalence. Every slice records
   `mode: static_only_no_debloating`.

### 3.2 DescGen (grounded generation)

Input is the slice; comments and docstrings are removed; identifiers are normalized to ≤20 characters
with collision checks; an auxiliary model pass removes promotional identifier terms while preserving
behaviour-bearing strings. The description model receives the sanitized slice plus a signature-derived
schema template and must return summary, functionalities and input schema.

Claim bookkeeping is **mechanical**: each claim copies one generated prose field verbatim and points at
its path. This adds no semantic content; it makes DynVer able to address statements individually. The
generated schema is then checked against the entry signature (argument names, required flags, simple
types) and rejected on disagreement.

### 3.3 DynVer (behavioural verification)

Claims are classified as runtime-verifiable or not; verifiable claims become tasks executed by a
bounded agent; a separate judge reads the recorded observations (never the agent's prose) and returns
supported / refuted / inconclusive; refuted claims are removed and the description is re-tested.

For the **recovered third-party corpus this stage is blocked**: executing arbitrary MCP server code is
gated in this implementation and no validated isolated runner exists for these servers. The block is
recorded per run rather than replaced with a scripted stand-in.

## 4. Model configuration

One resident model at a time, Apple Silicon MLX, pinned immutable revision, verified asset hashes,
supervised worker with wall-clock and RSS limits, explicit unload.

| Setting | Value |
|---|---|
| Model | `mlx-community/Qwen3-4B-Instruct-2507-4bit` |
| Revision | `50d427756c6b1b2fe0c0a10f67fbda1fc8e82c1b` |
| Runtime | MLX 0.32.4 / MLX-LM 0.28.3, 4-bit weights |
| Temperature | 0.2 (the paper's setting; the delivered fixture configuration used 0.0), seed 42 |
| Input cap | 4096 tokens for this pass; slices above it are rejected, not truncated |
| Output cap | 1600 tokens |
| Qualification | arithmetic, structured JSON, exact tool action — must pass before any stage |

Substitutions relative to the paper: the paper used Claude-4.5-Sonnet, Gemini-3-Flash, GPT-5.2 and
gpt-oss-120b on four RTX PRO 6000 GPUs. A 4B model on a 16 GB laptop is **not** model-equivalent, and
results are not extrapolated to the paper's numbers.

## 5. Measurement definitions

- **Valid structured description** — output passes every structural validator (required fields, claim
  coverage, object schema, required subset) *and* the signature consistency check. Rejections are
  counted as failures, never repaired into a pass.
- **Sliced tool** — an entry was resolved and a non-empty slice was produced.
- **TSR** — not computed. No task set, no labels.

Failures are first-class results: raw model output, validator diagnostic, and timing are stored for
every rejected tool.

## 6. Reproducing this work

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-apple-lock.txt
.venv/bin/python -m unittest discover -s tests -t .          # software tests
.venv/bin/python scripts/discover_recovered_tools.py         # static inventory
.venv/bin/python scripts/build_recovered_benchmark.py        # discovery + slicing
.venv/bin/python scripts/run_recovered_descgen.py --workspace reports/recovered_descgen
.venv/bin/python scripts/report_recovered_dataset.py
.venv/bin/python scripts/report_recovered_experiments.py
```

The recovered clones live under ignored `data/raw/`; `data/manifests/recovered_benchmark.json` records
every commit, license line and slice hash so the corpus can be reconstructed.

## 7. Scientific integrity rules applied

- No original benchmark record, task, label or trace was invented.
- No scripted description was substituted for model output; failures stay failures.
- Software tests are reported as software validation, never as research accuracy.
- Paper numbers appear only as reference values under an explicit "not our measurement" label.
