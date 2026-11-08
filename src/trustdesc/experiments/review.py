from __future__ import annotations
import csv
import io
import json
from pathlib import Path
import uuid

from trustdesc.common.io import digest, ValidationError
from .storage import Store, now


def review_template(run_root):
    store=Store(run_root);records=store.read('task_predictions.json')
    text=io.StringIO();fields=['result_id','evidence_hash','model','variant','task_id','observed_target_invoked','reviewed','target_invoked','objective_achieved','reviewer']
    w=csv.DictWriter(text,fieldnames=fields);w.writeheader()
    for r in records:
        w.writerow({k:r.get(k,'') for k in fields if k not in {'reviewed','target_invoked','objective_achieved','reviewer'}}|{'reviewed':'false'})
    store.text('REVIEW_TEMPLATE.csv',text.getvalue());return records


def submit_review(run_root,result_id,*,target_invoked,objective_achieved,reviewer,confirmed=False,evidence_hash=None):
    store=Store(run_root)
    if not confirmed or not isinstance(reviewer,str) or not reviewer.strip():raise ValidationError('Explicit human review confirmation and reviewer name are required')
    if type(target_invoked) is not bool or type(objective_achieved) is not bool:raise ValidationError('Review decisions must be booleans')
    records=store.read('task_predictions.json');r=next((x for x in records if x['result_id']==result_id),None)
    if not r or (evidence_hash and r['evidence_hash']!=evidence_hash):raise ValidationError('Review does not match current task evidence')
    if not r.get('trace') or r['status'] in {'blocked','unavailable'}:raise ValidationError('Unavailable execution cannot be converted into a measured success/failure')
    if target_invoked and not r.get('observed_target_invoked'):raise ValidationError('Trace contains no target invocation; cannot label it invoked')
    review={'result_id':result_id,'evidence_hash':r['evidence_hash'],'run_fingerprint':r['run_fingerprint'],
            'reviewed':True,'target_invoked':target_invoked,'objective_achieved':objective_achieved,
            'reviewer':reviewer,'review_origin':'explicit_human_input_attestation_not_model_self_assessment','timestamp':now()}
    store.write(Path('reviews')/(uuid.uuid4().hex+'.json'),review)
    return review


def import_reviews(run_root,csv_path):
    count=0
    with Path(csv_path).open(newline='') as f:
        for row in csv.DictReader(f):
            if row.get('reviewed','').lower()!='true':continue
            for field in ['target_invoked','objective_achieved']:
                if row.get(field,'').lower() not in {'true','false'}:raise ValidationError('Reviewed CSV booleans must be true/false')
            submit_review(run_root,row['result_id'],target_invoked=row['target_invoked'].lower()=='true',
                          objective_achieved=row['objective_achieved'].lower()=='true',reviewer=row.get('reviewer'),
                          confirmed=True,evidence_hash=row.get('evidence_hash'))
            count+=1
    return count


def latest_reviews(run_root):
    result={};root=Path(run_root)
    for name in Store(root).read('OUTPUT_INDEX.json'):
        if not name.startswith('reviews/') or not name.endswith('.json'):continue
        r=json.loads((root/name).read_text())
        if r['result_id'] not in result or r['timestamp']>result[r['result_id']]['timestamp']:result[r['result_id']]=r
    return result


def review_widget(run_root):
    """Optional notebook UI. Never derives objective success from model answers."""
    import ipywidgets as W
    from IPython.display import display
    records=review_template(run_root)
    available=[r for r in records if r.get('trace') and r['status'] not in {'blocked','unavailable'}]
    if not available:
        print('No executed tasks to review. Inspect failure/unavailable records.');return
    selector=W.Dropdown(options=[(f"{r['model']} / {r['variant']} / {r['task_id']}",r['result_id']) for r in available],description='Task')
    evidence=W.Output();target=W.Dropdown(options=[('Unreviewed',None),('Yes',True),('No',False)],description='Target called')
    objective=W.Dropdown(options=[('Unreviewed',None),('Yes',True),('No',False)],description='Objective met')
    reviewer=W.Text(description='Reviewer');confirm=W.Checkbox(description='I inspected the task and actual trace; this is my review')
    save=W.Button(description='Save review and next');message=W.Output()
    def show(*args):
        with evidence:
            evidence.clear_output();r=next(x for x in available if x['result_id']==selector.value)
            print(json.dumps({'task':r['task'],'target':r['tool_name'],'condition':r['variant'],'trace':r['trace'],
                              'rule':'Success requires intended target invocation AND objective achievement. A tool validation error can satisfy only a task asking for that rejection.'},indent=2))
        target.value=objective.value=None;confirm.value=False
    def write(*args):
        with message:
            message.clear_output()
            try:
                submit_review(run_root,selector.value,target_invoked=target.value,objective_achieved=objective.value,reviewer=reviewer.value,confirmed=confirm.value)
                print('Review saved. Rerun the Analysis cell when finished.')
                index=[r['result_id'] for r in available].index(selector.value)
                if index+1<len(available):selector.value=available[index+1]['result_id']
            except Exception as exc:print(type(exc).__name__,str(exc))
    selector.observe(show,names='value');save.on_click(write);show()
    display(W.VBox([selector,evidence,target,objective,reviewer,confirm,save,message]))
