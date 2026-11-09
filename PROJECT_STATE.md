# Project state

Updated: 2026-11-09 (Asia/Kolkata).

## Current milestone
Native MLX pipeline executed; validate the repaired pipeline and complete notebook in a fresh Python environment, then package and publish.

## Completed
- User explicitly adopted the full implementation brief.
- Cloned existing history at b7a8c8b into an isolated workspace; baseline clean.
- Located historical CPU runs and the user's Desktop T4 handover ZIP; preserved originals.
- Confirmed primary notebook and LocalModel support only CPU/CUDA and need Mac support.
- Read baseline scientific status: original 52-tool/208-task benchmark is unavailable; recorded CPU and T4 runs have 0/24 completed authored attempts.

## Pending
- Diagnose historical CUDA error from actual records.
- Implement and validate memory-aware MLX/MPS/CPU backends and real model qualification.
- Audit and repair SliceMin, DescGen, DynVer and evaluation; run component/integration tests.
- Execute matched real local inference experiments, preserve provenance and checkpoints.
- Build local Run-all notebook and validate fresh environment.
- Generate reports, integrity-checked phase3_handover.zip, commit and push.

## Known blockers
- Original benchmark/prompts/labels not authenticated; investigate again, never invent them.
- Native hardware was validated with an authorized external-sandbox probe: Apple M3, 16 GiB; MLX GPU available. No unresolved native startup blocker.

## Last successful test
151 unit/integration tests pass. 23 Python-only Codex startup checks pass (10 inherited environment, 10 clean, 3 Seatbelt); all four isolation canaries pass. See reports/apple_recovery/startup_investigation/.

## Last successful experiment
Native run automatic-bfb7f182699c8cdf5b15: real MLX Qwen3-4B, SliceMin and grounded DescGen for two authored tools, iterative DynVer, 24 matched attempts. Original/lite/full each 6/8 (75%) exact authored objectives. No original-paper TSR. Public arXiv DescGen exceeded the initial 8192-token cap; retained as failed. See work/native-experiment and reports staged for delivery. Native archive/member validation passed.

## Next exact action
Finish the one-model public-example study, then run the self-contained notebook in the fresh environment. Validate all reports/ZIP hashes, record limitations, commit and push without force.

## Python startup incident (13:54:32 IST)
- Parent 5020 ran work/debug_seatbelt5.py; children 5022 and 5023 were print-only policy variants, not model workers.
- Kernel logs identify file-read-data / denial in both children before Python main.
- Minimal project fix: allow file-read-data on literal / only, and launch the canonical framework executable directly. Private descendant reads, outside writes, network and child processes remain denied by probes.
- Apple XNU xnu-12377.1.9 reason.h defines namespace 35 (0x23) as LIBIGNITION; code 2 not decoded without a verified definition.
- No Homebrew installation, SIP or system caches changed.
- No background qualification/debug/model worker remains.
- Native Terminal comparison completed from the generated result: TERM_PROGRAM=Apple_Terminal; 23/23 startup checks and all four canaries pass. Codex comparison also passes 23/23.

## User-confirmed native Terminal result
The user confirmed the native Terminal result on 2026-11-09. Proceed with MLX import/device detection, one monitored model process, strict structured/action qualification, then integration. Do not compare further models or load multiple models concurrently.

## Implemented since recovery
- MLX 4-bit backend; MPS/CPU adapter support; monitored worker RSS/wall limits, unload and startup gate.
- Missing .jinja model chat template diagnosed and repaired with hash verification/regression test.
- Qwen3-4B qualified on arithmetic, JSON structure and exact whitespace-preserving actions; about 1.9 GiB peak worker RSS in qualification. No further model comparison.
- First native run preserved; exception type now retained in tool traces after diagnosing an erroneous judge refutation.
- Primary local notebook embeds source, automatically creates/installs a fresh venv, and emits handover/report links. Fresh environment preflight passed; full inference validation pending.
- Pinned MIT public example source-body smoke: 4/4 sandboxed arithmetic cases pass. Separate real-model public study currently running from an immutable local source snapshot.
