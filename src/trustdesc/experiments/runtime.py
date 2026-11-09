from __future__ import annotations
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from importlib.metadata import version,PackageNotFoundError
from pathlib import Path


def inspect_runtime():
    packages={}
    for name in ['torch','transformers','matplotlib','huggingface-hub','safetensors','mlx','mlx-lm','psutil']:
        try:packages[name]=version(name)
        except PackageNotFoundError:packages[name]=None
    total = available = None
    if Path('/proc/meminfo').exists():
        values = dict(re.findall(r'^(\w+):\s+(\d+)', Path('/proc/meminfo').read_text(), re.M))
        total = int(values['MemTotal']) * 1024
        available = int(values.get('MemAvailable', values.get('MemFree', 0))) * 1024
    else:
        try: total = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
        except (ValueError, OSError): pass
    try:
        import psutil
        memory = psutil.virtual_memory()
        total, available = memory.total, memory.available
    except (ImportError, OSError):
        pass
    apple = platform.system() == 'Darwin' and platform.machine() == 'arm64'
    mps = False
    if apple and packages['torch']:
        try:
            import torch
            mps = torch.backends.mps.is_available()
        except (ImportError, RuntimeError):
            pass
    gpu = []
    cuda = None
    if shutil.which('nvidia-smi'):
        p = subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.free,driver_version','--format=csv,noheader,nounits'],capture_output=True,text=True)
        if p.returncode == 0:
            for line in p.stdout.splitlines():
                name, memory, free, driver = [v.strip() for v in line.split(',')]
                gpu.append({'name':name,'total_bytes':int(memory)*1024**2,'free_bytes':int(free)*1024**2,'driver':driver})
        p = subprocess.run(['nvidia-smi'],capture_output=True,text=True)
        match = re.search(r'CUDA Version:\s*([\d.]+)', p.stdout)
        cuda = match.group(1) if match else None
    recommended = 'C' if gpu and gpu[0]['free_bytes'] >= 32*1024**3 else 'B' if gpu and gpu[0]['free_bytes'] >= 8*1024**3 else 'A'
    return {'python':platform.python_version(),'python_supported':sys.version_info >= (3,11),
            'platform':platform.platform(),'machine':platform.machine(),'ram_total_bytes':total,
            'ram_available_bytes':available,'disk_free_bytes':shutil.disk_usage('.').free,'gpus':gpu,
            'apple_silicon':apple,'mlx_installed':bool(apple and packages['mlx-lm']), 'mps_available':mps,
            'cuda_driver_supported_version':cuda,'packages':packages,'runtime_type':'colab' if 'COLAB_RELEASE_TAG' in os.environ or Path('/content').is_dir() else 'local_validation',
            'recommended_profile':recommended,'note':'Recommendation selects capacity profile only, never a scientific model automatically.'}
