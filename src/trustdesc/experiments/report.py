from __future__ import annotations
from collections import Counter,defaultdict
import csv
import io
import json
import os
from pathlib import Path
from statistics import mean
import tempfile

from trustdesc.evaluation import summarize,overhead
from .review import latest_reviews,review_template
from .storage import Store,now


def csv_text(rows,fields):
    s=io.StringIO();w=csv.DictWriter(s,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows);return s.getvalue()


def analyze(run_root):
    store=Store(run_root);manifest=store.read('EXPERIMENT_MANIFEST.json');config=store.read('config.json')
    bundle=store.read('dataset.json');records=store.read('task_predictions.json');reviews=latest_reviews(run_root)
    groups=defaultdict(list);joined=[]
    for r in records:
        label=reviews.get(r['result_id'])
        if label and (label['evidence_hash']!=r['evidence_hash'] or label['run_fingerprint']!=r['run_fingerprint']):label=None
        item={**r,'human_review':label,'reviewed':bool(label),
              'target_invoked':label['target_invoked'] if label else None,
              'objective_achieved':label['objective_achieved'] if label else None}
        joined.append(item);groups[(r['model'],r['variant'])].append(item)
    summary=[];complete_metrics=[];overheads=[]
    for (model,variant),rows in sorted(groups.items()):
        intended=[r for r in rows if r['backend']=='controlled_fixture']
        reviewed=[r for r in intended if r['human_review']]
        complete=bool(intended) and len(reviewed)==len(intended) and all(r.get('trace') for r in intended)
        metric_rows=[{k:r[k] for k in ['task_id','model','variant','run_id','reviewed','target_invoked','objective_achieved','latency_seconds','input_tokens','output_tokens','cost_usd','tool_calls'] if k in r} for r in reviewed]
        tsr=summarize(metric_rows,expected_tasks=[r['task_id'] for r in intended])[0]['TSR_percent'] if complete else None
        if complete:complete_metrics.extend(metric_rows)
        def avg(k):
            vals=[r.get(k) for r in rows if r.get('trace')]
            return mean(vals) if vals and all(type(v) in {int,float} for v in vals) else None
        summary.append({'model':model,'variant':variant,'tasks_total':len(rows),'eligible_controlled_tasks':len(intended),
                        'executed':sum(bool(r.get('trace')) for r in rows),'reviewed':len(reviewed),
                        'condition_complete_for_reviewed_scope':complete,'TSR_percent':tsr,
                        'mean_latency_seconds':avg('latency_seconds'),'mean_cost_usd':avg('cost_usd'),
                        'mean_input_tokens':avg('input_tokens'),'mean_output_tokens':avg('output_tokens'),
                        'scope':'Controlled fixture subset only; synthetic/reconstructed, never original 208',
                        'model_mode':next((r.get('model_mode') for r in rows if r.get('model_mode')),None)})
    for cfg in config['models']:
        conditions=[s for s in summary if s['model']==cfg['id']]
        if len(conditions)==3 and all(s['condition_complete_for_reviewed_scope'] for s in conditions):
            overheads.extend(overhead([r for r in complete_metrics if r['model']==cfg['id']]))
    failures=Counter(r.get('error_type') or r.get('trace',{}).get('reason') or r.get('reason') or r['status'] for r in records if r['status']!='completed')
    stages={name:store.read(name+'.json') for name in ['static_results','description_results','verification_results'] if (store.root/(name+'.json')).exists()}
    tool_rows=[]
    for cfg in config['models']:
        for t in bundle['tools']:
            static=stages.get('static_results',{}).get(t['id'],{})
            row={'model':cfg['id'],'tool_id':t['id'],'origin':t['origin'],'backend':t['backend'],'static_status':static.get('status'),
                 'descgen_status':stages.get('description_results',{}).get(cfg['id'],{}).get(t['id'],{}).get('status'),
                 'dynver_status':stages.get('verification_results',{}).get(cfg['id'],{}).get(t['id'],{}).get('status'),
                 'reachable_functions':len(static.get('slice',{}).get('functions',[])) if static.get('slice') else None,
                 'unresolved_calls':len(static.get('slice',{}).get('unresolved_calls',[])) if static.get('slice') else None}
            tool_rows.append(row)
    per_tool=[]
    for key in sorted({(r['model'],r['variant'],r['tool_id']) for r in joined}):
        rows=[r for r in joined if (r['model'],r['variant'],r['tool_id'])==key]
        complete=bool(rows) and all(r['reviewed'] and r.get('trace') for r in rows)
        per_tool.append({'model':key[0],'variant':key[1],'tool_id':key[2], 'TSR_percent':100*sum(r['target_invoked'] and r['objective_achieved'] for r in rows)/len(rows) if complete else None,'reviewed':sum(r['reviewed'] for r in rows),'tasks':len(rows)})
    gaps=['Exact original implementation/52 selections/208 tasks/prompts/labels/model versions not recovered.',
          'No validated isolated external MCP/LangChain runtime; external execution blocked.',
          'Python subset only; no validated TypeScript or complete dynamic resolution.',
          'Replay measures software mechanics, not LLM efficacy. Alternative models are not paper models.',
          'TSR withheld until all eligible condition tasks have explicit human review; no model self-assessment used.',
          'Paper values are reference only; no numeric published-versus-measured difference is meaningful for fixtures.',
          'Actual Colab/GPU/model inference not validated by local notebook compilation.']
    result={'schema_version':1,'run_id':manifest['run_id'],'fingerprint':manifest['fingerprint'],'generated_at':now(),
            'origin':bundle['origin'],'full_scientific_reproduction':False,'conditions':summary,'overheads':overheads,
            'per_tool':per_tool,'failure_breakdown':dict(failures),'reviewed_results':len(reviews),
            'predictions':joined,'tool_coverage':tool_rows,'reproduction_gaps':gaps,
            'dataset_inventory':{'initial_tasks':len(bundle['tasks']),'effective_tasks':len({r['task_id'] for r in records}),
                                 'tools':len(bundle['tools']),'origin_counts':dict(Counter(t.get('origin',bundle['origin']) for t in bundle['tasks']))}}
    validate_output(result)
    store.write('EXPERIMENT_RESULTS.json',result);store.write('FAILURE_ANALYSIS.json',{'task_failures':dict(failures),'stage_results':stages})
    store.write('REVIEWED_RESULTS.json',[r for r in joined if r['reviewed']])
    store.write('reproduction_gaps.json',gaps)
    store.text('TASK_RESULTS.csv',csv_text(joined,['result_id','evidence_hash','model','variant','task_id','tool_id','dataset_origin','status','reviewed','target_invoked','objective_achieved','observed_target_invoked','latency_seconds','input_tokens','output_tokens','cost_usd','tool_calls']))
    store.text('TOOL_RESULTS.csv',csv_text(tool_rows,list(tool_rows[0]) if tool_rows else ['tool_id','status']))
    store.text('METRICS_SUMMARY.csv',csv_text(summary,list(summary[0]) if summary else ['model','variant','TSR_percent']))
    store.text('DATASET_INVENTORY.csv',csv_text([result['dataset_inventory']],list(result['dataset_inventory'])))
    registry=store.read('model_registry.json')['models'] if (store.root/'model_registry.json').exists() else config['models']
    model_rows=[{'id':m['id'],'provider':m['provider'],'model_id':m.get('model_id'),'paper_name':m.get('paper_name'),
                 'selected':m['id'] in {c['id'] for c in config['models']},'classification':m.get('classification'),
                 'status':'See measured condition/stage records' if m['id'] in {c['id'] for c in config['models']} else 'not selected; no execution'} for m in registry]
    store.text('MODEL_CONFIGURATIONS.csv',csv_text(model_rows,['id','provider','model_id','paper_name','selected','classification','status']))
    store.text('PER_TOOL_RESULTS.csv',csv_text(per_tool,list(per_tool[0]) if per_tool else ['tool_id','TSR_percent']))
    store.text('RUNTIME_OVERHEAD.csv',csv_text([{'model':r['model'],'variant':r['variant'],'matched_tasks':len(r['matched_successful_tasks']),**r['relative_percent']} for r in overheads],['model','variant','matched_tasks','latency_seconds','cost_usd','input_tokens','output_tokens','tool_calls']))
    plots=make_plots(store,summary,per_tool,failures)
    store.write('plot_inventory.json',plots)
    lines=['# Colab experiment report','',f"Run: {manifest['run_id']}; fingerprint: {manifest['fingerprint']}",'',
           '**Not a complete scientific TRUSTDESC reproduction.** Conditions use the declared fixture/reconstructed/original-candidate provenance. Original paper values are not measurements here.','',
           '## Dataset and execution coverage','',json.dumps(result['dataset_inventory'],indent=2),'',
           '## Original / lite / full conditions','',
           '| Model | Condition | Total | Executed | Reviewed | TSR (%) | Mean latency (s) | Mean actual API cost (USD) |',
           '|---|---|---:|---:|---:|---|---|---|']
    for r in summary:
        show=lambda v:'Not available / incomplete' if v is None else f'{v:.6g}'
        lines.append(f"| {r['model']} | {r['variant']} | {r['tasks_total']} | {r['executed']} | {r['reviewed']} | {show(r['TSR_percent'])} | {show(r['mean_latency_seconds'])} | {show(r['mean_cost_usd'])} |")
    lines+=['','TSR requires target invocation AND objective success, with complete human-reviewed eligible task coverage. Unreviewed predictions remain separate. Overheads use the three-way success intersection; unknown costs and zero baselines do not produce invented ratios. Replay has zero API billing but no model inference.','',
            '## Failures','',json.dumps(dict(failures),indent=2),'','## Reproduction gaps','']+['- '+g for g in gaps]
    lines+=['','## Plots','']+['- '+str(p) for p in plots]
    store.text('COLAB_EXPERIMENT_REPORT.md','\n'.join(lines)+'\n')
    review_template(store.root)
    return result


def validate_output(result):
    from trustdesc.common.io import ValidationError
    if result.get('schema_version')!=1 or result.get('full_scientific_reproduction') is not False:raise ValidationError('Invalid experiment output identity')
    if len({r['result_id'] for r in result['predictions']})!=len(result['predictions']):raise ValidationError('Duplicate task outputs')
    for r in result['conditions']:
        value=r['TSR_percent']
        if value is not None and (not r['condition_complete_for_reviewed_scope'] or not 0<=value<=100):raise ValidationError('Unreviewed/incomplete success metric cannot be published')
    return True


def make_plots(store,summary,per_tool,failures):
    os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'trustdesc-matplotlib'))
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:return [{'status':'unavailable','reason':'matplotlib is not installed; install notebook CPU requirements and rerun analysis'}]
    plots=[]
    specs=[('task_success','TSR_percent','Human-reviewed task success (%)',summary),
           ('latency','mean_latency_seconds','Mean observed benchmark latency (s)',summary),
           ('cost','mean_cost_usd','Mean actual API cost (USD), replay has no inference',summary),
           ('per_tool','TSR_percent','Human-reviewed per-tool task success (%)',per_tool),
           ('model_comparison','TSR_percent','Configuration/condition comparison: reviewed fixture scope',summary)]
    for name,field,title,rows in specs:
        valid=[r for r in rows if r.get(field) is not None]
        if not valid:plots.append({'plot':name,'status':'no_valid_measurements'});continue
        labels=[r['model']+'/'+r['variant']+('/'+r['tool_id'] if 'tool_id'in r else '') for r in valid]
        fig,ax=plt.subplots(figsize=(max(7,len(valid)*.8),4.5));ax.bar(labels,[r[field] for r in valid],color='#286891')
        ax.set_title(title);ax.tick_params(axis='x',rotation=45);ax.grid(axis='y',alpha=.2)
        fig.text(.5,.01,'Declared synthetic/reconstructed scope; missing/incomplete measurements are omitted. Not paper efficacy.',ha='center',fontsize=8)
        fig.tight_layout(rect=[0,.05,1,1]);relative=Path('plots')/(name+'.png');(store.root/relative).parent.mkdir(exist_ok=True)
        fig.savefig(store.root/relative,dpi=140);plt.close(fig);store.track(relative);plots.append({'plot':name,'status':'measured','path':str(relative)})
    if failures:
        fig,ax=plt.subplots(figsize=(9,4));ax.barh(list(failures),list(failures.values()));ax.set_title('Recorded failure/unavailability categories');fig.tight_layout()
        relative=Path('plots/failures.png');(store.root/relative).parent.mkdir(exist_ok=True);fig.savefig(store.root/relative,dpi=140);plt.close(fig);store.track(relative);plots.append({'plot':'failures','status':'measured','path':str(relative)})
    else:plots.append({'plot':'failures','status':'no_recorded_failures'})
    return plots
