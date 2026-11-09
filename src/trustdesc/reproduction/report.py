"""Honest metrics, report generation, artifact validation and handover export."""
from __future__ import annotations
from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import zipfile
from trustdesc.common.io import digest
from trustdesc.experiments.export import export_results
from trustdesc.experiments.storage import Store, now

REPORTS = ['PHASE2_COMPLETION_REPORT.md', 'PHASE3_HANDOVER.md', 'METHODOLOGY.md', 'DATASET_PROVENANCE.md',
           'EXPERIMENT_RESULTS.md', 'LIMITATIONS_AND_REPRODUCIBILITY.md', 'REPRODUCTION_INSTRUCTIONS.md', 'FINAL_PROJECT_COMPLETION_REPORT.md']


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z*z/total
    center = (p + z*z/(2*total))/denominator
    half = z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))/denominator
    return [max(0, center-half)*100, min(1, center+half)*100]


def aggregate(records):
    rows = []
    generators = sorted({r['generator'] for r in records})
    for generator in generators:
        for variant in ['original', 'lite', 'full']:
            for tool in [None] + sorted({r['tool_id'] for r in records}):
                group = [r for r in records if r['generator'] == generator and r['variant'] == variant and (tool is None or r['tool_id'] == tool)]
                observed = [r for r in group if r['status'] in {'completed', 'failed'} and type(r.get('fixture_oracle', {}).get('success')) is bool]
                successes = sum(r['fixture_oracle']['success'] for r in observed)
                complete = bool(group) and len(observed) == len(group)
                rows.append({'generator': generator, 'variant': variant, 'tool': tool or 'ALL', 'expected_tasks': len(group),
                             'observed_tasks': len(observed), 'missing_tasks': len(group)-len(observed),
                             'completed_fixture_objectives': successes if observed else None,
                             'fixture_oracle_success_rate_percent': successes/len(group)*100 if complete else None,
                             'observed_subset_success_rate_percent': successes/len(observed)*100 if observed else None,
                             'descriptive_wilson95_percent': wilson(successes, len(observed)) if complete else None,
                             'paper_human_reviewed_TSR_percent': None,
                             'interval_caveat': 'Descriptive binomial reference only; eight related authored tasks are not a random population sample.'})
    return rows


def paired_overhead(records):
    rows = []
    for generator in sorted({r['generator'] for r in records}):
        lookup = {(r['task_id'], r['variant']): r for r in records if r['generator'] == generator}
        tasks = sorted({task for task, _ in lookup})
        intersection = [t for t in tasks if all(lookup.get((t,v), {}).get('fixture_oracle', {}).get('success') is True for v in ['original','lite','full'])]
        for variant in ['lite','full']:
            metrics = {}
            for field in ['latency_seconds', 'cost_usd', 'input_tokens', 'output_tokens']:
                pairs = [(lookup[(t,'original')].get(field), lookup[(t,variant)].get(field)) for t in intersection]
                if not pairs or any(type(a) not in {int,float} or type(b) not in {int,float} for a,b in pairs):
                    metrics[field] = None
                else:
                    base = statistics.mean(a for a,b in pairs)
                    metrics[field] = (statistics.mean(b for a,b in pairs)/base-1)*100 if base else None
            rows.append({'generator': generator, 'variant': variant, 'common_success_task_ids': intersection,
                         'relative_percent': metrics, 'scope': 'Synthetic oracle intersection; not original paper benchmark',
                         'aggregation': 'ratio of means; zero baseline cost makes relative cost undefined'})
    return rows


def write_csv(store, name, rows):
    if not rows:
        store.text(name, 'status\nno_observations\n')
        return
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(v) if isinstance(v, (dict,list)) else v for k,v in row.items()})
    store.text(name, stream.getvalue())


def analyze(workflow, acquisition, model_manifest, isolation, setup_failures=()):
    store = workflow.store
    records = store.read('evaluation_results.json')
    static, descriptions, verified = (store.read(name) for name in ['static_results.json','description_results.json','verification_results.json'])
    conditions = aggregate(records)
    overhead = paired_overhead(records)
    failures = [{'stage':'setup', **r} for r in setup_failures]
    for stage, data in [('SliceMin', {'static': static}), ('DescGen', descriptions), ('DynVer', verified)]:
        for model, tools in data.items():
            for tool, result in tools.items():
                if result['status'] != 'completed':
                    failures.append({'stage': stage, 'model': model, 'tool': tool, 'status': result['status'],
                                     'reason': result.get('error',result.get('reason'))})
    for r in records:
        if r['status'] != 'completed' or r.get('fixture_oracle',{}).get('success') is not True:
            failures.append({'stage': 'evaluation', 'model': r['generator'], 'tool': r['tool_id'],
                             'task':r['task_id'], 'condition':r['variant'], 'status':r['status'],
                             'reason': r.get('reason',r.get('error',r.get('trace',{}).get('reason','oracle_objective_not_observed')))})
    # Iteration-level observations and comparisons, never overwrite old evidence.
    traces, comparisons, assessments = [], [], []
    for model, tools in verified.items():
        for tid, result in tools.items():
            tool = workflow.tools[tid]
            row = {'model':model,'tool':tid,'original':tool['original_description'],'generated_draft':None,'full':None,'lite':None}
            draft = descriptions.get(model,{}).get(tid,{})
            if draft.get('status') == 'completed':
                row['generated_draft'] = draft['draft']['description']
            if result['status'] == 'completed':
                v = result['verification']
                row.update(full=v['full'],lite=v['lite'])
                decisions = Counter(d['verdict'] for d in v['decisions'])
                assessments.append({'model':model,'tool':tid,'claim_decisions':dict(decisions),'usable_summary':v['usable_summary'],
                                    'trust_assessment':'finite_behavioral_evidence_only; malware_safety_not_assessed',
                                    'confidence':'limited_fixture_observations' if tool['backend']=='controlled_fixture' else 'inconclusive_no_external_execution'})
                for history in v['history']:
                    for trace in history['verification']['traces']:
                        traces.append({'kind':'DynVer','model':model,'tool':tid,'round':history['round'],**trace})
            else:
                assessments.append({'model':model,'tool':tid,'trust_assessment':'not_assessed','reason':result.get('reason',result.get('error'))})
            comparisons.append(row)
    for record in records:
        if record.get('trace'):
            traces.append({'kind':'evaluation','task':record['task_id'],'condition':record['variant'],'model':record['generator'],'trace':record['trace']})
    store.text('execution_traces.jsonl',''.join(json.dumps(t,ensure_ascii=False,allow_nan=False)+'\n' for t in traces))
    store.write('description_comparisons.json',comparisons)
    store.write('tool_verification.json',{'verification':verified,'assessments':assessments})
    calls = [store.read(name) for name in store.read('OUTPUT_INDEX.json') if name.startswith('calls/') and name.endswith('.json')]
    generation = []
    generation_calls = [c for c in calls if c.get('context',{}).get('stage') != 'benchmark_fixed_agent']
    for stage in sorted({c['stage'] for c in generation_calls}):
        group = [c for c in generation_calls if c['stage']==stage]
        def total(field):
            vals=[c.get(field) for c in group]
            return sum(vals) if vals and all(type(v) in {int,float} for v in vals) else None
        generation.append({'stage':stage,'calls':len(group),'failed_calls':sum(c['status']!='completed' for c in group),
                           'seconds':total('seconds'),'input_tokens':total('input_tokens'),'output_tokens':total('output_tokens'),
                           'api_cost_usd':total('cost_usd'),'compute_cost_usd':None})
    blockers = ['Original 52-tool/208-task release, labels, traces and exact prompts not recovered.',
                'Original generation models and fixed Gemini-3-Flash task agent replaced by explicitly named free local model.',
                'Python AST subset; TypeScript, unrestricted dynamic dispatch and proof of slicing equivalence unavailable.',
                'Full external MCP transport is gated by a validated immutable-image backend; the separate macOS boundary supports offline Python source observations only.',
                'Finite authored fixture observations and automated oracles do not establish original human-reviewed TSR.',
                'Q3 degraded-tool competition, Q4 seven original attacks and Q5 adaptive naming experiments lack authenticated experimental artifacts.']
    results = {'schema_version':1,'created_at':now(),'scope':'independent_partial_reproduction',
               'phase2_complete':False,'pipeline_finished':True,'scientific_reproduction_complete':False,
               'conditions':conditions,'paired_overhead':overhead,'generation_measurements':generation,
               'task_results':records,'tool_assessments':assessments,'failure_analysis':failures,'blockers':blockers,
               'paper_reference_only':{'original_tasks':208,'original_tools':52,'baseline_completed':175,'baseline_TSR_percent':84.1,
                                       'mean_full_TSR_percent':87.7,'mean_lite_TSR_percent':86.3,
                                       'source':'arXiv:2604.07536v1 Table 2; not measured in this run'},
               'attack_success_rate':None,'tool_modification_rate':None,'paper_TSR_percent':None}
    store.write('results.json',results)
    store.write('model_manifest.json',model_manifest)
    store.write('dataset_manifest.json',{'dataset_hash':digest(workflow.bundle),'dataset':workflow.bundle,
                                        'validation':workflow.bundle.get('validation'),'resource_report':acquisition})
    store.write('prompt_manifest.json',{'prompts':store.read('prompt_versions.json'),'grounding_and_refinement':_evidence_prompts(),
                                       'origin':'independently_reconstructed_not_author_prompts'})
    store.write('isolation_report.json',isolation)
    write_csv(store,'metrics.csv',conditions)
    write_csv(store,'generation_measurements.csv',generation)
    write_csv(store,'task_results.csv',[{k:r.get(k) for k in ['generator','variant','task_id','tool_id','status','task_agent_id','fixture_oracle','latency_seconds']} for r in records])
    _chart(store,conditions)
    _documents(workflow,results,acquisition,model_manifest)
    return results


def _evidence_prompts():
    from .evidence import GROUND,REFINE,GENERATE_COMPACT
    return {'GROUND':GROUND,'REFINE':REFINE,'GENERATE_COMPACT':GENERATE_COMPACT,
            'hashes':{k:digest(v) for k,v in {'GROUND':GROUND,'REFINE':REFINE,'GENERATE_COMPACT':GENERATE_COMPACT}.items()}}


def _chart(store,conditions):
    rows=[r for r in conditions if r['tool']=='ALL']
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="820" height="330" viewBox="0 0 820 330">',
           '<rect width="820" height="330" fill="#f7f9fc"/>',
           '<text x="28" y="35" font-family="sans-serif" font-size="21" fill="#153750">Authored fixture objectives by description condition</text>']
    from html import escape
    for i,row in enumerate(rows):
        y=80+i*65
        value=row['fixture_oracle_success_rate_percent']
        label=f"{row['variant']} • {row['observed_tasks']}/{row['expected_tasks']} observed"
        parts.append(f'<text x="28" y="{y}" font-family="sans-serif" font-size="15">{escape(label)}</text>')
        if value is not None:
            parts.append(f'<rect x="285" y="{y-18}" width="{value*4:.2f}" height="27" rx="4" fill="#277e91"/><text x="705" y="{y}" font-family="sans-serif" font-size="15">{value:.1f}%</text>')
        else:
            parts.append(f'<text x="285" y="{y}" font-family="sans-serif" font-size="15" fill="#986832">Missing observations — no score</text>')
    parts.append('<text x="28" y="302" font-family="sans-serif" font-size="12" fill="#566">Synthetic software/agent checks. No original paper TSR measured.</text></svg>')
    store.text('plots/fixture_objectives.svg',''.join(parts))


def _documents(workflow,results,acquisition,models):
    store=workflow.store
    blockers='\n'.join('- '+v for v in results['blockers'])
    observed=sum(r['status']=='completed' for r in results['task_results'])
    phase=f'''# Phase 2 status: INCOMPLETE

The automatic pipeline finished and produced a handover package. This is an independent, partial reimplementation. It is not the authors' released implementation or a completed quantitative reproduction.

{observed}/{len(results['task_results'])} task attempts completed in this run. These are authored fixture tasks, not the original 208 tasks. Consult results.json for actual outcomes and missing observations. A generated report or ZIP does not establish scientific completion.

## Outstanding essential evidence

{blockers}

## Delivered implementation

Automatic source acquisition, conservative SliceMin, local-model DescGen with exact-source attribution and interface checks, iterative DynVer, a fixed task agent across original/lite/full, explicit fixture oracles, checkpoints, validation, reports and an integrity-indexed ZIP. Failed scientific stages are recorded; no replay substitutes for a failed model.
'''
    store.text('PHASE2_COMPLETION_REPORT.md',phase)
    store.text('PHASE3_HANDOVER.md',f'''# Phase 3 handover

Start with PHASE2_COMPLETION_REPORT.md and validation_report.json. The experiment fingerprint is `{workflow.fingerprint}`. Original Phase 2 scientific completion is blocked by the evidence below; Phase 3 must not assume it is complete.

{blockers}

## Package inventory

- results.json, metrics.csv and task_results.csv: measured or missing observations with explicit scope.
- dataset_manifest.json, acquisition_report.json, source_hashes.json: dataset/source identity, licenses and acquisition errors.
- model_manifest.json, prompt_manifest.json, config.json, environment.json, installed_packages.txt: model/settings/prompts/runtime.
- slices/, static_results.json, description_results.json and tool_verification.json: source reachability, drafts, tasks, decisions and refinement history.
- execution_traces.jsonl, calls/, checkpoints/: actual events, raw model outputs, errors and recoverable stage records.
- reproduction_source/: exact project source/configuration needed to rerun; no model weights or external caches.
- artifact_hashes.json: complete member hashes; the outer archive also has an independent .sha256 sidecar.

## Resume and extend

Rerun the unchanged notebook in the same runtime to reuse successful hash-bound checkpoints and retry failed stages. New source/model/runtime settings create a separate run. Local checkpoints persist under the notebook workspace. Optional Colab disk is ephemeral; download its ZIP before discarding the VM. Restore with trustdesc.experiments.export.restore_results(archive, expected_sha256, destination) to inspect the run evidence.

Recover and authenticate original tool/task/prompt/label/trace artifacts before original-benchmark evaluation. Verify rights and license before redistribution. Supply a reviewed immutable container image/source attestation on a Linux Docker host, validate probes and actual integration, then enable the external adapter. Unknown source must never execute outside a validated isolation boundary. Keep the task agent fixed while comparing generator models. Perform original human trace review separately from the fixture oracle. Record exact mutations/tasks for Q3–Q5 before computing attack or selection rates.
''')
    store.text('METHODOLOGY.md','''# Methodology

Reference: Ye, Zhang, Jia and Hong Hu, TRUSTDESC, arXiv:2604.07536v1, §§4–5. Existing docs/PAPER_ANALYSIS.md and reports/published_results.csv preserve the paper analysis/reference values.

SliceMin parses Python without importing it, identifies decorator/explicit registrations or an unambiguous dispatcher callee, traverses cross-file imports, supported aliases, lexical nested functions and self/cls methods. Builtins/external/dynamic calls remain unresolved. Class/context and optional branches are conservative; this is not the authors' tree-sitter implementation. Model debloat proposals are recorded; semantic changes without equivalence evidence are not silently accepted or deployed.

DescGen strips comments/docstrings, enforces 20-character collision-checked identifier normalization, uses a contextual model filter and synthesizes summary, functionalities and input schema. Every prose field has one claim. Generated argument names/required flags/simple annotated types must match the implementation signature. Exact source quotes are validated against file hashes and source spans; model attribution is not a semantic proof. Invalid outputs receive bounded retries and remain recorded failures if invalid.

DynVer generates tasks, executes them using a fixed task agent, collects actual observations and separately judges claims as supported/refuted/inconclusive. Incorrect claims can produce a correction candidate; every candidate is executed and judged again. Nonverifiable/inconclusive claims are removed. Lite removes only functionalities/claim bookkeeping after full refinement. Return values and side effects are captured in code evidence/claims/traces when generated; no universal side-effect or return-schema certification is asserted.

Default dynamic observations come from two bounded project-authored pure tools. This is real fixture execution and not external MCP execution or replay. The offline immutable-image MCP transport requires explicit permission and successful isolation checks; absent infrastructure stays disabled. No paid model/API is configured.

Evaluation uses one unchanged task set and one fixed task-agent model/revision/settings for original/lite/full. Fixture objectives are checked by independently authored exact event oracles, including requested validation errors. These checks are not human-reviewed original-benchmark TSR. Missing attempts are shown separately; full-condition rates are null when observations are incomplete. Generation time/tokens/API charges are aggregated only from recorded calls; local compute cost is unknown. Relative overhead uses the three-condition common-success intersection and ratio of arithmetic means. Zero baseline cost yields undefined relative cost. Descriptive Wilson intervals for authored fixtures do not support population claims. No adaptive attack rate or tool-modification rate is computed without observations.
''')
    ledger=acquisition['resources']
    lines=['# Dataset provenance','',workflow.bundle['provenance'],'','| Resource | Status | Class | License |','|---|---|---|---|']
    for r in ledger:
        lines.append('| '+ ' | '.join(str(r.get(k,'unknown')).replace('|','/').replace('\n',' ') for k in ['name','status','classification','license'])+' |')
    lines+=['','Exact URLs, revisions, hashes and missing components are in acquisition_report.json. External JSON container validation does not authenticate original TRUSTDESC membership. No external labels are guessed. Unlicensed resources are referenced by hash/URL and not bundled.']
    store.text('DATASET_PROVENANCE.md','\n'.join(lines)+'\n')
    lines=['# Experiment results','','Original paper results are reference-only: baseline 175/208 (84.1%), mean lite 86.3%, mean full 87.7% (Table 2). No difference-to-paper score is meaningful under this independent fixture/model setting.','','| Condition | Observed / expected | Authored fixture successes | Fixture rate | Paper TSR |','|---|---|---|---|---|']
    for r in results['conditions']:
        if r['tool']=='ALL':
            rate=r['fixture_oracle_success_rate_percent']
            lines.append(f"| {r['variant']} | {r['observed_tasks']}/{r['expected_tasks']} | {r['completed_fixture_objectives']} | {rate if rate is not None else 'unavailable'} | unavailable |")
    lines+=['','Per-tool results, failure analysis, common-success overhead, actual call time/tokens and uncertainty are in results.json and the CSV files. plots/fixture_objectives.svg visualizes only observed fixture rates. Unavailable conditions are not replaced with baseline descriptions. Paired tasks/conditions are constant; condition scheduling is deterministic and not randomized, so timings are descriptive.','',f"Recorded failures or missing objectives: {len(results['failure_analysis'])}."]
    store.text('EXPERIMENT_RESULTS.md','\n'.join(lines)+'\n')
    store.text('LIMITATIONS_AND_REPRODUCIBILITY.md',f'''# Limitations and reproducibility

{blockers}

## Honest execution status

Actual execution environment, hardware, dependencies and code hashes are in environment.json, installed_packages.txt and EXPERIMENT_MANIFEST.json. Read the delivery validation evidence for which tests actually ran on the developer host. No real Colab T4 execution is claimed unless a future run manifest records it. A CPU path uses a smaller model and records that substitution; it may be slow or fail structured-generation checks. A local-model download or inference failure does not become a scripted response. Baseline fixture evaluation can proceed independently of failed DescGen/DynVer stages.

## Reproducibility scope

Fixed immutable source/model revisions, resource SHA-256, seeds, per-request prompts/raw outputs and hash-bound checkpoints make identity auditable. CUDA/PyTorch sampling is not guaranteed bit-identical across hardware/versions. Direct dependencies are pinned; the installed full transitive environment is captured, not claimed to be a universal cross-platform lock. Cache files are integrity checked; partial/corrupt resource files are quarantined and acquired again. Output exports use a registered-file allowlist and secret-pattern checks. Model weights, private PDF, user files and external caches are excluded.

The threat model assumes accessible source and no overtly malicious runtime implementation. Finite tests do not certify safety, absence of malicious code, or universal semantic equivalence. Containers share the host kernel and are not a VM. Current container integration and T4 inference require validation on their actual infrastructure. Ordinary fixture execution is never described as an untrusted-code sandbox.
''')
    store.text('REPRODUCTION_INSTRUCTIONS.md','''# Run the local notebook

1. Open TRUSTDESC_REPRODUCTION.ipynb in local Jupyter on the Mac and choose Run All.
2. The notebook verifies its embedded source, creates a local Python environment, installs the pinned Apple dependency lock, and tests Python startup before loading a model.
3. Read the qualification and stage statuses. The same free quantized task agent is held fixed across Original / lite / full. Invalid model responses remain recorded failures.
4. Download phase3_handover.zip and its SHA-256 sidecar from the final cell. Read FINAL_PROJECT_COMPLETION_REPORT.md before interpreting the results.

No source uploads, API keys, configuration edits or manual human labels are required for the authored-fixture workflow. Rerun unchanged cells to reuse successful hash-bound checkpoints; changed code/model/runtime/source/configuration uses a new run identity. Local files persist until removed by the operator. Optional Colab entry points are retained under notebooks/colab; its disk is ephemeral.

Apple Silicon uses the qualified MLX model subject to memory constraints. MPS and CPU adapters are available with explicit device/substitution records. Original benchmark claims remain unavailable without authenticated tools/tasks/prompts/labels/traces. External execution requires a validated boundary; default fixture execution is not an untrusted-code sandbox.
''')
    lines=['# Final project completion report', '',
           'Status: working independent pipeline; original scientific reproduction INCOMPLETE.', '',
           f'Run identity: `{workflow.root.name}`. Fingerprint: `{workflow.fingerprint}`.', '',
           f'Model status: {models.get("status")}; inference mode: {models.get("mode")}.', '',
           '## Actual execution', '',
           '| Condition | Observed / expected | Authored objectives achieved | Fixture rate |',
           '|---|---|---|---|']
    for row in results['conditions']:
        if row['tool']=='ALL':
            lines.append(f"| {row['variant']} | {row['observed_tasks']}/{row['expected_tasks']} | {row['completed_fixture_objectives']} | {row['fixture_oracle_success_rate_percent']} |")
    test_file=store.root/'software_test_status.json'
    test_status=store.read('software_test_status.json') if test_file.exists() else {'status':'not_executed_by_this_session'}
    lines += ['', 'These are authored exact-trace objectives, not original paper TSR. Failed and missing attempts remain explicit. Repeated software-validation runs are not pooled as independent research samples.', '',
              '## Validation and evidence', '', json.dumps(test_status,indent=2), '',
              'Read source_hashes.json, model_manifest.json, prompt_manifest.json, acquisition_report.json, raw calls, checkpoints and execution_traces.jsonl. The exporter checks required artifacts and member hashes. A package is a handover, not evidence of scientific completion.', '',
              '## Implementation and remaining work', '',
              'Python SliceMin, real model DescGen, source attribution, iterative DynVer, fixed-agent fixture evaluation, checkpoints and portable report export are implemented within their documented scope. Model substitutions, approximate static resolution and finite model-judged observations limit the claims.', '', blockers, '',
              'Git publication and wider project handover status are recorded by the delivery agent separately; this notebook does not push repositories or claim publication. Supplementary public-example observations, when run, are separate from the authored benchmark.']
    store.text('FINAL_PROJECT_COMPLETION_REPORT.md','\n'.join(lines)+'\n')



def validate_and_package(workflow, destination):
    store=workflow.store
    required=REPORTS+['results.json','EXPERIMENT_MANIFEST.json','dataset_manifest.json','model_manifest.json','prompt_manifest.json',
                      'source_hashes.json','config.json','execution_traces.jsonl','tool_verification.json','acquisition_report.json',
                      'environment.json','installed_packages.txt','metrics.csv','description_comparisons.json']
    errors=[]
    for name in required:
        path=store.root/name
        if not path.is_file(): errors.append('Missing '+name)
        elif name.endswith('.json'):
            try:json.loads(path.read_text())
            except ValueError:errors.append('Invalid JSON '+name)
    for name in store.read('OUTPUT_INDEX.json'):
        if name.endswith('/state.json'):
            state=store.read(name)
            result=store.root/Path(name).parent/'result.json'
            if state.get('result_sha256') and hashlib.sha256(result.read_bytes()).hexdigest()!=state['result_sha256']:
                errors.append('Checkpoint mismatch '+name)
    results=store.read('results.json')
    agents={(r['task_agent_id'],r['task_agent_revision']) for r in results['task_results']}
    if len(agents)!=1:errors.append('Task agent varied across conditions')
    if any(r.get('paper_TSR_eligible') for r in results['task_results']):errors.append('Synthetic task mislabeled paper eligible')
    validation={'valid':not errors,'errors':errors,'required_files':required,'fixed_task_agent':len(agents)==1,
                'original_paper_TSR_computed':False,'phase2_complete':False,'scope':'artifact/software consistency, not scientific efficacy',
                'scientific_stage_failures':len(results['failure_analysis'])}
    store.write('validation_report.json',validation)
    if errors:raise ValueError('Output validation failed: '+'; '.join(errors))
    hashes={n:hashlib.sha256((store.root/n).read_bytes()).hexdigest() for n in store.read('OUTPUT_INDEX.json') if n not in {'artifact_hashes.json','OUTPUT_INDEX.json'}}
    store.write('artifact_hashes.json',hashes)
    exported=export_results(workflow.root,Path(destination)/'phase3_handover.zip')
    with zipfile.ZipFile(exported['archive']) as z:
        if z.testzip():raise ValueError('Handover ZIP CRC failure')
        manifest=json.loads(z.read('EXPORT_MANIFEST.json'))
        if any(hashlib.sha256(z.read(n)).hexdigest()!=h for n,h in manifest['files'].items()):
            raise ValueError('Handover member hash mismatch')
    return exported
