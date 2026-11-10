"""Fail-closed macOS Seatbelt boundary for offline Python source observations.

Not a VM or general MCP server. The OS sandbox, rather than subprocess alone,
denies private reads, writes outside scratch, network and child processes.
No external source may run until canary probes pass on the current machine.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import selectors
import shutil
import signal
import subprocess
import sys
import sysconfig
import tempfile
import time
from .runner import SandboxError
from trustdesc.reproduction.startup import python_binary, launch_environment, startup_smoke


def policy(scratch, extra_reads=()):
    scratch = Path(scratch).resolve()
    executable = python_binary()
    stdlib = Path(sysconfig.get_path('stdlib')).resolve()
    # -I -S excludes cwd, user site, PYTHONPATH and site packages unless the
    # caller opts into a specific dependency directory via extra_reads.
    reads = [scratch, stdlib, Path(sys.base_prefix).resolve(), Path('/System/Library'),Path('/usr/lib'),
             Path('/private/var/db/dyld')] + [Path(p).resolve() for p in extra_reads]
    q = lambda p: json.dumps(str(p))
    return '\n'.join(['(version 1)','(deny default)','(allow file-read-metadata)',
        '(allow sysctl-read)', '(allow mach-lookup (global-name "com.apple.system.logger"))',
        '(allow process-exec (literal '+q(executable)+'))',
        # dyld/libignition opens the root directory during cache discovery.
        # Literal / permits that directory only, never its descendants.
        '(allow file-read-data (literal "/") '+ ' '.join('(subpath '+q(p)+')' for p in reads)+
        ' (literal "/dev/null") (literal "/dev/random") (literal "/dev/urandom"))',
        '(allow file-write* (subpath '+q(scratch)+') (literal "/dev/null"))'])


WRAPPER = '''import resource, json, sys, runpy
resource.setrlimit(resource.RLIMIT_CPU, (4,4))
resource.setrlimit(resource.RLIMIT_FSIZE, (262144,262144))
resource.setrlimit(resource.RLIMIT_NOFILE, (32,32))
resource.setrlimit(resource.RLIMIT_CORE, (0,0))
# Darwin RLIMIT_AS is not a reliable RSS limit. Restrict address space as a
# best-effort extra bound, and enforce RSS from the supervising process.
request=json.loads(open('request.json').read())
try:
    namespace=runpy.run_path('tool.py')
    value=namespace[request['function']](**request['arguments'])
    print(json.dumps({'status':'ok','result':value},allow_nan=False))
except Exception as exc:
    import traceback
    print(json.dumps({'status':'tool_error','error_type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc()}))
'''


class SeatbeltPython:
    def __init__(self, workspace, *, timeout=8, memory_bytes=256*1024**2, extra_reads=(), isolated=True):
        self.extra_reads = tuple(extra_reads)
        self.isolated = isolated
        if platform.system()!='Darwin' or not shutil.which('sandbox-exec'):
            raise SandboxError('macOS Seatbelt unavailable; no host execution fallback')
        try:
            import psutil
        except ImportError as exc:
            raise SandboxError('psutil required for resource supervision') from exc
        self.psutil,self.workspace=psutil,Path(workspace).resolve()
        self.workspace.mkdir(parents=True,exist_ok=True)
        self.timeout,self.memory_bytes=timeout,memory_bytes
        self.probed=False
        self.startup_result=None

    def _execute(self, source, function, arguments, wrapper=None, timeout=None):
        wrapper = wrapper or WRAPPER
        with tempfile.TemporaryDirectory(prefix='seatbelt-',dir=self.workspace) as temp:
            root=Path(temp)
            (root/'policy.sb').write_text(policy(root, self.extra_reads))
            (root/'tool.py').write_text(source)
            (root/'wrapper.py').write_text(wrapper)
            (root/'request.json').write_text(json.dumps({'function':function,'arguments':arguments},allow_nan=False))
            start=time.perf_counter()
            flags=['-I'] + (['-S'] if self.isolated else [])
            with (root/'stdout').open('wb') as stdout,(root/'stderr').open('wb') as stderr:
                proc=subprocess.Popen(['/usr/bin/sandbox-exec','-f',str(root/'policy.sb'),
                                       str(python_binary()),*flags,str(root/'wrapper.py')],
                                      cwd=root,env=launch_environment(),
                                      stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
                status='exited'
                peak=0
                while proc.poll() is None:
                    try:peak=max(peak,self.psutil.Process(proc.pid).memory_info().rss)
                    except self.psutil.NoSuchProcess:pass
                    if time.perf_counter()-start>(timeout or self.timeout) or peak>self.memory_bytes:
                        status='timeout' if peak<=self.memory_bytes else 'memory_limit'
                        os.killpg(proc.pid,signal.SIGKILL)
                        break
                    time.sleep(.02)
                proc.wait(timeout=3)
            raw=(root/'stdout').read_text(errors='replace')[:262144]
            error=(root/'stderr').read_text(errors='replace')[:262144]
            result={'backend':'macos_seatbelt_offline_python','process_status':status,'returncode':proc.returncode,
                    'stdout':raw,'stderr':error,'seconds':time.perf_counter()-start,'peak_rss_bytes':peak,
                    'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
                    'policy_sha256':hashlib.sha256(policy(root, self.extra_reads).encode()).hexdigest(),
                    'scope':'offline Python source module; not full MCP transport; finite resource supervision'}
            try: result['observation']=json.loads(raw)
            except ValueError:result['observation']=None
            return result

    def probe(self):
        with tempfile.TemporaryDirectory(prefix='startup-',dir=self.workspace) as temp:
            root=Path(temp)
            profile=root/'policy.sb'
            profile.write_text(policy(root))
            self.startup_result=startup_smoke(cwd=root,repeats=3,env=launch_environment(),
                              prefix=['/usr/bin/sandbox-exec','-f',str(profile)])
        if not self.startup_result['passed']:
            self.probed=False
            return {'passed':False,'status':'python_startup_failed','startup':self.startup_result,
                    'external_source_executed':False}
        canary=self.workspace/'outside-canary.txt'
        canary.write_text('project-created private-read canary, never personal data')
        source='''def probe(path):
    import socket, subprocess
    result={}
    try:
        open(path).read(); result['read_denied']=False
    except PermissionError: result['read_denied']=True
    try:
        open(path+'.write','w').write('bad'); result['write_denied']=False
    except PermissionError: result['write_denied']=True
    try:
        socket.socket().connect(('127.0.0.1',9)); result['network_denied']=False
    except PermissionError: result['network_denied']=True
    except OSError: result['network_denied']=False
    try:
        subprocess.run(['/bin/echo','bad'],check=True); result['process_denied']=False
    except PermissionError: result['process_denied']=True
    return result
'''
        result=self._execute(source,'probe',{'path':str(canary)})
        try:
            value=result['observation']['result']
            self.probed=value=={'read_denied':True,'write_denied':True,'network_denied':True,'process_denied':True}
        except (KeyError,TypeError):self.probed=False
        result['passed']=self.probed
        self.probe_result=result
        canary.unlink(missing_ok=True)
        Path(str(canary)+'.write').unlink(missing_ok=True)
        return result

    def run_source(self, source, function, arguments, wrapper=None, timeout=None):
        if not self.probed:
            raise SandboxError('Isolation probes must pass before external source execution')
        return self._execute(source,function,arguments,wrapper=wrapper,timeout=timeout)
