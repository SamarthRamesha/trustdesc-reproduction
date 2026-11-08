# Data availability and acquisition

No original TRUSTDESC benchmark records are bundled. Original code, exact 52-tool selection, commits, 208 tasks and human success labels have not been recovered. Do not infer their availability from repository URLs or record counts.

| Resource | Location | Records / units | Provenance and suitability |
|---|---|---|---|
| Paper source pool | `manifests/paper_servers.json` | 12 metadata entries; selected counts total 52 | PDF Table 1 links/counts. Not executable source snapshots or selected tool IDs |
| Paper attack examples | `manifests/paper_attacks.json` | 7 source links / reported outcomes | PDF Table 7. Published outcomes, not our observations or task benchmark |
| Publication fingerprint | `manifests/paper_fingerprint.json` | One 17-page PDF fingerprint | arXiv v1 identity; private supplied PDF not redistributed |
| Acquired source record | `manifests/acquired_sources.json` | One pinned arxiv server | Public external tool source, Apache-2.0 checked; unknown match to paper revision |
| Synthetic tasks | `../tests/fixtures/tasks.jsonl` | 8 records; 2 tools/groups | Newly authored; all labels null. For engineering checks only |
| Synthetic model responses | `../src/trustdesc/fixtures.py` | One five-claim scenario with 4 executable tasks | Hand-authored replay; not author data or inference |
| Source fixture | `../tests/fixtures/server.py` and bundled identical package data | One static server fixture | Parsed as text; executed fixture functions are fixed authored built-ins |

Ignored `raw/`, `interim/` and `processed/` folders are local working data, not tracked distributions. One raw public archive was obtained locally; it is excluded from Git/ZIP along with extracted external source. Other source repositories and author tasks were not downloaded. See [dataset analysis](../docs/DATASET_ANALYSIS.md) and [audit](../docs/PHASE1_COMPLETION_AUDIT.md).

Prepare included tasks:

```sh
python scripts/prepare_dataset.py tests/fixtures/tasks.jsonl --output data/processed/synthetic
```

Expected: 8 records, 2 servers, 2 tools, 8 missing labels, 0 duplicate removals, evaluation-only split. Output normalization/checksums are deterministic; missing labels remain unknown. Optional server-group ML splitting is our extension and requires at least three servers; it is not applicable to these two groups or an original paper training split.

Reacquire the optional public source snapshot, after reviewing the manifest/license:

```sh
python scripts/acquire_artifact.py https://codeload.github.com/blazickjp/arxiv-mcp-server/zip/572e301bb3198962c025d5ed5e14becb86868daa --output data/raw/arxiv-public/snapshot.zip --sha256 933aaafd43e4e166caccbf5cc46fff0f52fdb3c733e58d03a5253b4ca4b12158 --license-note 'Apache-2.0; pinned public tool source; static inspection only' --inventory-zip
python scripts/run_public_static.py --archive data/raw/arxiv-public/snapshot.zip
```

Acquisition refuses overwrite, requires an independent expected checksum and allowlisted HTTPS host, and never executes the bytes. Public static analysis extracts inspected Python/license text only. Its resulting source has 19 tool-list entries, 23 traversed functions and 194 unresolved call sites in the saved experiment; this does not reconstruct the paper's four selected arxiv tools. Runtime/model timings are not deterministic. Network restrictions may require a normally network-enabled shell, not disabled security controls.
