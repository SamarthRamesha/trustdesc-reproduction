# Validation scope and known limits

The automatic root notebook supersedes the previous upload/configuration notebook. The inspected baseline was clean main at e7270af. All historical results are retained.

## Verified locally

- The baseline's 119 unit/integration tests passed before editing.
- The expanded suite exercises source registration/resolution, shadowing, no source execution, schema/evidence rejection, refinement/retesting, fixed-agent evaluation, missing resources/models, invalid datasets, cache corruption/recovery, checkpoints/resume and ZIP integrity.
- Every Python cell in the primary notebook compiles. All ten code cells execute in order under an explicitly injected scripted **software-validation** model. That test calls the real authored fixture functions; its scripted planner/judge is not real inference or research efficacy.
- The complete notebook also executes the missing-model path, producing reports/ZIP with null research scores and no semantic replay substitution.
- Inference dependencies were installed in a fresh isolated workspace virtual environment: torch 2.9.0, transformers 4.57.1, huggingface-hub 0.36.0, safetensors 0.6.2, tokenizers 0.22.1 and numpy 2.2.6. `pip check` found no broken requirements. This environment is macOS CPU, not Linux CUDA/Colab.
- Actual free-model CPU smoke results and final test counts are recorded under reports/reproduction_delivery/. Inspect those records for successful and failed attempts; the first small-model attempts exposed invalid claim bookkeeping/source attribution, which motivated exact mechanical prose-to-claim records and simpler checked source references. No failures are represented as successes.

## Not validated here

No real Google Colab session, T4 inference, original paper model, paid API call or external MCP server execution has been performed. Container command construction and permission gating are tested, but daemon/image integration, timeout cleanup and adversarial isolation require real Linux Docker validation. The Python-capable probe image must already exist locally and bind its source revision/hash to an immutable digest; the adapter never pulls or builds unknown images. Default Colab records this unavailable boundary and does not execute external servers.

## Research incompleteness

The exact 52 selected tool identities/commits, 208 task texts, original prompts, reviewed labels, traces and complete configuration are not recovered/authenticated. The suggested anonymous artifact remains only a candidate reference until linkage/authenticity and usable contents are established. MCPTox/MCPSecBench/MCPCorpus are external datasets, not replacements mislabeled as original material. Only explicit authored fixture objectives have automatic oracles. Their rates are not paper TSR and are not a general tool-poisoning defense benchmark.

Python AST analysis is partial and differs from the authors' tree-sitter implementation. TypeScript, arbitrary dispatch, closures, reflection and external library behavior are not fully resolved. LLM debloat proposals are recorded but semantic changes without equivalence evidence are not accepted. Exact source references check attribution identity, not entailment. Model judges and finite tasks can miss behavior. Static signature checks do not certify every nested schema constraint, return type or side effect. The implementation does not certify absence of malware.

A successful engineering run still writes Phase 2 scientific status **INCOMPLETE**, with explicit outstanding evidence in the completion report and Phase 3 handover. Original Q3–Q5 degraded-tool/attack/adaptive experiments stay unmeasured. No original scores or labels are fabricated. GPU/CUDA compatibility, CPU model quality and execution time remain hardware-specific. Direct dependency pins plus a saved complete installed environment are provided; no universal cross-platform transitive lock or bitwise stochastic reproducibility is claimed.
