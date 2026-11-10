# DynVer: sandboxed execution on real recovered tools

Backend: **macOS Seatbelt** (`sandbox-exec`), deny-by-default policy, writes only to a per-run scratch directory, network denied, CPU/file-size/process limits, RSS supervision. Isolation canary probes passed on this machine before any source ran: `True`.

## Conditions and verdicts

| Condition | Supported | Refuted | Inconclusive | Total |
|---|---|---|---|---|
| original | 4 | 2 | 0 | 6 |
| full | 4 | 2 | 0 | 6 |
| lite | 4 | 2 | 0 | 6 |

## Measured outcome

Each of the three conditions produced the same split: 4/6 supported tasks. The descriptions differ, but on this three-tool slice the sandboxed tasks did not separate them. That is a null result, not a failing pipeline: it is the honest outcome of a small task set with a 4B task generator.

## How execution works

Recovered tool bodies are adapters over external SDKs, so the harness strips module-level imports and supplies explicit, recorded shims for the transport only (for `arxiv-mcp-server`, `mcp.types.TextContent`, `Settings` and the two network helpers that raise). Real `python-dateutil` code runs, the real body runs unmodified, and every observation is a real process result with captured stdout, stderr, exit status, peak RSS and a policy hash.

Claims that depend on a shimmed adapter are classified `inconclusive` by rule and never `supported`.

## Reproduce

```sh
.venv/bin/python scripts/run_dynver_recovered.py
.venv/bin/python scripts/report_dynver.py
```

State is appended after every unit, so an interrupted run resumes where it stopped.

## Limits

- Three tools, one server, 18 tasks total: `arxiv-mcp-server` subscription bookkeeping.
- Other servers need their own shim layer before they can run.
- This is not the paper’s 208-task benchmark and its TSR is not reproduced.
