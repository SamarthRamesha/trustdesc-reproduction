#!/usr/bin/env python3
"""Build the primary notebook from a committed source snapshot (no IPython dependency)."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import textwrap

ROOT=Path(__file__).resolve().parents[1]


def build(revision):
    paths=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    # Do not hash the notebook into itself. History/reports stay in the snapshot;
    # every runtime module/config/test used is independently checked before import.
    selected=[p for p in paths if p.startswith(('src/','configs/','tests/','data/manifests/','notebooks/colab/')) or p in ['pyproject.toml','requirements-colab.txt','LICENSE','NOTICE.md','docs/PAPER_ANALYSIS.md','reports/published_results.csv']]
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in selected}
    cells=[]
    def md(id,text):cells.append({'cell_type':'markdown','id':id,'metadata':{},'source':textwrap.dedent(text).strip().splitlines(True)})
    def code(id,text):cells.append({'cell_type':'code','id':id,'metadata':{},'execution_count':None,'outputs':[],'source':textwrap.dedent(text).strip().splitlines(True)})
    md('overview','''
    # TRUSTDESC · Reproducible Research Pipeline
    **Independent implementation · automatic Colab workflow · evidence-first handover**

    TRUSTDESC replaces potentially poisoned tool descriptions with descriptions inferred from source and checked against behavior. This notebook acquires its verified project modules automatically, detects hardware, runs SliceMin → DescGen → DynVer, compares original/lite/full descriptions using a fixed task agent, and packages the evidence.

    **Run:** Runtime → Change runtime type → Python 3 → **T4 GPU** → Save. Then Runtime → **Run all**. No uploads, API keys, cell edits, terminal commands or review spreadsheets are required. Public package/model downloads need internet access.

    Reference: Hengkai Ye, Zhechang Zhang, Jinyuan Jia and Hong Hu, [*TRUSTDESC*](https://arxiv.org/abs/2604.07536v1), §§4–5.

    **Scientific scope:** The original 52-tool/208-task artifact has not been authenticated or recovered. The automatic experiment uses two explicitly authored pure tools/eight synthetic tasks, plus a pinned paper-linked public source for static analysis. These are separate from the paper's original benchmark. The free local model is an alternative to the paper's models. Generated reports never turn missing observations into scores or declare Phase 2 complete without essential evidence.
    ''')
    md('architecture','''
    <div style="padding:18px;border-radius:12px;background:#eef5f8;color:#17384b;font-size:16px">
    <b>1 · Source + provenance</b> → <b>2 · SliceMin</b> (reachable code + unresolved calls)<br><br>
    → <b>3 · DescGen</b> (local LLM + source evidence) → <b>4 · DynVer</b> (tasks → execution → judge → retested corrections)<br><br>
    → <b>5 · Original / lite / full</b> (fixed task agent) → <b>6 · Reports + Phase 3 ZIP</b>
    </div>

    Lite is the refined full description with its functionality list removed. External code is parsed as text; external MCP execution requires a validated isolated container. The authored fixture allowlist is not an untrusted-code sandbox.
    ''')
    md('bootstrap-heading','''
    ## 1 · Verify and acquire the project
    A fixed Git commit and per-file SHA-256 manifest bind the modules used by this notebook. A cached copy is rechecked; corrupt or partial downloads are replaced. A bootstrap failure stops before importing unchecked code and gives the exact diagnostic.
    ''')
    bootstrap='''
    import hashlib, io, json, os, platform, shutil, subprocess, sys, urllib.request, zipfile
    from pathlib import Path, PurePosixPath
    from importlib.metadata import version, PackageNotFoundError
    from IPython.display import display, HTML, Markdown, FileLink, SVG
    if sys.version_info < (3, 11):
        raise RuntimeError("Python >=3.11 is required. Select a current Python 3 Colab runtime.")
    VALIDATION = globals().get("_TRUSTDESC_VALIDATION", {})
    SOURCE_REVISION = __REVISION__
    SOURCE_HASHES = __HASHES__
    BASE = Path(VALIDATION.get("workspace", "/content/trustdesc_automatic" if Path("/content").exists() else "./trustdesc_automatic")).resolve()
    BASE.mkdir(parents=True, exist_ok=True)
    PROJECT = Path(VALIDATION.get("project", BASE / ("project-" + SOURCE_REVISION))).resolve()
    def verified_project():
        return PROJECT.is_dir() and all((PROJECT / name).is_file() and not (PROJECT/name).is_symlink() and hashlib.sha256((PROJECT/name).read_bytes()).hexdigest() == sha for name, sha in SOURCE_HASHES.items())
    if not VALIDATION.get("project") and not verified_project():
        url = "https://codeload.github.com/SamarthRamesha/trustdesc-reproduction/zip/" + SOURCE_REVISION
        try:
            request = urllib.request.Request(url, headers={"User-Agent":"trustdesc-colab-research"})
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read(25_000_001)
            if len(raw) > 25_000_000:
                raise ValueError("Project archive exceeds 25 MB download limit")
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                members = archive.infolist()
                if len(members) > 10000 or sum(m.file_size for m in members) > 100_000_000:
                    raise ValueError("Project archive exceeds expanded limits")
                if len({m.filename for m in members}) != len(members):
                    raise ValueError("Duplicate project archive members")
                by_relative = {}
                for member in members:
                    p = PurePosixPath(member.filename)
                    if p.is_absolute() or ".." in p.parts or "\\\\" in member.filename or ((member.external_attr >> 16) & 0o170000) == 0o120000:
                        raise ValueError("Unsafe project archive member")
                    if len(p.parts) > 1 and not member.is_dir():
                        by_relative[PurePosixPath(*p.parts[1:]).as_posix()] = member
                checked = {}
                for name, sha in SOURCE_HASHES.items():
                    data = archive.read(by_relative[name])
                    if hashlib.sha256(data).hexdigest() != sha:
                        raise ValueError("Project SHA-256 mismatch: " + name)
                    checked[name] = data
                # No archive extraction API: only checked allowlisted files written.
                PROJECT.mkdir(parents=True, exist_ok=True)
                for name, data in checked.items():
                    target = PROJECT / name
                    if not target.resolve().is_relative_to(PROJECT) or target.is_symlink():
                        raise ValueError("Project output path is linked or escapes root")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    temporary = target.with_name(target.name + ".download-part")
                    temporary.write_bytes(data)
                    temporary.replace(target)
            if not verified_project():
                raise ValueError("Post-write project verification failed")
        except Exception as exc:
            raise RuntimeError(f"Verified project acquisition failed at {url}: {type(exc).__name__}: {exc}. Completed run outputs remain in {BASE}. Rerun after network recovery.") from exc
    elif VALIDATION.get("project"):
        print("Explicit local software-validation source override; not a Colab/GPU validation.")
    if not VALIDATION.get("project"):
        (PROJECT / "PORTABLE_MANIFEST.json").write_text(json.dumps({"git_commit":SOURCE_REVISION,"notebook":"TRUSTDESC_REPRODUCTION.ipynb","source_integrity":"per-file SHA-256"}))
    sys.path.insert(0, str(PROJECT / "src"))
    print(f"Project ready · Python {platform.python_version()} · source {SOURCE_REVISION[:12]} · {len(SOURCE_HASHES)} verified files")
    '''
    code('bootstrap',textwrap.dedent(bootstrap).replace('__REVISION__',repr(revision)).replace('__HASHES__',repr(hashes)))
    md('dependencies-heading','''
    ## 2 · Detect hardware and install pinned inference dependencies
    T4 uses Qwen2.5-Coder-1.5B-Instruct (about 3.1 GB of weights). CPU uses the 0.5B variant (about 1 GB); substitutions are recorded. GPU VRAM, host RAM, disk and library versions are checked. Loading is blocked when estimates exceed available resources. CPU inference can be substantially slower. No paid API is used.
    ''')
    code('dependencies','''
    INSTALL_ERRORS = []
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    startup_disk = shutil.disk_usage(BASE).free
    print(f"Startup disk available: {startup_disk / 1024**3:.1f} GiB")
    if startup_disk < 8 * 1024**3:
        INSTALL_ERRORS.append({"component":"disk_preflight","status":"unavailable","reason":"Less than 8 GiB free before dependency installation"})
    def installed(name):
        try: return version(name)
        except PackageNotFoundError: return None
    def install_logged(arguments, name):
        log = BASE / (name + ".txt")
        with log.open("w") as stream:
            result = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *arguments], stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            INSTALL_ERRORS.append({"component":name,"status":"failed","reason":log.read_text()[-6000:]})
            print(f"{name} failed. Diagnostic: {log.read_text()[-1200:]}")
        else: print(name + " ready")
    if not VALIDATION.get("skip_install", False) and not INSTALL_ERRORS:
        cuda_host = False
        try:
            probe = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.free", "--format=csv,noheader"], capture_output=True, text=True, timeout=10)
            cuda_host = probe.returncode == 0
            print(probe.stdout.strip() if cuda_host else "CUDA GPU unavailable; selecting CPU-compatible installation")
        except (OSError, subprocess.TimeoutExpired):
            print("CUDA GPU unavailable; selecting CPU-compatible installation")
        # Library imports happen only after installation. Existing Colab torch
        # is replaced only when the exact selected pin is missing.
        if (installed("torch") or "").split("+")[0] != "2.9.0":
            install_logged(["torch==2.9.0", *([] if cuda_host else ["--index-url", "https://download.pytorch.org/whl/cpu"])], "torch-install")
        wanted = {"transformers":"4.57.1", "huggingface-hub":"0.36.0", "safetensors":"0.6.2", "tokenizers":"0.22.1", "numpy":"2.2.6"}
        if any(installed(name) != pin for name,pin in wanted.items()):
            install_logged(["-r", str(PROJECT / "requirements-colab.txt")], "inference-install")
    elif VALIDATION.get("skip_install", False):
        print("Dependency installation skipped only by explicit software-validation harness")
    from trustdesc.reproduction.session import Session
    SESSION = Session(PROJECT, BASE / "experiment", network=not VALIDATION.get("offline", False),
                      model=VALIDATION.get("model"), model_error="Dependency installation failed; inspect install logs" if INSTALL_ERRORS else VALIDATION.get("model_error"))
    SESSION.failures.extend(INSTALL_ERRORS)
    for log in BASE.glob("*-install.txt"):
        SESSION.store.text(Path("diagnostics") / log.name, log.read_text())
    display(Markdown("**Hardware/model decision**"))
    display(SESSION.store.read("hardware_model_selection.json"))
    print("Run directory:", SESSION.run_root)
    ''')
    md('data-heading','''
    ## 3 · Acquire resources and validate provenance
    The notebook checks the suggested artifact endpoint and author group, validates pinned external resources by SHA-256, and parses public dataset containers. MCPTox, MCPSecBench and MCPCorpus are external resources, not the TRUSTDESC benchmark. Their availability, licenses and missing components are written to the acquisition report. Unknown/unlicensed external data is referenced rather than bundled. Public tool code is never imported on the host.
    ''')
    code('acquire','''
    ACQUISITION = SESSION.acquire()
    counts = {}
    for resource in ACQUISITION["resources"]:
        counts[resource["status"]] = counts.get(resource["status"], 0) + 1
    display(counts)
    print("Original benchmark recovered:", ACQUISITION["original_artifact_recovered"])
    print("Evaluated dataset:", SESSION.bundle["validation"])
    ''')
    md('model-heading','''
    ## 4 · Initialize the free local model
    The tokenizer and safetensors weights are loaded once from an immutable Hugging Face commit, with remote code disabled. Asset hashes, model settings and every prompt/raw response are recorded. Invalid responses get bounded format retries. An unavailable model produces explicit missing observations; it is never replaced with scripted semantic answers. Successful stage checkpoints remain recoverable.
    ''')
    code('initialize-model','''
    MODEL_MANIFEST = SESSION.initialize_model()
    display({key: value for key,value in MODEL_MANIFEST.items() if key != "runtime"})
    if MODEL_MANIFEST["status"] == "unavailable":
        print("Inference unavailable. Static analysis and honest missing-observation reports will continue.")
    ''')
    md('slicemin-heading','''
    ## 5 · SliceMin — reachable implementation and evidence
    Python source is analyzed without execution. Supported aliases, imports, nested functions, self/cls methods and unambiguous dispatcher callees are followed. Unresolved calls remain visible. Model-guided debloat proposals are saved; semantic changes lacking equivalence evidence are not silently accepted. TypeScript and general dynamic resolution remain limitations of this independent implementation.
    ''')
    code('slicemin','''
    STATIC = SESSION.workflow.static()
    display({tool: {"status":result["status"], "reachable_functions":len(result.get("slice",{}).get("functions",[])),
                   "unresolved_calls":len(result.get("slice",{}).get("unresolved_calls",[])),
                   "diagnostic":result.get("error", result.get("reason"))} for tool,result in STATIC.items()})
    ''')
    md('descgen-heading','''
    ## 6 · DescGen — grounded descriptions
    Comments/docstrings are removed, identifiers normalized and contextually filtered, and descriptions generated from the code. All prose is decomposed into claims. Source quotations must match actual implementation spans; input names, required flags and simple annotated types must match the entry signature. This is evidence validation, not a proof of semantic equivalence.
    ''')
    code('descgen','''
    DRAFTS = SESSION.workflow.descriptions()
    display({model:{tool:{"status":result["status"],"diagnostic":result.get("error",result.get("reason")),
                         "claims":len(result.get("draft",{}).get("description",{}).get("claims",[]))} for tool,result in tools.items()} for model,tools in DRAFTS.items()})
    ''')
    md('dynver-heading','''
    ## 7 · DynVer — execute, judge and refine
    A fixed task agent executes synthesized verification objectives against the authored tool allowlist. Claims are supported, refuted or inconclusive. Corrected descriptions must pass another execution/judging round. The offline container MCP transport stays disabled without a reviewed local image and successful isolation probes; missing infrastructure is not evidence that a claim is false. Read `tool_verification.json` for plans, rounds, decisions and uncertainty.
    ''')
    code('dynver','''
    VERIFIED = SESSION.workflow.verification()
    display({model:{tool:{"status":result["status"],"rounds":result.get("verification",{}).get("refinement_rounds"),
                         "usable_summary":result.get("verification",{}).get("usable_summary"),
                         "diagnostic":result.get("error",result.get("reason"))} for tool,result in tools.items()} for model,tools in VERIFIED.items()})
    display(SESSION.isolation)
    ''')
    md('evaluation-heading','''
    ## 8 · Matched original / lite / full evaluation
    The same eight authored tasks, tool set and task-agent model/revision/settings are reused across all conditions. A condition is unavailable if a required trusted description is missing. An exact trace oracle checks the requested authored objective and target call. **This automatic fixture metric is distinct from the paper's manually reviewed TSR.** Original paper TSR, adaptive attack success and tool-modification rates stay unavailable without their required observations.
    ''')
    code('evaluate','''
    TASK_RESULTS = SESSION.workflow.benchmark()
    from collections import Counter
    display(dict(Counter(result["status"] for result in TASK_RESULTS)))
    print("Fixed task agent:", SESSION.config["task_agent"]["model_id"], SESSION.config["task_agent"]["revision"])
    ''')
    md('validation-heading','''
    ## 9 · Software validation
    Unit and integration tests check software behavior separately from scientific evaluation. Output consistency, matched task-agent identity, provenance, checkpoint hashes and the ZIP member hashes are also checked before export. Tests do not supply labels for the original paper benchmark.
    ''')
    code('software-checks','''
    import unittest
    if not VALIDATION.get("skip_tests", False):
        test_log = BASE / "software-tests.txt"
        with test_log.open("w") as stream:
            test_result = subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-t","."], cwd=PROJECT,
                                         env={**os.environ,"PYTHONPATH":str(PROJECT/"src")}, stdout=stream, stderr=subprocess.STDOUT)
        SESSION.store.text("software_tests.txt",test_log.read_text())
        SESSION.store.write("software_test_status.json",{"returncode":test_result.returncode,"scope":"software tests, not research efficacy"})
        print(test_log.read_text()[-1600:])
        if test_result.returncode:
            SESSION.failures.append({"component":"software_tests","status":"failed","reason":"See software_tests.txt"})
    else:
        SESSION.store.write("software_test_status.json",{"status":"skipped_by_explicit_validation_harness"})
    ''')
    md('handover-heading','''
    ## 10 · Results, limitations and Phase 3 handover
    The reports distinguish completed observations, failed stages and missing original material. Generation time/tokens/API charges come only from saved calls. Runtime overhead uses the three-condition common-success intersection. Fixture Wilson intervals are descriptive references for authored tests, not population estimates. The package includes the exact source/configuration, dataset references, source slices, prompts, raw model records, traces, checkpoints, comparisons, manifests, reports and integrity hashes. Model caches, secrets, the private PDF and personal files are excluded.
    ''')
    code('package','''
    EXPORT = SESSION.finish()
    RESULTS = SESSION.results
    display(SVG(filename=str(SESSION.run_root / "plots/fixture_objectives.svg")))
    table = [r for r in RESULTS["conditions"] if r["tool"] == "ALL"]
    display(table)
    display(Markdown((SESSION.run_root / "PHASE2_COMPLETION_REPORT.md").read_text()))
    print("Output validation:", SESSION.store.read("validation_report.json")["valid"])
    print("ZIP verified:", EXPORT["sha256"])
    print("Indexed output files:", EXPORT["files"])
    display(Markdown("### Download handover and reports"))
    # Colab links are relative to /content and invoke the notebook file server.
    def result_link(path):
        path = Path(path).resolve()
        if Path("/content").exists() and path.is_relative_to(Path("/content")):
            from html import escape
            relative = path.relative_to("/content").as_posix()
            display(HTML(f'<a href="/files/{escape(relative)}" download target="_blank">{escape(path.name)}</a>'))
        else:
            display(FileLink(str(path)))
    result_link(EXPORT["archive"])
    result_link(EXPORT["checksum_file"])
    if not VALIDATION and SESSION.runtime["runtime_type"] == "colab":
        try:
            from google.colab import files
            files.download(EXPORT["archive"])
        except Exception as exc:
            print("Automatic browser download was unavailable; use the ZIP link above:", str(exc))
    from trustdesc.reproduction.report import REPORTS
    for report in REPORTS + ["results.json","validation_report.json","OUTPUT_INDEX.json"]:
        result_link(SESSION.run_root / report)
    print("Generated output groups (complete file list is linked as OUTPUT_INDEX.json):")
    output_names = SESSION.store.read("OUTPUT_INDEX.json")
    print("\\n".join(sorted({name.split("/")[0] + ("/" if "/" in name else "") for name in output_names})))
    display(Markdown("**Pipeline finished. Phase 2 scientific status: INCOMPLETE.** Read the completion report for missing original artifacts and any failed stages. Download the ZIP before the Colab VM is discarded. Rerun unchanged cells to reuse completed checkpoints and retry failed stages."))
    ''')
    nb={'cells':cells,'metadata':{'colab':{'name':'TRUSTDESC_REPRODUCTION.ipynb','provenance':[]},'accelerator':'GPU',
        'gpuClass':'standard','kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
        'language_info':{'name':'python','version':'3.11'},'trustdesc':{'source_revision':revision,'default_semantic_replay':False,'original_benchmark_available':False}},'nbformat':4,'nbformat_minor':5}
    for cell in cells:
        if cell['cell_type']=='code':compile(''.join(cell['source']),cell['id'],'exec')
    return nb


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--revision');args=parser.parse_args()
    revision=args.revision or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    notebook=build(revision)
    (ROOT/'TRUSTDESC_REPRODUCTION.ipynb').write_text(json.dumps(notebook,indent=1,ensure_ascii=False)+'\n')
    print('Built',len(notebook['cells']),'cells for source',revision)
