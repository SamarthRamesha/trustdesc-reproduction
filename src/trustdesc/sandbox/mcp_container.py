"""Offline, immutable-image MCP stdio backend, fail closed by default.

No image pulls/builds, host mounts, credentials, or host-side tool imports.
This backend is unavailable on normal Colab when Docker is unavailable.
Container isolation is an engineering boundary, not a proof against kernel bugs.
"""
from __future__ import annotations
import json
import os
import platform
import re
import selectors
import shutil
import subprocess
import time
import uuid
from trustdesc.common.io import ValidationError, digest
from trustdesc.descgen.prompts import AGENT
from .runner import SandboxError


def container_command(image, command, name):
    if not re.fullmatch(r'[a-zA-Z0-9./:_-]+@sha256:[0-9a-f]{64}', image):
        raise ValidationError('Immutable image digest required')
    if not isinstance(command, list) or not command or not all(isinstance(s, str) and s and '\x00' not in s for s in command):
        raise ValidationError('Explicit argument-vector command required')
    if not re.fullmatch('trustdesc-[a-f0-9]{32}', name):
        raise ValidationError('Invalid container name')
    return ['docker', 'run', '-i', '--rm', '--pull=never', '--name', name,
            '--network=none', '--read-only', '--cap-drop=ALL',
            '--security-opt=no-new-privileges', '--pids-limit=64',
            '--memory=512m', '--memory-swap=512m', '--cpus=1',
            '--ulimit=nofile=128:128', '--user=65534:65534',
            '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m',
            '--workdir=/tmp', '--env=HOME=/tmp', image, *command]


def availability():
    return {'platform': platform.system(), 'docker_cli': bool(shutil.which('docker')),
            'status': 'requires_approved_local_image_and_probe' if platform.system() == 'Linux' and shutil.which('docker') else 'unavailable',
            'reason': 'No automatic image pull or host execution fallback; default Colab does not supply an isolated Docker daemon.'}


class ContainerMCP:
    def __init__(self, spec, *, execution_permitted=False, timeout=30, log_bytes=1_000_000):
        if not execution_permitted:
            raise SandboxError('Explicit execution permission is required')
        if platform.system() != 'Linux' or not shutil.which('docker'):
            raise SandboxError('Linux Docker isolation unavailable; tool remains disabled')
        if not spec.get('source_sha256') or not re.fullmatch('[0-9a-f]{64}', spec['source_sha256']):
            raise ValidationError('Image-to-source SHA-256 attestation required')
        if not spec.get('provenance'):
            raise ValidationError('Image/source provenance required')
        if not 1 <= timeout <= 120 or not 1024 <= log_bytes <= 4_000_000:
            raise ValidationError('Invalid execution bounds')
        self.spec, self.timeout, self.limit = spec, timeout, log_bytes
        self.name = 'trustdesc-' + uuid.uuid4().hex
        self.command = container_command(spec['image'], spec['command'], self.name)
        self.proc = None
        self.selector = selectors.DefaultSelector()
        self.buffers = {'stdout': b'', 'stderr': b''}
        self.bytes_seen = 0
        self.rpc_id = 0
        self.tools = {}
        self.binding = digest(spec)

    def __enter__(self):
        try:
            # Pull is forbidden: inspect must find this exact repository digest.
            p = subprocess.run(['docker', 'image', 'inspect', self.spec['image'], '--format', '{{json .RepoDigests}}'],
                               capture_output=True, text=True, timeout=10, check=True)
            if self.spec['image'] not in json.loads(p.stdout):
                raise SandboxError('Local image digest mismatch')
            probe_name = 'trustdesc-' + uuid.uuid4().hex
            probe = container_command(self.spec['image'], ['python', '-I', '-c',
                "import os,json; s=open('/proc/self/status').read(); print(json.dumps({'uid':os.getuid(),'net':open('/proc/net/route').read(),'mounts':open('/proc/mounts').read(),'status':s}))"], probe_name)
            try:
                result = subprocess.run(probe, capture_output=True, text=True, timeout=10, check=True)
            finally:
                subprocess.run(['docker', 'rm', '-f', probe_name], capture_output=True, timeout=10)
            evidence = json.loads(result.stdout)
            if evidence['uid'] != 65534 or not re.search(r'CapEff:\s+0+\n', evidence['status']) or not re.search(r'NoNewPrivs:\s+1', evidence['status']):
                raise SandboxError('Isolation capability/user probe failed')
            if any(line.split()[1] == '00000000' for line in evidence['net'].splitlines()[1:] if len(line.split()) > 1):
                raise SandboxError('Unexpected default network route')
            roots = [line.split()[3].split(',') for line in evidence['mounts'].splitlines() if len(line.split()) >= 4 and line.split()[1] == '/']
            if not roots or 'ro' not in roots[0]:
                raise SandboxError('Root filesystem is not read-only')
            self.probe = evidence
            self.proc = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
            for stream in ['stdout', 'stderr']:
                pipe = getattr(self.proc, stream)
                os.set_blocking(pipe.fileno(), False)
                self.selector.register(pipe, selectors.EVENT_READ, stream)
            self.deadline = time.monotonic() + self.timeout
            self.request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                         'clientInfo': {'name': 'trustdesc-isolated', 'version': '1'}})
            self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
            listed = self.request('tools/list', {})
            if listed.get('nextCursor'):
                raise SandboxError('Paginated tool lists require explicit support; refusing partial catalog')
            for tool in listed.get('tools', []):
                if tool['name'] in self.tools:
                    raise SandboxError('Duplicate MCP tool name')
                self.tools[tool['name']] = tool
            if not self.tools:
                raise SandboxError('Empty MCP tool catalog')
            return self
        except BaseException:
            self.close()
            raise

    def send(self, value):
        data = json.dumps(value, separators=(',', ':')).encode() + b'\n'
        if len(data) > 65536:
            raise SandboxError('RPC input exceeds bound')
        if self.proc.poll() is not None:
            raise SandboxError('MCP container terminated')
        # Requests are small; no large user writes can block the pipe.
        os.set_blocking(self.proc.stdin.fileno(), False)
        end = time.monotonic() + 2
        while data:
            if time.monotonic() >= min(end, self.deadline):
                raise TimeoutError('MCP write timeout')
            try:
                count = os.write(self.proc.stdin.fileno(), data)
                data = data[count:]
            except BlockingIOError:
                time.sleep(.01)

    def request(self, method, params):
        self.rpc_id += 1
        ident = self.rpc_id
        self.send({'jsonrpc': '2.0', 'id': ident, 'method': method, 'params': params})
        while time.monotonic() < self.deadline:
            while b'\n' in self.buffers['stdout']:
                line, self.buffers['stdout'] = self.buffers['stdout'].split(b'\n', 1)
                if not line.strip():
                    continue
                message = json.loads(line)
                if 'method' in message and 'id' in message:
                    # Never service server requests for sampling, roots, etc.
                    self.send({'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32601, 'message': 'Client method disabled'}})
                if message.get('id') == ident and 'method' not in message:
                    if 'error' in message:
                        raise SandboxError('MCP RPC error: ' + str(message['error'])[:500])
                    return message['result']
            if self.proc.poll() is not None:
                raise SandboxError('MCP container exited before response')
            for key, _ in self.selector.select(min(.2, max(0, self.deadline-time.monotonic()))):
                raw = os.read(key.fileobj.fileno(), 65536)
                if not raw:
                    self.selector.unregister(key.fileobj)
                    continue
                self.bytes_seen += len(raw)
                if self.bytes_seen > self.limit:
                    raise SandboxError('MCP output/log cap reached')
                self.buffers[key.data] += raw
        raise TimeoutError('MCP execution deadline reached')

    def call(self, name, arguments):
        if name not in self.tools or not isinstance(arguments, dict):
            raise SandboxError('Unlisted tool/invalid arguments')
        return self.request('tools/call', {'name': name, 'arguments': arguments})

    def close(self):
        if self.proc:
            self.proc.kill()
            self.proc.wait(timeout=5)
            for stream in [self.proc.stdin, self.proc.stdout, self.proc.stderr]:
                stream.close()
        self.selector.close()
        # Covers timeout, RPC errors and broken pipes; no daemon-side orphan.
        subprocess.run(['docker', 'rm', '-f', self.name], capture_output=True, timeout=10)

    def __exit__(self, *exc):
        self.close()


class ContainerAgent:
    def __init__(self, model, spec, *, execution_permitted=False, max_steps=6, descriptions=None):
        self.model, self.spec, self.permitted = model, spec, execution_permitted
        self.steps, self.descriptions = max_steps, descriptions

    def run(self, task):
        events = []
        try:
            with ContainerMCP(self.spec, execution_permitted=self.permitted) as mcp:
                catalog = mcp.tools if self.descriptions is None else {k: v for k, v in self.descriptions.items() if k in mcp.tools}
                for step in range(self.steps):
                    action = self.model.complete('agent', AGENT, {'task': task, 'tools': catalog, 'observations': events, 'step': step})
                    if action.get('action') == 'finish':
                        return {'backend': 'docker_mcp_stdio', 'status': 'completed', 'events': events,
                                'answer': action.get('answer', ''), 'source_binding': mcp.binding, 'isolation_probe': mcp.probe}
                    name, arguments = action.get('tool'), action.get('arguments')
                    if name not in catalog:
                        raise SandboxError('Agent requested an unexposed tool')
                    observed = mcp.call(name, arguments)
                    events.append({'tool': name, 'arguments': arguments, 'status': 'tool_error' if observed.get('isError') else 'ok',
                                  **({'error': json.dumps(observed)} if observed.get('isError') else {'result': observed})})
                status = 'step_limit'
        except TimeoutError:
            status = 'timeout'
        except Exception as exc:
            return {'backend': 'docker_mcp_stdio', 'status': 'sandbox_error', 'events': events, 'reason': f'{type(exc).__name__}: {exc}'}
        return {'backend': 'docker_mcp_stdio', 'status': status, 'events': events}
