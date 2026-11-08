# Colab experiment report

Run: validation-run; fingerprint: ef1881ceb23c217feed1e7f19007882c39ffa6a824daa31f61ef98088112f9a2

**Not a complete scientific TRUSTDESC reproduction.** Conditions use the declared fixture/reconstructed/original-candidate provenance. Original paper values are not measurements here.

## Dataset and execution coverage

{
  "initial_tasks": 8,
  "effective_tasks": 8,
  "tools": 2,
  "origin_counts": {
    "synthetic": 8
  }
}

## Original / lite / full conditions

| Model | Condition | Total | Executed | Reviewed | TSR (%) | Mean latency (s) | Mean actual API cost (USD) |
|---|---|---:|---:|---:|---|---|---|
| replay | full | 8 | 8 | 0 | Not available / incomplete | 0.00340667 | 0 |
| replay | lite | 8 | 8 | 0 | Not available / incomplete | 0.00304553 | 0 |
| replay | original | 8 | 8 | 0 | Not available / incomplete | 0.00313081 | 0 |

TSR requires target invocation AND objective success, with complete human-reviewed eligible task coverage. Unreviewed predictions remain separate. Overheads use the three-way success intersection; unknown costs and zero baselines do not produce invented ratios. Replay has zero API billing but no model inference.

## Failures

{}

## Reproduction gaps

- Exact original implementation/52 selections/208 tasks/prompts/labels/model versions not recovered.
- No validated isolated external MCP/LangChain runtime; external execution blocked.
- Python subset only; no validated TypeScript or complete dynamic resolution.
- Replay measures software mechanics, not LLM efficacy. Alternative models are not paper models.
- TSR withheld until all eligible condition tasks have explicit human review; no model self-assessment used.
- Paper values are reference only; no numeric published-versus-measured difference is meaningful for fixtures.
- Actual Colab/GPU/model inference not validated by local notebook compilation.

## Plots

- {'plot': 'task_success', 'status': 'no_valid_measurements'}
- {'plot': 'latency', 'status': 'measured', 'path': 'plots/latency.png'}
- {'plot': 'cost', 'status': 'measured', 'path': 'plots/cost.png'}
- {'plot': 'per_tool', 'status': 'no_valid_measurements'}
- {'plot': 'model_comparison', 'status': 'no_valid_measurements'}
- {'plot': 'failures', 'status': 'no_recorded_failures'}
