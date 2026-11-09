# Final project completion report

Status: working independent pipeline; original scientific reproduction INCOMPLETE.

Run identity: `automatic-93589e7e9672adf4a537`. Fingerprint: `1f199a7054d887162fbe7487fc9e0fdafb3b8185463eed302d6c8f6e42df2f32`.

Model status: loaded_real_local_model; inference mode: real_local_mlx_inference.

## Actual execution

| Condition | Observed / expected | Authored objectives achieved | Fixture rate |
|---|---|---|---|
| original | 8/8 | 6 | 75.0 |
| lite | 8/8 | 6 | 75.0 |
| full | 8/8 | 6 | 75.0 |

These are authored exact-trace objectives, not original paper TSR. Failed and missing attempts remain explicit. Repeated software-validation runs are not pooled as independent research samples.

## Validation and evidence

{
  "returncode": 0,
  "scope": "software tests, not research labels"
}

Read source_hashes.json, model_manifest.json, prompt_manifest.json, acquisition_report.json, raw calls, checkpoints and execution_traces.jsonl. The exporter checks required artifacts and member hashes. A package is a handover, not evidence of scientific completion.

## Implementation and remaining work

Python SliceMin, real model DescGen, source attribution, iterative DynVer, fixed-agent fixture evaluation, checkpoints and portable report export are implemented within their documented scope. Model substitutions, approximate static resolution and finite model-judged observations limit the claims.

- Original 52-tool/208-task release, labels, traces and exact prompts not recovered.
- Original generation models and fixed Gemini-3-Flash task agent replaced by explicitly named free local model.
- Python AST subset; TypeScript, unrestricted dynamic dispatch and proof of slicing equivalence unavailable.
- Full external MCP transport is gated by a validated immutable-image backend; the separate macOS boundary supports offline Python source observations only.
- Finite authored fixture observations and automated oracles do not establish original human-reviewed TSR.
- Q3 degraded-tool competition, Q4 seven original attacks and Q5 adaptive naming experiments lack authenticated experimental artifacts.

Git publication and wider project handover status are recorded by the delivery agent separately; this notebook does not push repositories or claim publication. Supplementary public-example observations, when run, are separate from the authored benchmark.

## Supplementary public study

{
  "status": "experiment_finished",
  "returncode": 0,
  "scope": "public SDK function body; separate from authored benchmark and original MCP transport",
  "conditions": [
    {
      "condition": "original",
      "expected": 4,
      "observed": 4,
      "successes": 4,
      "source_body_oracle_rate_percent": 100.0
    },
    {
      "condition": "lite",
      "expected": 4,
      "observed": 4,
      "successes": 4,
      "source_body_oracle_rate_percent": 100.0
    },
    {
      "condition": "full",
      "expected": 4,
      "observed": 4,
      "successes": 4,
      "source_body_oracle_rate_percent": 100.0
    }
  ]
}
