# Run the local notebook

1. Open TRUSTDESC_REPRODUCTION.ipynb in local Jupyter on the Mac and choose Run All.
2. The notebook verifies its embedded source, creates a local Python environment, installs the pinned Apple dependency lock, and tests Python startup before loading a model.
3. Read the qualification and stage statuses. The same free quantized task agent is held fixed across Original / lite / full. Invalid model responses remain recorded failures.
4. Download phase3_handover.zip and its SHA-256 sidecar from the final cell. Read FINAL_PROJECT_COMPLETION_REPORT.md before interpreting the results.

No source uploads, API keys, configuration edits or manual human labels are required for the authored-fixture workflow. Rerun unchanged cells to reuse successful hash-bound checkpoints; changed code/model/runtime/source/configuration uses a new run identity. Local files persist until removed by the operator. Optional Colab entry points are retained under notebooks/colab; its disk is ephemeral.

Apple Silicon uses the qualified MLX model subject to memory constraints. MPS and CPU adapters are available with explicit device/substitution records. Original benchmark claims remain unavailable without authenticated tools/tasks/prompts/labels/traces. External execution requires a validated boundary; default fixture execution is not an untrusted-code sandbox.
