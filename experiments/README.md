# Experiment layout

Canonical experiment configurations are in `../configs/`; duplicate empty `configs/` directories are unnecessary. Curated measured outputs live in `../reports/` and are indexed by its README. Raw generated runs are written to ignored `runs/<timestamp>/`; they are not source data and are excluded from Git and portable archives.

Supported local commands, from repository root:

```sh
python scripts/run_local_experiments.py
PYTHONPATH=src python -m trustdesc demo --output experiments/runs/fixture-001
```

`run_local_experiments.py` reads `configs/experiments.json`, executes twenty safe fixture/replay runs and persists stage files. It writes `reports/local_experiments.json` and `reports/local_example/`; to preserve earlier evidence, run experiments in a separate clone/copy and copy reviewed new evidence into a uniquely named directory. The completion audit follows that practice.

An optional downloaded public source is processed only through `scripts/run_public_static.py`; a separately opted-in GPU/model experiment uses `scripts/run_small_model.py`. Neither the original four-model benchmark nor real MCP/LangChain execution is available. No external source or model/API is invoked by the default fixture command.
