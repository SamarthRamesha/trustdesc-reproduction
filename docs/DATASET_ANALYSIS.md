# Dataset analysis and preparation

Audit continuation: original dataset/source evidence below is preserved. Fresh-copy preparation reproduces the original synthetic input/output hashes exactly; all eight labels remain null. Installed CLI fixture source is now bundled as inert package data, byte-identical to the original synthetic `tests/fixtures/server.py`; this is not another real-world dataset. See the [completion audit](PHASE1_COMPLETION_AUDIT.md) and [data availability guide](../data/README.md).

## What the original paper provides

The evaluation is an author-constructed task benchmark, not a supervised training dataset. Table 1 gives 12 server source links and counts totaling 52 tools; §5.1 describes 208 tasks (two from original and two from generated descriptions per tool). Exact selected tool IDs, commits, task strings, labels, source snapshots and raw traces were not obtained. There is no original train/validation/test split to reconstruct. See `paper_servers.json` and `paper_attacks.json` for source traceability and `EVIDENCE_LEDGER.md` for availability.

All 12 server names/categories/languages/stars/counts are transcribed from Table 1, not assumed current GitHub statistics. Language labels preserve the paper even where surprising. Original benchmark commit, license and selected-tool fields are **null**, not guessed. Those 12 manifests are metadata entries, not 52 usable observations. The seven attack links are an additional evaluation source, not substitutes for 208 task records.

Separately, `acquired_sources.json` records a current pinned arxiv-mcp-server snapshot (490,822 bytes, Apache-2.0, full commit/archive checksum). Static analysis inspected 31 Python files, found 19 exposed entries in its current list_tools (not the paper's exact four), and traversed a reviewed search-handler entry. The source archive/license were inspected without importing/executing any server code. This is one real-world **source acquisition**, not recovered task records; current revision match is unknown. Raw and transformed source stay excluded from Git/portable distribution. `reports/public_static_experiment.json` contains source hashes, counts and limitations; the other eleven servers were not downloaded.

## Included synthetic fixtures

`tests/fixtures/tasks.jsonl` contains eight newly authored tasks across two synthetic tool groups (`apply_formula`, `normalize_name`). The call implementations are our bounded fixture code; the static-analysis fixture file is inert source. No author observations, classifications or attack outcomes are implied. `label` is null in all eight records; it is reserved for explicitly documented dataset annotations and is not used to determine TSR. Verification replay decisions are separate engineering expectations, not collected truth labels. Provenance is recorded in every row; no personal/private data is present.

Fields: `id`, `server`, `tool`, `task`, `origin`, `source`, `commit`, `license`, `label`. Origin is synthetic/author_released/reconstructed. Non-synthetic rows require a pinned version identifier. License/source must be nonempty; an explicit unknown restriction must remain explicit and cannot be treated as redistribution permission. Extra or missing fields, invalid label types, duplicate IDs, conflicting duplicate annotations and empty datasets fail validation.

Preparation normalizes task whitespace, deduplicates identical server/tool/task content, preserves provenance/labels and writes input/output SHA-256, record/tool/server counts, missing-label counts and origin/split statistics. Default split is evaluation-only. Optional server-level seeded 70/15/15 grouping is **our extension** for later ML studies, requires at least three servers and prevents the same server leaking across splits; it does not eliminate semantic overlap across servers. No optional split was used for the paper comparison.

```sh
.venv/bin/python scripts/prepare_dataset.py tests/fixtures/tasks.jsonl --output data/processed/synthetic
```

Prepared data stays ignored; the validated small fixture manifest is copied into `reports/synthetic_dataset_manifest.json`. Raw source datasets/archives are ignored by Git. Public acquisition requires a specific HTTPS source on an allowlist, known checksum and license-review note; downloaded bytes remain quarantined and never execute/extract. ZIP inventory rejects traversal/symlinks and large expansions. Checksums identify bytes, not safety or ownership. When a hash is unknown, record it during a separate research review before acquisition rather than inventing an expected value.

## Original-benchmark recovery checklist

Recover an authenticated release or author clarification; record URL and exact revision. Obtain the 52-tool list and server commits, 208 original task texts, generated-description versions used to create tasks, original/full/lite metadata and human trace judgments. Audit licenses at those revisions. Validate IDs/counts and missing data, inspect task provenance and generated-task bias, and preserve the author's evaluation-only design. Acquire dependencies without executing server setup on the host. Only then plan isolated agent evaluation and manually review success criteria. Newly generated replacements must be marked reconstructed and cannot establish the exact published TSR.
