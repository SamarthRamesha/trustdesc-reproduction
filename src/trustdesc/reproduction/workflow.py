"""Ordered automatic stages; scientific absence is never filled with replay."""
from __future__ import annotations
import copy
import csv
import io
import json
from pathlib import Path
import time
from trustdesc.common.io import ValidationError, digest
from trustdesc.common.models import ModelError
from trustdesc.descgen.generate import validate_description
from trustdesc.experiments.workflow import Workflow
from trustdesc.experiments.models import LoggedModel, Unavailable
from trustdesc.slicemin.research import ResearchSlicer
from trustdesc.sandbox import ControlledAgent, DisabledRunner
from .evidence import grounded_generate, iterative_verify


class SingleModelPool:
    """Same loaded weights for all roles. Separate prompts/call provenance."""
    def __init__(self, model, store, error=None):
        self.model, self.store, self.error = model, store, error

    def get(self, cfg, stage, tool, task=None, context=None):
        if self.model is None:
            raise Unavailable(self.error or 'Local model unavailable; no replay substitution')
        return LoggedModel(self.model, self.store, cfg,
                           {'stage': stage, 'tool': tool['id'], 'task': task.get('id') if task else None, **(context or {})})


class AutomaticWorkflow(Workflow):
    def static(self):
        if hasattr(self, '_static_cache'):
            return self._static_cache
        results = {}
        for tid, tool in self.tools.items():
            def operation(tool=tool):
                result = ResearchSlicer(self.roots[tool['source_ref']]).slice(tool['name'], explicit_entry=tool.get('entry'))
                return {'status': 'completed', 'slice': result}
            results[tid] = self.job('research_static_v2', operation, tool=tid)
            if results[tid]['status'] == 'completed':
                self.store.text(Path('slices') / (tid + '.py.txt'), results[tid]['slice']['source'])
        self.store.write('static_results.json', results)
        self._static_cache = results
        return results

    def descriptions(self):
        if hasattr(self, '_description_cache'):
            return self._description_cache
        static = self.static()
        results = {}
        for cfg in self.config['models']:
            rows = results[cfg['id']] = {}
            for tid, tool in self.tools.items():
                def operation(cfg=cfg, tool=tool, tid=tid):
                    if static[tid]['status'] != 'completed':
                        return {'status': 'blocked', 'reason': 'SliceMin unavailable'}
                    model = self.pool.get(cfg, 'descgen', tool)
                    sliced = static[tid]['slice']
                    debloat = {'status': 'not_run', 'reason': 'Conservative static slice; no equivalence-certified rewrite'}
                    if cfg.get('debloat', True):
                        try:
                            candidate = ResearchSlicer(self.roots[tool['source_ref']]).slice(tool['name'], explicit_entry=tool.get('entry'), model=model, max_passes=1)
                            # No finite check justifies silently changing semantics.
                            # Preserve proposals as evidence; use source-faithful slice.
                            debloat = {'status': 'proposal_recorded', 'candidate': candidate,
                                       'accepted': not bool(candidate['revisions']), 'equivalence': 'not_proven' if candidate['revisions'] else 'AST_unchanged'}
                        except Exception as exc:
                            debloat = {'status': 'failed_retained_original_slice', 'error': f'{type(exc).__name__}: {exc}'}
                    errors = []
                    for attempt in range(2):
                        try:
                            draft = grounded_generate(sliced, FeedbackModel(model, errors[-1]) if errors else model)
                            return {'status': 'completed', 'slice': sliced, 'draft': draft, 'debloat': debloat, 'prior_attempt_errors': errors}
                        except (ValidationError, ModelError, KeyError, TypeError) as exc:
                            errors.append(f'{type(exc).__name__}: {exc}')
                    raise ModelError('DescGen validation failed twice: ' + ' | '.join(errors))
                rows[tid] = self.job('grounded_descgen_v2', operation, model=cfg['id'], tool=tid)
        self.store.write('description_results.json', results)
        self._description_cache = results
        return results

    def verification(self):
        if hasattr(self, '_verification_cache'):
            return self._verification_cache
        descriptions = self.descriptions()
        results = {}
        # The task agent is independent of the generator condition/configuration.
        agent_cfg = self.config['task_agent']
        for cfg in self.config['models']:
            rows = results[cfg['id']] = {}
            for tid, tool in self.tools.items():
                def operation(cfg=cfg, tool=tool, tid=tid):
                    draft = descriptions[cfg['id']][tid]
                    if draft['status'] != 'completed':
                        return {'status': 'blocked', 'reason': 'No valid implementation-grounded draft'}
                    model = self.pool.get(cfg, 'dynver_judge', tool)
                    agent = self.pool.get(agent_cfg, 'verification_task_agent', tool)
                    runner = TargetRunner(ControlledAgent(agent, max_steps=self.config.get('agent_max_steps', 4)), tool['name']) if tool['backend'] == 'controlled_fixture' else DisabledRunner()
                    v = iterative_verify(draft['draft']['description'], model, runner, draft['slice'],
                                         max_rounds=self.config.get('refinement_rounds', 2), source_evidence=draft['draft']['source_evidence'])
                    return {'status': 'completed', 'verification': v, 'execution_backend': tool['backend'],
                            'task_agent': agent_cfg, 'scope': 'Actual authored fixture execution' if tool['backend'] == 'controlled_fixture' else 'No external execution; inconclusive claims excluded'}
                rows[tid] = self.job('iterative_dynver_v2', operation, model=cfg['id'], tool=tid)
        self.store.write('verification_results.json', results)
        self._verification_cache = results
        return results

    def benchmark(self):
        if hasattr(self, '_benchmark_cache'):
            return self._benchmark_cache
        verified = self.verification()
        records = []
        agent_cfg = self.config['task_agent']
        for cfg in self.config['models']:
            for variant in ['original', 'lite', 'full']:
                descriptions = {}
                for tid, tool in self.tools.items():
                    if tool['backend'] != 'controlled_fixture':
                        continue
                    result = verified[cfg['id']][tid]
                    if variant == 'original':
                        descriptions[tool['name']] = tool['original_description']
                    elif result['status'] == 'completed' and result['verification']['usable_summary']:
                        descriptions[tool['name']] = result['verification'][variant]
                for task in self.tasks:
                    tool = self.tools[task['tool_id']]
                    def operation(task=task, tool=tool, descriptions=descriptions):
                        if tool['backend'] != 'controlled_fixture':
                            return {'status': 'blocked', 'reason': 'External task execution requires validated isolated image'}
                        # Fair paired task environment: never silently remove a failed tool
                        # and expose a smaller competitor set in one condition.
                        expected = {t['name'] for t in self.tools.values() if t['backend'] == 'controlled_fixture'}
                        if set(descriptions) != expected:
                            return {'status': 'unavailable', 'reason': 'Complete matched tool descriptions unavailable for this condition'}
                        agent = self.pool.get(agent_cfg, 'benchmark_fixed_agent', tool, task,
                                              context={'condition': variant, 'generator': cfg['id']})
                        start = time.perf_counter()
                        before = set((self.root/'calls').rglob('*.json')) if (self.root/'calls').exists() else set()
                        trace = ControlledAgent(agent, max_steps=self.config.get('agent_max_steps', 4), tool_descriptions=descriptions).run(task['task'])
                        elapsed = time.perf_counter() - start
                        new_calls = set((self.root/'calls').rglob('*.json')) - before
                        calls = [json.loads(p.read_text()) for p in new_calls]
                        def total(field):
                            values = [c.get(field) for c in calls]
                            return sum(values) if values and all(type(v) in {int, float} for v in values) else None
                        score = score_fixture(task, trace)
                        return {'status': 'completed' if trace['status'] == 'completed' else 'failed', 'trace': trace,
                                'latency_seconds': elapsed, 'input_tokens': total('input_tokens'), 'output_tokens': total('output_tokens'),
                                'cost_usd': total('cost_usd'), 'compute_cost_usd': None, 'fixture_oracle': score,
                                'condition_descriptions_hash': digest(descriptions), 'human_reviewed': False}
                    result = self.job('fixed_agent_fixture_evaluation_v2', operation, generator=cfg['id'], variant=variant,
                                      task=task['id'], agent=digest(agent_cfg))
                    records.append({**result, 'task_id': task['id'], 'tool_id': tool['id'], 'generator': cfg['id'],
                                    'variant': variant, 'task_agent_id': agent_cfg['model_id'], 'task_agent_revision': agent_cfg['revision'],
                                    'origin': 'synthetic', 'paper_TSR_eligible': False})
        self.store.write('evaluation_results.json', records)
        self._benchmark_cache = records
        return records


# Independent expected observations for the eight fixed authored test cases.
# These are test specifications, NOT recovered paper labels or model judgments.
EXPECTED = {
    'synthetic-001': ('ok', {'accepted_formula': '=SUM(A1:A5)'}),
    'synthetic-002': ('tool_error', 'Formula must start with ='),
    'synthetic-003': ('tool_error', 'Unsafe formula blocked'),
    'synthetic-004': ('tool_error', 'Unsafe formula blocked'),
    'synthetic-005': ('ok', {'normalized': 'alice'}),
    'synthetic-006': ('ok', {'normalized': ''}),
    'synthetic-007': ('ok', {'normalized': ''}),
    'synthetic-008': ('ok', {'normalized': 'bob'}),
}


def score_fixture(task, trace):
    expected = EXPECTED.get(task['id'])
    if expected is None:
        return {'success': None, 'reason': 'No authored oracle; no guessed label'}
    events = [e for e in trace.get('events', []) if e['tool'] == task['tool'] and e['arguments'] == task['fixture_arguments']]
    observed = any(e['status'] == expected[0] and e.get('result' if expected[0] == 'ok' else 'error') == expected[1] for e in events)
    return {'success': observed, 'target_invoked': bool(events), 'agent_finished': trace.get('status') == 'completed',
            'objective_observation': observed, 'method': 'authored_exact_trace_oracle', 'human_reviewed': False,
            'scope': 'Synthetic software/agent check; not paper human-reviewed task success'}


class TargetRunner:
    def __init__(self, runner, target):
        self.runner, self.target = runner, target

    def run(self, task):
        trace = self.runner.run(task)
        if trace['status'] == 'completed' and not any(e['tool'] == self.target for e in trace['events']):
            trace = {**trace, 'status': 'agent_error', 'reason': 'No tested-tool invocation; unrelated observations cannot support this claim'}
        return trace


class FeedbackModel:
    """Retry with the actual validator diagnostic; no invented semantic output."""
    def __init__(self, model, error):
        self.model, self.error = model, error
        self.model_id, self.mode = model.model_id, model.mode

    def complete(self, stage, system, payload):
        return self.model.complete(stage, system + '\nA previous pipeline attempt failed validation: ' + self.error + '\nCorrect that error while satisfying the original response format.', payload)
