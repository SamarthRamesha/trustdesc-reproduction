# Evidence index

Existing evidence files are preserved in place. New publication checks are append-only under `publication_audit/`, avoiding replacement of the initial results.

| Evidence | Meaning |
|---|---|
| [PHASE1_REPORT.md](PHASE1_REPORT.md) | Initial Phase 1 technical report; historical 91-test baseline |
| [COMPARISON.md](COMPARISON.md) | Published versus measured separation; no original-condition measurements |
| [published_results.csv](published_results.csv) | 201 paper quantitative reference rows; measured/difference columns blank |
| [local_experiments.json](local_experiments.json) | 20 synthetic engineering timing/allocation repetitions; replay, no inference |
| [local_example/verification.json](local_example/verification.json) | Real safe fixture traces + simulated semantic decisions |
| [public_static_experiment.json](public_static_experiment.json) | One pinned real-source static check; external execution false |
| [synthetic_dataset_manifest.json](synthetic_dataset_manifest.json) | Eight synthetic task records with unknown labels preserved |
| [test_results.json](test_results.json) and [test_python311.txt](test_python311.txt) | Original 91-test validation, preserved |
| [notebook_validation.txt](notebook_validation.txt) | Original 10-cell compilation / 5 portable cells, no Colab/GPU execution |
| [publication audit](../docs/PHASE1_COMPLETION_AUDIT.md) | Independent rechecks, packaging defect/fix, latest validation and limits |

The initial `local_experiments.json` reports a dirty working tree at anchor `87c733b`. Audit recomputation against the preserved `e3de3bc` source reproduces its **source-content hash exactly**. Its time/allocation values remain measurements from that run, not numbers a fresh run should match bit-for-bit. The curated example is retained; repetitive raw runs are ignored and are not required to run the supported workflow.

Use source manifests/configuration/semantic observations to compare runs. Do not compare synthetic milliseconds to paper LLM latency or convert simulated decisions into attack-defense accuracy.
