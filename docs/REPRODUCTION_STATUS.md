> Historical status document. The current Apple Silicon execution path is the root TRUSTDESC_REPRODUCTION.ipynb. Consult PROJECT_STATE.md and FINAL_PROJECT_COMPLETION_REPORT.md for current evidence and outstanding work. The historical record below is preserved.

# Reproduction status

Final Colab preparation adds a complete executable **available-workflow** notebook: [TRUSTDESC_FULL_REPRODUCTION](../notebooks/colab/TRUSTDESC_FULL_REPRODUCTION.ipynb), with [operator guide](COLAB_EXPERIMENT_GUIDE.md). It supports multiple tools/conditions/models, real core stages, explicit resources/profiles, condition-specific agent metadata, failure continuation, human review, safe checkpoint/resume and complete export. CPU fixture workflow runs now; live GPU/paid models depend on operator resources/access and were not run locally. Exact original benchmark/runtime/model reproduction remains blocked and is never inferred from notebook execution. Final validation: 119 tests pass on Python 3.13.9 and 3.11.14; all 19 notebook code cells compile and 18 noninteractive CPU cells execute. No further MacBook preparation step is requested.

Publication audit update: the original 91-test baseline was independently rechecked on Python 3.13.9 and 3.11.14. The current suite has 92 passing tests after a real installed-CLI fixture packaging fix. Earlier reports are preserved, not overwritten. See [completion audit](PHASE1_COMPLETION_AUDIT.md), [handover](PROJECT_HANDOVER.md) and [new validation evidence](../reports/publication_audit/updated_checks.json). Full scientific reproduction remains unestablished.

This project is an engineering baseline with documented blockers. **Original-condition scientific reproduction is not achieved.** “Implemented” below means working code for the stated scope, not verified parity with author artifacts.

| Component | Classification | Evidence | Gap |
|---|---|---|---|
| Paper understanding | Completed research analysis | All pages read, tables visually checked, 201 numeric reference entries | Original artifacts still missing |
| Resource discovery | Completed bounded investigation | Evidence ledger; interactive expiry response | Suggested artifact authenticity unverified; no authenticated alternate found |
| Python registration/reachability | Reimplemented with documented differences | AST DFS, aliases, caller/site capture, cycle and error tests | Paper's tree-sitter, full resolver semantics unavailable |
| TypeScript SliceMin | Not implemented | Explicit unsupported error | Needed for complete source-pool coverage |
| Dispatch/LLM entry fallback | Not implemented | Ambiguous/missing entry errors + reviewed override | No original fallback prompt; paper entry convention ambiguous |
| LLM call-context debloating | Implemented interface/mechanics; reasoning simulated locally | Per-node prompt, rewrites, graph rebuild, bounded passes, replay tests | Real LLM quality and equivalence not evaluated; no signature removal |
| Comment/docstring removal and 20-char normalization | Reimplemented with documented differences | Real AST/token transforms, collision rejection tests | Semantic effects of normalization not proven |
| Contextual identifier classifier and DescGen | Model-backed implementation; simulated locally | HTTP/local-model interfaces, strict validation, replay tests | Original prompts/models not executed; output truth not established by schema checks |
| DynVer planning/judge/filtering | Reimplemented with documented differences; model decisions simulated locally | Coverage validation, traces, claim filtering and full/lite integration | One-pass removal; no iterative free-form revision or formal schema certification |
| Controlled agent execution | Controlled synthetic experiment | Real execution of fixed project-authored tools | Replaces LangChain/MCP; not a sandbox |
| Real untrusted MCP execution | Blocked / disabled | DisabledRunner, sandbox review plan | Isolated backend not available/validated; source never run |
| Original 52-tool/208-task benchmark | Blocked by missing artifacts | Verified counts/source links and dataset gap report | Selected IDs/commits/tasks/labels not recovered |
| Data preparation | Implemented and validated on eight synthetic tasks | Checksums, validation, deduplication/statistics tests | Original author data not available; no fabricated labels |
| Public-source acquisition/static experiment | Completed bounded real-source analysis | One pinned Apache-2.0 arxiv source archive, 31 Python files, reviewed handler traversal | Current source has 19 exposed entries; unknown paper revision; 194 unresolved call sites; not full coverage |
| Paper evaluation metrics | Implemented for reviewed input | TSR and paired-overhead tests | Original reviewed task records not available |
| Local experiments | Completed synthetic engineering evidence | Repeated timing, allocation peaks, real fixture traces | No model-backed TSR, cost or attack-defense efficacy |
| Four original model settings | Not executed / blocked | Paper settings recorded; remote access gated | No cost authorization/credentials; four-GPU setup unavailable |
| Colab CPU handover | Prepared and portable workflow validated locally | Notebook compile + equivalent commands | Actual Colab session not connected/run |
| Optional small-model GPU track | Prepared, not run | Download gate/JSON parsing tests; compiled adapter/notebook | Dependencies/model/CUDA inference not validated in this Mac session |
| Capstone review and report | Completed within stated evidence bounds | Report, explanations, limitations, team contracts | No production trust-decision deployment |

## Completion interpretation

The user's deliverable definition explicitly permits a component implementation **or documented blocker**. This package supplies code, evidence and handover for feasible work and records missing original resources. It does not mark resource-dependent experiments complete, placeholders as working implementations, or a fixture execution as a successful paper reproduction. Remaining original-condition work is listed in PHASE1_REPORT and COLAB_HANDOVER. No research extension has an improvement claim.
