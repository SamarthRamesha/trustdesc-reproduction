# TRUSTDESC reproduction

Open [TRUSTDESC_REPRODUCTION.ipynb](TRUSTDESC_REPRODUCTION.ipynb) in local Jupyter on Apple Silicon and choose **Run All**. The notebook embeds and verifies its source, creates a local Python environment, installs pinned dependencies, tests Python startup, qualifies a real free quantized model, runs the pipeline, and exports `phase3_handover.zip` with evidence and checksums. Python 3.11 is recommended. No manual source uploads, API keys or cell edits are required. First use needs internet access for public packages, weights and references.

This is an independent implementation of [Ye et al., TRUSTDESC](https://arxiv.org/abs/2604.07536v1). **The original scientific reproduction remains incomplete:** authenticated original 52-tool/208-task identities, snapshots, task texts, prompts, labels and traces have not been recovered. Authored fixtures and public example observations are labeled separately and never presented as the paper's benchmark or TSR.

## Local execution

The primary path uses **MLX on Apple Silicon**, a pinned 4-bit Qwen3-4B-Instruct-2507 model, and one supervised model process. Current memory checks guard model selection, load and generation. Each model must pass arithmetic inference, structured-output and exact-action tests before research stages start. The task-agent model, revision and settings stay fixed across Original / lite / full.

The PyTorch adapter also supports MPS and CPU. Those adapters preserve explicit device selection and report unavailable hardware; they do not silently claim GPU execution. These are model substitutions relative to the paper. No paid inference is configured. Local API charges are zero; electricity and compute cost are not measured.

If working from a checkout, an optional terminal route is:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-apple.txt
.venv/bin/python scripts/run_local_reproduction.py --workspace trustdesc_local
```

Optional Colab entry points are preserved under [notebooks/colab](notebooks/colab). The historical automatic Colab notebook remains pinned to its historical validated source; the root notebook is now the self-contained local deliverable.

## Pipeline and evidence limits

| Stage | Available implementation | Limit |
|---|---|---|
| SliceMin | Import-free Python AST registration detection, cross-file reachability, aliases, nested calls, named self/cls methods, dispatcher patterns, source spans and hashes | Restricted Python resolver; TypeScript/reflection are not fully implemented. LLM rewrites are retained as unproven proposals. |
| DescGen | Real model generation, comment/docstring removal, 20-character normalization, contextual identifier filtering, source attribution, argument-schema checks, return/exception/mutation/side-effect syntax records | Static indications and source attribution do not prove entailment or absence of side effects. |
| DynVer | Generated tasks, bounded agent actions, actual tool observations, model judging, supported/refuted/inconclusive filtering, bounded corrections and retesting | Finite tests establish observed behavior only. Missing execution remains inconclusive. |
| Matched evaluation | Eight authored tasks over two pure authored tools; identical task agent across Original / lite / full; exact trace oracles | Authored fixture success is separate from original human-reviewed paper TSR. |
| External observations | macOS Seatbelt boundary with Python startup, private-read/write, network and process-denial probes; supplementary pinned public example function-body study | Offline Python source execution, not a full MCP transport. The Linux immutable-image MCP adapter stays separately gated. |

The public SDK example study, when executed, removes only the registration decorator from a pinned function and executes its unchanged signature/body under Seatbelt. Its manifest records that transformation, source Git blob, revision, license and scope. It is neither the complete external MCP server nor a paper-selected tool. No arbitrary downloaded setup script is executed on the host.

## Startup and failure recovery

[Python startup investigation](docs/PYTHON_STARTUP_INVESTIGATION.md) records the diagnosed pre-main dyld/libignition abort. The project's original Seatbelt policy denied `file-read-data /`. The narrow fix grants the root directory itself with `(literal "/")`, without recursive filesystem access. Both native Terminal and Codex passed their model-free startup checks and isolation canaries. Homebrew, SIP and system dyld caches were not changed.

Worker launch is blocked after a failed startup check. Generation has wall deadlines, RSS monitoring, explicit unload/termination and bounded protocol retries. Full tracebacks and raw model outputs are retained. An invalid or unavailable model never becomes scripted semantic replay. Failed checkpoints and historical runs are preserved.

Successful checkpoints are bound to code, source, dataset, prompts, model, configuration and runtime. Rerun unchanged inputs to reuse them; changed identities create another run. See [PROJECT_STATE.md](PROJECT_STATE.md) for the current milestone, last successful tests/experiments and next exact action.

## Outputs

The pipeline exports source slices, descriptions, source-to-claim records, verification tasks/decisions, execution traces, task comparisons, metrics and a graph; model/prompt/dataset/experiment manifests; environment/dependency records; seven research/handover reports; and a member-hash-verified ZIP. A generated ZIP never implies scientific completion. The final project report states exactly what was executed and what remains incomplete.

Model weights, caches, credentials, the private paper PDF and unrelated personal files are excluded. The pinned MIT public example retains its license. External datasets without redistribution permission are referenced by revision/hash rather than bundled.

## Validation

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -t .
python3 scripts/check_python_startup.py --context terminal --output startup-check.json
```

Tests are software validation, not experimental labels. Recorded real-model experiments and their limitations belong in the final completion report and preserved run manifests. Historical reports remain available under `reports/`; historical Colab instructions do not supersede the local notebook.
