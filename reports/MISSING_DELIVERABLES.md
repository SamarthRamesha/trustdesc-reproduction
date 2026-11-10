# Missing deliverables

What a complete reproduction of Ye et al. (arXiv:2604.07536) would contain but this
repository does not, and why. Nothing here is hidden in another document.

## Not recoverable with available materials

| Item | Why it is missing | Evidence |
|---|---|---|
| Paper task benchmark (208 tasks) | Never publicly released | `MISSING_RESEARCH_MATERIALS.md` |
| Ground-truth labels for those tasks | Never released | same |
| Author execution traces and prompts | Never released | same |
| Original artifact (52-tool bundle) | Anonymous URL returns HTTP 410 `repository_expired`; no archive copy; no author reply | `reports/original_dataset/artifact_probe.json` |
| Exact original tool revisions | Only the server names and repositories are public; the paper does not pin revisions for all of them | `SOURCE_PROVENANCE.json` |
| Reported task success rate | Cannot be computed without the tasks and labels | — |
| Cost and quality-selection curves | Depend on the paper's task set and model budget | — |
| Adaptive-attack / TPA-blocking results | No attack implementations or evaluation harness released | — |

## Not implemented in this project

| Item | Consequence | Owner |
|---|---|---|
| TypeScript / JavaScript slicing | 22 of the paper's tool slots are unrepresented | Person 1 in `TEAM_HANDOVER.md` |
| Adapter shims for 5 servers | Sliced tools from excel, mysql, yfinance, imagesorcery, wikipedia, paper-search cannot execute | Person 2 |
| Shared task set across conditions | The three-condition comparison is unpaired, so no paired test is valid | Person 3 |
| Second judge model and human adjudication | Verdicts rest on one 4B judge gated by deterministic rules | Person 3 |
| Statistical power (≥ 90 units/condition) | 6 units per condition; no inferential claim possible | Person 3 |
| Attack experiments | Nothing here speaks to poisoning resistance | out of scope for this checkpoint |

## Partially delivered

| Item | What exists | What is missing |
|---|---|---|
| Description generation | 10 valid descriptions, every rejection preserved | 18 tools still without a valid description; validator fixes identified but not applied |
| Behavioural verification | 18 sandboxed executions with full observations | coverage of only 3 tools; no file-system or network tools executed |
| Documentation | methodology, limits, provenance, handover, audit | no panel-ready slide deck; no recorded demo video |
| Notebook | 12 cells, fresh-kernel validated for 5 of 6 code cells | the recovered-corpus driver cell was neutralised during validation and was not executed in that kernel |

## Deliberately not produced

- Any chart of a task success rate, cost curve or attack success rate. Those quantities were
  never measured, and plotting them would be fabrication.
- Any significance test on the three-condition split. With 6 unpaired units per condition no
  test would be meaningful; `reports/STATISTICAL_ANALYSIS.md` explains which methods were
  rejected and why.
- An "equivalence" statement. Identical counts at this sample size are not equivalence.
