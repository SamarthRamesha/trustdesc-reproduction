"""Paper TSR and explicit paired-overhead aggregation; no automatic labels."""
from __future__ import annotations

from collections import defaultdict
import math
from statistics import mean

from trustdesc.common.io import ValidationError, nonempty

CONDITIONS = {'original', 'lite', 'full'}
COST_FIELDS = ['input_tokens', 'output_tokens', 'cost_usd', 'latency_seconds', 'tool_calls']


def validate(records):
    if not isinstance(records, list) or not records:
        raise ValidationError('Evaluation needs nonempty records')
    seen = set()
    for r in records:
        if not isinstance(r, dict):
            raise ValidationError('Evaluation records must be objects')
        for k in ['task_id', 'model', 'run_id']:
            nonempty(r.get(k), k)
        if r.get('variant') not in CONDITIONS:
            raise ValidationError('Unknown description condition')
        key = (r['run_id'], r['model'], r['variant'], r['task_id'])
        if key in seen:
            raise ValidationError('Duplicate evaluation result')
        seen.add(key)
        if r.get('reviewed') is not True or any(type(r.get(k)) is not bool for k in ['target_invoked', 'objective_achieved']):
            raise ValidationError('TSR requires explicit reviewed boolean labels; unknown is not failure')
        for k in COST_FIELDS:
            v = r.get(k)
            if v is not None and (type(v) not in {int, float} or not math.isfinite(v) or v < 0):
                raise ValidationError('Costs/latencies/tokens must be nonnegative finite numbers or null')
    return records


def success(record):
    return record['target_invoked'] and record['objective_achieved']


def summarize(records, expected_tasks=None):
    validate(records)
    grouped = defaultdict(list)
    for r in records:
        grouped[(r['run_id'], r['model'], r['variant'])].append(r)
    result = []
    for (run, model, variant), group in sorted(grouped.items()):
        if expected_tasks is not None and {r['task_id'] for r in group} != set(expected_tasks):
            raise ValidationError('Missing or extra tasks relative to evaluation manifest')
        n = sum(success(r) for r in group)
        result.append({'run_id': run, 'model': model, 'variant': variant,
                       'tasks': len(group), 'successful': n, 'TSR_percent': n/len(group)*100})
    return result


def overhead(records):
    validate(records)
    groups = defaultdict(dict)
    for r in records:
        groups[(r['run_id'], r['model'])][(r['task_id'], r['variant'])] = r
    result = []
    for (run, model), lookup in sorted(groups.items()):
        tasks = {key[0] for key in lookup}
        if any((t, v) not in lookup for t in tasks for v in CONDITIONS):
            raise ValidationError('Overhead requires matched original/lite/full task coverage')
        intersection = sorted(t for t in tasks if all(success(lookup[(t, v)]) for v in CONDITIONS))
        for variant in ['lite', 'full']:
            metrics = {}
            for field in COST_FIELDS:
                pairs = [(lookup[(t, 'original')].get(field), lookup[(t, variant)].get(field)) for t in intersection]
                if not pairs or any(a is None or b is None for a,b in pairs):
                    metrics[field] = None
                else:
                    baseline = mean(a for a,b in pairs)
                    metrics[field] = (mean(b for a,b in pairs)/baseline - 1)*100 if baseline else None
            result.append({'run_id': run, 'model': model, 'variant': variant, 'matched_successful_tasks': intersection,
                           'relative_percent': metrics,
                           'aggregation': 'ratio of arithmetic means on three-way success intersection; exact paper aggregation unspecified'})
    return result
