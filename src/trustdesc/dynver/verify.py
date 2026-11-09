from __future__ import annotations

import copy

from trustdesc.common.io import ValidationError, nonempty, require_fields
from trustdesc.descgen.generate import validate_description
from trustdesc.descgen.prompts import PLAN, JUDGE
from trustdesc.sandbox.runner import SandboxError


def validate_trace(trace):
    if not isinstance(trace, dict) or not isinstance(trace.get('events'), list):
        raise ValidationError('Malformed execution trace')
    if trace.get('status') not in {'completed', 'timeout', 'blocked', 'dependency_error', 'sandbox_error', 'agent_error', 'step_limit'}:
        raise ValidationError('Unknown trace status')
    nonempty(trace.get('backend'), 'trace backend')
    for e in trace['events']:
        if not isinstance(e, dict) or not isinstance(e.get('arguments'), dict) or not isinstance(e.get('tool'), str):
            raise ValidationError('Malformed trace event')
        if e.get('status') not in {'ok', 'tool_error'}:
            raise ValidationError('Unexpected execution event')
        if e['status'] == 'ok' and 'result' not in e:
            raise ValidationError('Missing observed tool result')
        if e['status'] == 'tool_error' and not isinstance(e.get('error'), str):
            raise ValidationError('Missing observed tool error')
    return trace


def filter_description(description, decisions):
    final = copy.deepcopy(description)
    supported = {d['claim_id'] for d in decisions if d['verdict'] == 'supported'}
    for c in description['claims']:
        if c['id'] in supported:
            continue
        parent = final
        for part in c['target'][:-1]:
            parent = parent[part]
        last = c['target'][-1]
        if isinstance(parent, list):
            parent[last] = None
        elif last == 'summary':
            parent[last] = ''
        else:
            parent.pop(last, None)
    old_indices = [i for i, v in enumerate(final['functionalities']) if v is not None]
    final['functionalities'] = [v for v in final['functionalities'] if v is not None]
    final['claims'] = [copy.deepcopy(c) for c in description['claims'] if c['id'] in supported]
    for c in final['claims']:
        if c['target'][0] == 'functionalities':
            c['target'][1] = old_indices.index(c['target'][1])
    return final


def verify(description, model, runner):
    validate_description(description)
    plan = model.complete('verification_plan', PLAN, {'description': description})
    require_fields(plan, {'tasks'}, 'verification plan')
    if not isinstance(plan['tasks'], list):
        raise ValidationError('Verification tasks must be a list')
    claims = {c['id']: c for c in description['claims']}
    tasks = {}
    for t in plan['tasks']:
        require_fields(t, {'claim_id', 'verifiable', 'task', 'reason'}, 'verification task')
        nonempty(t['claim_id'], 'task claim_id')
        if t['claim_id'] not in claims or t['claim_id'] in tasks or type(t['verifiable']) is not bool:
            raise ValidationError('Plan has duplicate/unknown claims or invalid verifiability')
        nonempty(t['reason'], 'task reason')
        if t['verifiable']:
            nonempty(t['task'], 'task objective')
        elif t['task'] is not None:
            raise ValidationError('Nonverifiable claims must have null task')
        tasks[t['claim_id']] = t
    if set(tasks) != set(claims):
        raise ValidationError('Verification plan omitted claims')
    decisions, traces = [], []
    for cid, claim in claims.items():
        task = tasks[cid]
        if not task['verifiable']:
            decisions.append({'claim_id': cid, 'verdict': 'not_runtime_verifiable', 'reason': task['reason']})
            continue
        try:
            trace = validate_trace(runner.run(task['task']))
        except (SandboxError, ValidationError, TimeoutError, ImportError) as exc:
            trace = {'backend': 'runner_failure', 'status': 'sandbox_error', 'events': [], 'reason': type(exc).__name__}
        traces.append({'claim_id': cid, 'task': task['task'], 'trace': trace})
        if trace['status'] != 'completed' or not trace['events']:
            decisions.append({'claim_id': cid, 'verdict': 'inconclusive',
                              'reason': f"No completed tool evidence: {trace['status']}"})
            continue
        judged = model.complete('judge', JUDGE, {'claim': claim, 'task': task['task'], 'execution': trace})
        require_fields(judged, {'verdict', 'reason'}, 'judge')
        if judged['verdict'] not in {'supported', 'refuted', 'inconclusive'}:
            raise ValidationError('Invalid judge verdict')
        nonempty(judged['reason'], 'judge reason')
        decisions.append({'claim_id': cid, **judged})
    full = filter_description(description, decisions)
    lite = {k: copy.deepcopy(v) for k, v in full.items() if k not in {'functionalities', 'claims'}}
    return {'full': full, 'lite': lite, 'decisions': decisions, 'traces': traces, 'plan': plan,
            'model': model.model_id, 'model_mode': model.mode,
            'status': 'synthetic_evidence_only' if any(t['trace']['backend'] == 'synthetic_allowlist' for t in traces) else 'requires_backend_validation',
            'usable_summary': bool(full['summary']), 'trust_decision': 'not_assessed',
            'limitations': ['Claims only supported on observed cases, not universally proven.',
                            'Structural schema fields are not separately dynamically certified.',
                            'Inconclusive/nonverifiable claims are excluded from supported output.',
                            'A new isolated execution backend must authenticate its own traces.']}
