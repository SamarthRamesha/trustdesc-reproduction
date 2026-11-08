from __future__ import annotations

from pathlib import Path
import time

from .common.io import dump, ValidationError
from .descgen import generate
from .dynver import verify
from .slicemin import PythonSlicer


def run_pipeline(source_root, tool, model, runner, output, *, debloat_model=None, explicit_entry=None):
    """Save each successful stage and failures for diagnosis; never import source."""
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValidationError('Pipeline output directory must be fresh to prevent stale evidence')
    state = {'tool': tool, 'status': 'running', 'stages': [], 'errors': []}
    start = time.perf_counter()
    try:
        sliced = PythonSlicer(source_root).slice(tool, explicit_entry=explicit_entry, model=debloat_model)
        dump(output / 'slice.json', sliced)
        state['stages'].append('SliceMin')
        generated = generate(sliced, model)
        dump(output / 'draft.json', generated)
        state['stages'].append('DescGen')
        verified = verify(generated['description'], model, runner)
        dump(output / 'verification.json', verified)
        state['stages'].append('DynVer')
        state['status'] = 'completed_with_reproduction_gaps'
        return verified
    except Exception as exc:
        state['status'] = 'failed'
        state['errors'].append({'type': type(exc).__name__, 'message': str(exc)})
        raise
    finally:
        state['seconds'] = time.perf_counter() - start
        dump(output / 'pipeline.json', state)
        dump(output / 'model_audit.json', getattr(model, 'audit', []))
        if debloat_model is not None and debloat_model is not model:
            dump(output / 'debloat_audit.json', getattr(debloat_model, 'audit', []))
