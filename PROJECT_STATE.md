# Project state

Updated 2026-11-09T14:27:56.676171+00:00.

## Current milestone

Recovered real MCP source integrated; SliceMin and real-model DescGen executed; bounded three-tool pilot delivered. Original quantitative reproduction remains impossible (authors released nothing; artifact expired).

## Completed

- 12/12 paper servers cloned at pinned commits with licenses and tree hashes.
- 30/30 Python tools sliced with resolved entries.
- 10 valid local-model descriptions from 28 attempts; all failures preserved with diagnostics.
- Pilot on 3 tools across original/full/lite; DynVer execution documented as blocked.
- 161 software tests pass; earlier evidence preserved unchanged.

## Last successful experiment

`reports/recovered_descgen/` (DescGen pass) and `reports/pilot_3tools/pilot.json` (pilot).

## Known blockers

Original tasks/labels/prompts unrecovered; TypeScript unsupported; third-party execution gated; 4B model limits structural yield.

## Next exact action

Resume the corpus pass with an extended input cap for the two size-rejected tools, or add TypeScript slicing; exact reproduction awaits the authors' bundle.
