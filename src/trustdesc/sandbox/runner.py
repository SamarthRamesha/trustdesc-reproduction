from __future__ import annotations

import time
from typing import Protocol

from trustdesc.common.io import ValidationError, nonempty, require_fields
from trustdesc.common.models import ModelError
from trustdesc.descgen.prompts import AGENT
from .fixture_tools import SCHEMAS, invoke


class SandboxError(RuntimeError):
    pass


class Runner(Protocol):
    def run(self, task: str) -> dict: ...


class DisabledRunner:
    """Default for all unknown source. A subprocess is not a security boundary."""
    def run(self, task):
        return {'backend': 'disabled', 'status': 'blocked', 'events': [],
                'reason': 'Untrusted execution requires an independently validated isolated backend; none enabled.'}


class ControlledAgent:
    """Bounded model-planned loop over two trusted synthetic built-ins only.

    This exercises real fixture functions, but is NOT a sandbox and cannot load
    arbitrary tools. It replaces the paper's LangChain/MCP agent for safe tests.
    """
    def __init__(self, model, *, max_steps=6):
        if type(max_steps) is not int or not 1 <= max_steps <= 20:
            raise ValidationError('max_steps must be 1..20')
        self.model, self.max_steps = model, max_steps

    def run(self, task):
        nonempty(task, 'task')
        events = []
        start = time.perf_counter()
        try:
            for step in range(self.max_steps):
                action = self.model.complete('agent', AGENT,
                                             {'task': task, 'tools': SCHEMAS, 'observations': events, 'step': step})
                if action.get('action') == 'finish':
                    require_fields(action, {'action', 'answer'}, 'finish action')
                    nonempty(action['answer'], 'answer')
                    return {'backend': 'synthetic_allowlist', 'status': 'completed', 'events': events,
                            'answer': action['answer'], 'seconds': time.perf_counter() - start}
                require_fields(action, {'action', 'tool', 'arguments'}, 'call action')
                if action['action'] != 'call' or action['tool'] not in SCHEMAS:
                    raise SandboxError('Agent requested an unregistered tool')
                event = {'index': step, 'tool': action['tool'], 'arguments': action['arguments']}
                try:
                    event.update({'status': 'ok', 'result': invoke(action['tool'], action['arguments'])})
                except ValueError as exc:
                    event.update({'status': 'tool_error', 'error': str(exc)})
                events.append(event)
        except SandboxError as exc:
            return {'backend': 'synthetic_allowlist', 'status': 'blocked', 'events': events, 'reason': str(exc)}
        except (ValidationError, ModelError, TypeError, AttributeError) as exc:
            return {'backend': 'synthetic_allowlist', 'status': 'agent_error', 'events': events,
                    'reason': type(exc).__name__}
        return {'backend': 'synthetic_allowlist', 'status': 'step_limit', 'events': events,
                'reason': 'Maximum agent steps reached'}


def docker_review_plan(image_digest: str) -> list[str]:
    """Return a REVIEW-ONLY command, never execute/pull/build images.

    This plan alone neither validates isolation nor authorizes execution.
    An external backend also needs timeout + forced cleanup, capped logs,
    canary probes, immutable source binding and approved image provenance.
    """
    import re
    if not re.fullmatch(r'[a-zA-Z0-9./:_-]+@sha256:[0-9a-f]{64}', image_digest):
        raise ValidationError('A pinned registry image digest is required')
    return ['docker', 'run', '--rm', '--pull=never', '--network=none', '--read-only',
            '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=64',
            '--memory=512m', '--cpus=1', '--user=65534:65534',
            '--tmpfs=/tmp:rw,noexec,nosuid,size=64m', image_digest]
