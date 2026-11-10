# Phase 3 handover

Updated 2026-11-09T14:27:56.676171+00:00.

## What you receive

1. A working Apple Silicon pipeline (`src/trustdesc`) with SliceMin, DescGen and DynVer stages.
2. A recovered, provenance-tracked corpus of 12 real MCP servers and 30 sliced Python tools.
3. Real model-produced descriptions and every raw model call, including rejected outputs.
4. A bounded three-tool pilot across original/full/lite conditions.
5. Preserved earlier evidence: authored fixtures, public-example study, startup investigation.
6. Honest reports separating paper values, our measurements and unknowns.

## Reproduce

```sh
python3.11 -m venv .venv && .venv/bin/python -m pip install -r requirements-apple-lock.txt
.venv/bin/python -m unittest discover -s tests -t .
.venv/bin/python scripts/discover_recovered_tools.py
.venv/bin/python scripts/build_recovered_benchmark.py
.venv/bin/python scripts/run_recovered_descgen.py --workspace reports/recovered_descgen
.venv/bin/python scripts/run_pilot_3tools.py --no-plan
.venv/bin/python scripts/report_recovered_dataset.py
.venv/bin/python scripts/report_recovered_experiments.py
.venv/bin/python scripts/run_dynver_recovered.py
.venv/bin/python scripts/report_dynver.py
.venv/bin/python scripts/report_final.py
```

The recovered clones are not committed (third-party licenses); re-clone the URLs in `SOURCE_PROVENANCE.json` at the recorded commits to rebuild `data/raw/`.

## Recommended next steps

1. Add TypeScript parsing to reach the remaining 22 tool slots.
2. Build a validated isolated runner so DynVer can execute real tools.
3. Request the authors' bundle using the prepared message in `MISSING_RESEARCH_MATERIALS.md`.
4. Re-run with a larger model if a paid API is authorized.
