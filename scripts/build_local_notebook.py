#!/usr/bin/env python3
"""Build a standalone local notebook with hash-checked embedded project source."""
from pathlib import Path
import base64
import hashlib
import io
import json
import textwrap
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def build():
    files=[]
    for prefix in ['src','configs','tests','data/manifests','data/public_example','scripts','docs']:
        files.extend(p for p in (ROOT/prefix).rglob('*') if p.is_file() and (p.suffix in {'.py','.json','.jsonl','.txt','.md'} or p.name=='LICENSE'))
    files.extend(ROOT/p for p in ['README.md','LICENSE','NOTICE.md','pyproject.toml','PROJECT_STATE.md','requirements-apple.txt','requirements-apple-lock.txt','requirements-colab.txt','requirements.txt'])
    files.append(ROOT/'reports/published_results.csv')
    source={p.relative_to(ROOT).as_posix():p.read_bytes() for p in sorted(set(files))}
    hashes={name:hashlib.sha256(raw).hexdigest() for name,raw in source.items()}
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,raw in source.items():
            info=zipfile.ZipInfo(name,date_time=(2026,11,9,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,raw)
    encoded=base64.b64encode(buffer.getvalue()).decode()
    cells=[]
    def add(kind,id,text):
        cell={'cell_type':kind,'id':id,'metadata':{},'source':textwrap.dedent(text).strip().splitlines(True)}
        if kind=='code':cell.update(execution_count=None,outputs=[])
        cells.append(cell)
    md=lambda id,text:add('markdown',id,text)
    code=lambda id,text:add('code',id,text)
    md('overview','''
    # TRUSTDESC · Local research reproduction
    **Apple Silicon primary · free local inference · evidence and checkpoint recovery**

    Open in local Jupyter and choose **Run All**. This notebook contains its own hash-checked implementation, creates a project-local Python environment, installs pinned dependencies, tests Python startup, qualifies a real model, executes SliceMin → DescGen → DynVer, compares Original / lite / full with a fixed task agent, and packages the recorded evidence. No uploads, API keys or manual cell edits are required. First use downloads public packages and model weights.

    The paper is [Ye et al., TRUSTDESC, arXiv:2604.07536v1](https://arxiv.org/abs/2604.07536v1). Its original 52-tool/208-task release remains unauthenticated/unavailable. The automatic comparison uses eight explicitly authored tasks and two pure tools; these results are not the paper's TSR. Public source analysis has separate provenance. A finished software run or handover does not establish full scientific reproduction.

    Apple Silicon uses quantized MLX when installed, otherwise supported MPS or CPU. Model selection considers available memory and must pass real inference, JSON-structure and action checks. No generation is replaced by scripted answers. Optional Colab notebooks remain under `notebooks/colab/`.
    ''')
    md('source-heading','''
    ## 1 · Recover the exact source
    Source is embedded in this notebook and checked against SHA-256 before import. Cached files are rechecked. The runtime is stored in `trustdesc_local` beside the notebook; old runs are preserved. The notebook never needs to download a moving Git branch.
    ''')
    code('bootstrap','''
    import base64, hashlib, io, json, os, platform, shutil, signal, subprocess, sys, time, venv, zipfile
    from pathlib import Path, PurePosixPath
    from IPython.display import display, Markdown, FileLink, SVG
    BASE = Path(globals().get("_TRUSTDESC_LOCAL_WORKSPACE", "trustdesc_local")).resolve()
    BASE.mkdir(parents=True, exist_ok=True)
    SOURCE_HASHES = __HASHES__
    SOURCE_ID = hashlib.sha256(json.dumps(SOURCE_HASHES,sort_keys=True).encode()).hexdigest()[:20]
    PROJECT = BASE / ("source-" + SOURCE_ID)
    EMBEDDED = __ENCODED__
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(EMBEDDED))) as archive:
        if set(archive.namelist()) != set(SOURCE_HASHES):
            raise RuntimeError("Embedded source inventory mismatch")
        for name, expected in SOURCE_HASHES.items():
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError("Unsafe source path")
            raw = archive.read(name)
            if hashlib.sha256(raw).hexdigest() != expected:
                raise RuntimeError("Embedded source checksum mismatch: " + name)
            target = PROJECT / name
            if target.is_symlink() or any(p.is_symlink() for p in target.parents if p != BASE.parent):
                raise RuntimeError("Symlink in runtime source path")
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
    (PROJECT/"PORTABLE_MANIFEST.json").write_text(json.dumps({"git_commit":None,"embedded_source_id":SOURCE_ID,"files_sha256":SOURCE_HASHES},indent=2))
    print("Verified",len(SOURCE_HASHES),"source files; identity",SOURCE_ID)
    print("Workspace:",BASE)
    '''.replace('__HASHES__',repr(hashes)).replace('__ENCODED__',repr(encoded)))
    md('python-heading','''
    ## 2 · Validate Python and install the local environment
    The startup check imports only the standard library. It stops on a failure before any inference library loads. The environment is separate from the notebook kernel. Apple packages use normal macOS wheels; the Linux CPU wheel index is never used on a Mac.
    ''')
    code('environment','''
    CANDIDATE = shutil.which("python3.11") or sys.executable
    startup = subprocess.run([CANDIDATE,"-I","-S","-c","import sys; assert sys.version_info >= (3,11); print('PYTHON_STARTUP_OK')"],capture_output=True,text=True,timeout=8)
    if startup.returncode or startup.stdout.strip() != "PYTHON_STARTUP_OK":
        raise RuntimeError("Python startup failed; model loading blocked. " + startup.stderr)
    ENV = BASE / "venv"
    PYTHON = ENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not PYTHON.is_file():
        subprocess.run([CANDIDATE,"-m","venv",str(ENV)],check=True)
    APPLE = platform.system()=="Darwin" and platform.machine()=="arm64"
    requirements = PROJECT / ("requirements-apple-lock.txt" if APPLE else "requirements-colab.txt")
    install_log = BASE / "dependency-install.txt"
    print("Preparing pinned", "Apple MLX" if APPLE else "PyTorch CPU/CUDA", "dependencies; log:",install_log)
    install_command = [str(PYTHON),"-m","pip","install","--disable-pip-version-check","-r",str(requirements)]
    if not APPLE:
        install_command.append("torch==2.9.0")
    with install_log.open("w") as stream:
        installed = subprocess.run(install_command,stdout=stream,stderr=subprocess.STDOUT)
    if installed.returncode:
        raise RuntimeError("Dependency installation failed. " + install_log.read_text()[-5000:])
    checked = subprocess.run([str(PYTHON),"-m","pip","check"],capture_output=True,text=True)
    (BASE/"dependency-check.txt").write_text(checked.stdout+checked.stderr)
    if checked.returncode:
        raise RuntimeError("Dependency consistency check failed: "+checked.stdout+checked.stderr)
    subprocess.run([str(PYTHON),str(PROJECT/"scripts/run_local_reproduction.py"),"--workspace",str(BASE),"--preflight-only"],check=True)
    print("Environment and Python-only startup ready.")
    ''')
    md('execution-heading','''
    ## 3 · Execute and preserve observations
    A qualified free local model performs actual generation, identifier filtering, claim attribution, task planning and judging. SliceMin records unresolved calls and unproven rewrite proposals. DynVer executes authored tools, records traces and removes unsupported claims. Original/lite/full use the same task agent. Lite removes the functionality list after refinement.

    External source stays disabled in the main benchmark unless an independently validated execution adapter is configured. macOS Seatbelt offers a separate offline Python observation boundary with startup and access-denial probes; ordinary fixture execution is not a sandbox. No private files or paid APIs are used. Failed stages retain tracebacks and missing observations; they do not become synthetic successes.

    Successful checkpoints bind source, configuration, prompts, dataset, model and runtime. Rerunning an unchanged environment reuses valid results. Changed identity creates another run. Model workers have wall deadlines and are unloaded when the run exits.
    ''')
    code('execute','''
    pipeline_log = BASE/"pipeline.txt"
    if pipeline_log.exists(): pipeline_log.rename(BASE/("pipeline-"+str(time.time_ns())+".txt"))
    command = [str(PYTHON),"-u",str(PROJECT/"scripts/run_local_reproduction.py"),"--workspace",str(BASE)]
    with pipeline_log.open("w") as stream:
        process = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,start_new_session=os.name!="nt")
        try:
            for line in process.stdout:
                stream.write(line); stream.flush(); print(line,end="",flush=True)
            process.wait()
        except BaseException:
            if os.name != "nt": os.killpg(process.pid,signal.SIGTERM)
            else: process.terminate()
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                if os.name != "nt": os.killpg(process.pid,signal.SIGKILL)
                else: process.kill()
                process.wait(timeout=5)
            raise
    if process.returncode:
        raise RuntimeError("Pipeline failed; inspect saved traceback and log: "+str(pipeline_log))
    LATEST = json.loads((BASE/"latest_run.json").read_text())
    RUN = Path(LATEST["run_root"])
    print("Recorded run:",RUN)
    ''')
    md('results-heading','''
    ## 4 · Results and limitations
    Read the actual stage statuses and observed denominators below. Fixture success is an authored exact-trace check, separate from the paper's human-reviewed TSR. Missing original artifacts, model substitutions, unsupported languages/dynamic behavior and absent external MCP execution remain explicit limitations. Finite behavioral tests do not prove universal correctness or safety.
    ''')
    code('results','''
    RESULTS = json.loads((RUN/"results.json").read_text())
    display([row for row in RESULTS["conditions"] if row["tool"]=="ALL"])
    display(SVG(filename=str(RUN/"plots/fixture_objectives.svg")))
    display(Markdown((RUN/"PHASE2_COMPLETION_REPORT.md").read_text()))
    display(json.loads((RUN/"model_manifest.json").read_text()))
    ''')
    md('validation-heading','''
    ## 5 · Validate software and export the handover
    Software checks are separate from scientific results. The archive is CRC-checked and every member is SHA-256-verified by the exporter. Model weights, caches, private PDFs and credentials are excluded.
    ''')
    code('validate','''
    print((RUN/"software_tests.txt").read_text()[-2500:])
    tests=json.loads((RUN/"software_test_status.json").read_text())
    if tests.get("returncode") != 0:
        raise RuntimeError("Software tests failed; inspect saved software_tests.txt")
    display(json.loads((RUN/"validation_report.json").read_text()))
    for path in [Path(LATEST["archive"]),Path(LATEST["checksum_file"]),RUN/"FINAL_PROJECT_COMPLETION_REPORT.md",RUN/"PHASE2_COMPLETION_REPORT.md",RUN/"PHASE3_HANDOVER.md",RUN/"EXPERIMENT_RESULTS.md",RUN/"results.json"]:
        display(FileLink(os.path.relpath(path,Path.cwd())))
    print("Handover exported. Scientific completion status:",LATEST["phase2_scientific_complete"])
    ''')
    return {'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
             'language_info':{'name':'python','version':'3.11'},'trustdesc':{'primary_platform':'Apple Silicon','source_id':hashlib.sha256(buffer.getvalue()).hexdigest(),'embedded_source':True,'original_benchmark_available':False}},'nbformat':4,'nbformat_minor':5}


if __name__=='__main__':
    (ROOT/'TRUSTDESC_REPRODUCTION.ipynb').write_text(json.dumps(build(),indent=1)+'\n')
