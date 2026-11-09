"""Notebook session: acquisition, hardware-aware models and portable outputs."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from trustdesc.common.io import digest
from trustdesc.experiments.runtime import inspect_runtime
from trustdesc.experiments.data import source_hashes
from trustdesc.experiments.setup import prepare_inputs
from trustdesc.experiments.workflow import implementation_hash
from trustdesc.experiments.storage import Store
from trustdesc.sandbox.mcp_container import availability
from .resources import acquire_references, validate_bundle
from .workflow import AutomaticWorkflow, SingleModelPool
from .report import analyze, validate_and_package


def select_config(project, runtime):
    spec=json.loads((Path(project)/'configs/reproduction.json').read_text())
    gpus=runtime.get('gpus',[])
    gpu_ok=bool(gpus) and gpus[0]['free_bytes']>=spec['models_by_hardware']['cuda']['minimum_gpu_free_bytes']
    hardware='cuda' if gpu_ok else 'cpu'
    cfg={**spec['models_by_hardware'][hardware],**spec['model_settings']}
    cfg['device'] = hardware
    cfg['substitution']='Single-T4 feasible independent local model; not paper models' if gpu_ok else 'No compatible CUDA GPU: smaller CPU model; slower and different experimental condition'
    config={k:spec[k] for k in ['schema_version','seed','agent_max_steps','refinement_rounds','paid_models_enabled','external_execution_enabled','evaluation']}
    config.update(models=[cfg],task_agent=copy.deepcopy(cfg),hardware_selection=hardware)
    available=runtime.get('ram_available_bytes') or runtime.get('ram_total_bytes')
    constraints=[]
    if available and available<cfg['minimum_available_ram_bytes']:constraints.append('Insufficient available host RAM for selected safe configuration')
    if runtime['disk_free_bytes']<spec['minimum_disk_free_bytes']:constraints.append('Less than 8 GiB free disk; automatic model loading blocked')
    if not runtime['python_supported']:constraints.append('Python >=3.11 required')
    return config,constraints


class Session:
    def __init__(self, project, workspace, *, network=True, model=None, model_error=None):
        self.project=Path(project).resolve()
        self.workspace=Path(workspace).resolve()
        self.workspace.mkdir(parents=True,exist_ok=True)
        os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
        self.runtime=inspect_runtime()
        self.config,self.constraints=select_config(self.project,self.runtime)
        self.network=network
        self.supplied_model=model
        self.model_error=model_error
        self.failures=[]
        self.model_manifest={'status':'not_loaded','selected':self.config['models'][0],
                             'task_agent':self.config['task_agent'],'original_models_run':False}
        self.isolation=availability()
        self.isolation.update(external_execution_permitted=False,external_tools_executed=False,
                              default_dynamic_backend='authored_pure_fixture_allowlist_not_a_sandbox')
        self.bundle,self.roots,self.input_report=prepare_inputs(self.project,self.workspace/'inputs',acquire_public=network)
        self.bundle['validation']=validate_bundle(self.bundle,self.roots)
        binding={'config':self.config,'bundle':self.bundle,'sources':source_hashes(self.roots),
                 'implementation':implementation_hash(),
                 'runtime':{k:self.runtime.get(k) for k in ['python','machine','packages']},
                 'gpus':[(g['name'],g['total_bytes']) for g in self.runtime.get('gpus',[])]}
        self.run_root=self.workspace/'runs'/('automatic-'+digest(binding)[:20])
        self.store=Store(self.run_root)
        # Workflow refuses a nonempty uninitialized run. Construct before writing
        # acquisition records, with a pool whose model is populated later.
        empty_pool=SingleModelPool(None,self.store,'Model not initialized')
        self.workflow=AutomaticWorkflow(self.project,self.run_root,self.config,self.bundle,self.roots,self.runtime,
                                        resume=(self.run_root/'EXPERIMENT_MANIFEST.json').exists(),retry_failed=True,pool=empty_pool)
        self.store.write('input_acquisition.json',self.input_report)
        self.store.write('hardware_model_selection.json',{'selected':self.config,'constraints':self.constraints,
                    'notes':'Estimated weight sizes only; T4 capacity and context limits are estimates, not a measured completion-time guarantee.'})
        self._record_source()

    def _record_source(self):
        selected=[]
        for prefix in ['src','configs','tests','data/manifests']:
            selected.extend(p for p in (self.project/prefix).rglob('*') if p.is_file() and p.suffix in {'.py','.json','.jsonl','.txt'})
        selected += [self.project/p for p in ['pyproject.toml','requirements-colab.txt','LICENSE','NOTICE.md']]
        runner = self.project/'scripts/run_automatic_reproduction.py'
        if runner.exists():selected.append(runner)
        portable = self.project/'PORTABLE_MANIFEST.json'
        if portable.exists():selected.append(portable)
        for path in selected:
            self.store.text(Path('reproduction_source')/path.relative_to(self.project),path.read_text())
        freeze=subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True,timeout=30)
        self.store.text('installed_packages.txt',freeze.stdout if freeze.returncode==0 else 'pip freeze unavailable: '+freeze.stderr)

    def acquire(self):
        self.acquisition=acquire_references(self.project,self.workspace/'cache/resources',self.store,network=self.network)
        self.acquisition['fixture_and_public_source']=self.input_report
        self.store.write('acquisition_report.json',self.acquisition)
        return self.acquisition

    def initialize_model(self):
        if self.supplied_model is not None:
            model=self.supplied_model
            real = model.mode == 'real_local_transformers_inference'
            self.model_manifest.update(status='injected_real_model_validation' if real else 'injected_software_validation_model',mode=model.mode,
                                       note='Explicit validation injection; never used by default notebook')
            if real:
                self.model_manifest['runtime'] = model.model.runtime
        else:
            model=None
            try:
                if self.constraints:raise RuntimeError('; '.join(self.constraints))
                if self.model_error:raise RuntimeError(self.model_error)
                if not self.network:raise RuntimeError('Offline software validation: inference not attempted')
                from .model import LocalModel,RepairModel
                model=RepairModel(LocalModel(self.config['models'][0],self.workspace/'cache/models'))
                self.model_manifest.update(status='loaded_real_local_model',runtime=model.model.runtime,
                                           mode=model.mode,substitutions=[self.config['models'][0]['substitution']])
            except Exception as exc:
                self.model_error=f'{type(exc).__name__}: {exc}'
                self.model_manifest.update(status='unavailable',error=self.model_error,semantic_replay_substitution=False)
                self.failures.append({'status':'unavailable','component':'model','reason':self.model_error})
        self.workflow.pool=SingleModelPool(model,self.store,self.model_error)
        self.store.write('model_manifest.json',self.model_manifest)
        return self.model_manifest

    def finish(self):
        if not hasattr(self,'acquisition'):self.acquire()
        self.results=analyze(self.workflow,self.acquisition,self.model_manifest,self.isolation,self.failures)
        self.workflow.manifest.update(status='pipeline_finished_scientific_phase2_incomplete',phase2_complete=False)
        self.store.write('EXPERIMENT_MANIFEST.json',self.workflow.manifest)
        self.export=validate_and_package(self.workflow,self.workspace/'deliverables'/self.run_root.name)
        return self.export

    def run_all(self):
        self.acquire()
        self.initialize_model()
        self.workflow.static()
        self.workflow.descriptions()
        self.workflow.verification()
        self.workflow.benchmark()
        return self.finish()
