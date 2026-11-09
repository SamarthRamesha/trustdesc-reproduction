#!/usr/bin/env python3
"""Real local MLX DescGen over the independently recovered public tool slices.

No scripted semantic fallback: every description comes from the pinned local
model, and every raw call is preserved. Descriptions are unverified drafts; the
DynVer stage for third-party tool code remains blocked (see reports).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from trustdesc.common.io import ValidationError  # noqa: E402
from trustdesc.reproduction.backends import ManagedModel, qualify  # noqa: E402
from trustdesc.reproduction.evidence import grounded_generate  # noqa: E402
from trustdesc.reproduction.model import ModelError, RepairModel  # noqa: E402
from trustdesc.reproduction.workflow import FeedbackModel  # noqa: E402


def model_config():
    cfg = json.loads((ROOT / 'configs/reproduction.json').read_text())
    mlx = dict(cfg['models_by_hardware']['mlx'])
    mlx.update({k: v for k, v in cfg['model_settings'].items() if k != 'max_calls'})
    mlx['seed'] = cfg['seed']
    mlx['max_worker_rss_bytes'] = 5 * 1024 ** 3
    return mlx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--cache', type=Path, default=ROOT / 'model_cache')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--max-new-tokens', type=int, default=0,
                        help='override the configured output cap; recorded as a deviation')
    parser.add_argument('--skip-qualification', action='store_true')
    args = parser.parse_args()
    out = args.workspace
    out.mkdir(parents=True, exist_ok=True)

    manifest = json.loads((ROOT / 'data/manifests/recovered_benchmark.json').read_text())
    tools = [t for t in manifest['tools'] if t['slice_status'] == 'sliced']
    if args.limit:
        tools = tools[:args.limit]

    config = model_config()
    if args.max_new_tokens:
        config['max_new_tokens'] = args.max_new_tokens
    started = datetime.now(timezone.utc).isoformat()
    state = {'started_utc': started, 'stage': 'startup', 'model_config': config,
             'config_deviation': ({'field': 'max_new_tokens',
                                   'delivered_fixture_value': 1600,
                                   'reason': 'real multi-parameter tools exceeded the cap and truncated JSON'}
                                  if args.max_new_tokens else None),
             'tools_requested': len(tools), 'results': [], 'failures': [],
             'scope': 'independently collected public tool source; not the paper benchmark'}
    (out / 'run_state.json').write_text(json.dumps(state, indent=2) + '\n')

    native = ManagedModel(config, args.cache)
    # Same wrapping the delivered pipeline uses: one bounded JSON format repair,
    # never a scripted semantic substitute.
    model = RepairModel(native)
    try:
        (out / 'runtime.json').write_text(json.dumps(native.runtime, indent=2) + '\n')
        state['stage'] = 'qualification'
        qualification = qualify(native) if not args.skip_qualification else {'passed': None, 'skipped': True}
        (out / 'model_qualification.json').write_text(json.dumps(qualification, indent=2) + '\n')
        if qualification.get('passed') is False:
            raise SystemExit('Model qualification failed; DescGen not started')

        state['stage'] = 'description'
        for index, tool in enumerate(tools, 1):
            record = {'id': tool['id'], 'server': tool['server'], 'tool': tool['tool'],
                      'slice_sha256': tool['slice_sha256'], 'started_utc': datetime.now(timezone.utc).isoformat()}
            slice_path = None
            for candidate in (ROOT / 'data/recovered_slices').glob('*.json'):
                data = json.loads(candidate.read_text())
                if data.get('tool') == tool['tool'] and hashlib.sha256(data['source'].encode()).hexdigest() == tool['slice_sha256']:
                    slice_path = candidate
                    break
            if slice_path is None:
                record.update({'status': 'slice_missing'})
                state['failures'].append(record)
                state['results'].append(record)
                (out / 'run_state.json').write_text(json.dumps(state, indent=2) + '\n')
                continue
            slice_result = json.loads(slice_path.read_text())
            record['slice_file'] = slice_path.relative_to(ROOT).as_posix()
            began = time.perf_counter()
            try:
                # Delivered DescGen path: grounded generation with mechanical claim
                # bookkeeping, one retry carrying the real validator diagnostic.
                errors = []
                draft = None
                for _attempt in range(2):
                    try:
                        draft = grounded_generate(slice_result,
                                                  FeedbackModel(model, errors[-1]) if errors else model)
                        break
                    except (ValidationError, ModelError, KeyError, TypeError) as exc:
                        errors.append(f'{type(exc).__name__}: {exc}')
                if draft is None:
                    raise ModelError('DescGen validation failed twice: ' + ' | '.join(errors))
                record.update({'status': 'generated', 'seconds': round(time.perf_counter() - began, 2),
                               'description': draft['description'],
                               'claims': len(draft['description']['claims']),
                               'source_evidence': draft.get('source_evidence'),
                               'implementation_interface': draft.get('implementation_interface'),
                               'prompt_hash': draft['prompt_hash'],
                               'prior_attempt_errors': errors,
                               'claim_decomposition': draft.get('claim_decomposition')})
                (out / 'drafts' / (record['id'].replace('::', '__') + '.json')).parent.mkdir(exist_ok=True)
                (out / 'drafts' / (record['id'].replace('::', '__') + '.json')).write_text(
                    json.dumps(draft, indent=2) + '\n')
                state['results'].append(record)
            except Exception as exc:
                record.update({'status': 'failed', 'seconds': round(time.perf_counter() - began, 2),
                               'error_type': type(exc).__name__, 'error': str(exc)[:4000],
                               'traceback': traceback.format_exc()[-6000:]})
                state['failures'].append(record)
                state['results'].append(record)
                if not getattr(native, 'process', None) or not native.process.is_alive():
                    state['stage'] = 'aborted_worker_died'
                    (out / 'run_state.json').write_text(json.dumps(state, indent=2) + '\n')
                    break
            (out / 'run_state.json').write_text(json.dumps(state, indent=2) + '\n')
            print(f"[{index}/{len(tools)}] {record['id']}: {record['status']} {record.get('seconds')}s", flush=True)
        state['stage'] = 'finished' if state['stage'] != 'aborted_worker_died' else state['stage']
    finally:
        audit = list(getattr(model, 'audit', []))
        model.close()
        state['finished_utc'] = datetime.now(timezone.utc).isoformat()
        state['peak_worker_rss_bytes'] = getattr(native, 'peak_worker_rss_bytes', None)
        (out / 'run_state.json').write_text(json.dumps(state, indent=2) + '\n')
        (out / 'model_calls.json').write_text(json.dumps(audit, indent=2) + '\n')
    generated = sum(1 for r in state['results'] if r['status'] == 'generated')
    print(f"generated {generated}/{len(tools)}; failures {len(state['failures'])}")


if __name__ == '__main__':
    main()
