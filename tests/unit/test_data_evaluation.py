import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from trustdesc.common.io import ValidationError
from trustdesc.dataset import prepare
from trustdesc.dataset.acquire import acquire, inventory_zip
from trustdesc.evaluation import summarize, overhead


def task(i=0, **changes):
    r={'id':f't{i}','server':f'server{i}','tool':'fixture','task':f'Compute {i}',
       'origin':'synthetic','source':'newly authored fixture','commit':None,'license':'project synthetic fixture','label':None}
    return {**r,**changes}


def result(task_id='t1', variant='original', **changes):
    r={'task_id':task_id,'run_id':'fixture-test','model':'synthetic-replay','variant':variant,
       'reviewed':True,'target_invoked':True,'objective_achieved':True,
       'input_tokens':100,'output_tokens':10,'cost_usd':None,'latency_seconds':1,'tool_calls':1}
    return {**r,**changes}


class DatasetTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def write(self, rows):
        p=self.root/'input.jsonl';p.write_text(''.join(json.dumps(r)+'\n' for r in rows));return p

    def test_manifest_missing_labels_and_hash(self):
        p=self.write([task()]);r=prepare(p,self.root/'out')
        self.assertEqual(r['stats']['missing_labels'],1)
        self.assertEqual(r['input_sha256'],hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertEqual(r['stats']['split_counts'],{'evaluation':1})

    def test_dedup_whitespace(self):
        r=prepare(self.write([task(),task(1,server='server0',task=' Compute   0 ')]),self.root/'out')
        self.assertEqual(r['stats']['duplicates_removed'],1)

    def test_duplicate_id_fails(self):
        with self.assertRaises(ValidationError):prepare(self.write([task(),task()]),self.root/'out')

    def test_conflicting_duplicate_labels_rejected(self):
        with self.assertRaises(ValidationError):prepare(self.write([task(label=True),task(1,server='server0',task='Compute 0',label=False)]),self.root/'out')

    def test_missing_provenance(self):
        r=task(origin='author_released')
        with self.assertRaises(ValidationError):prepare(self.write([r]),self.root/'out')

    def test_label_validation(self):
        with self.assertRaises(ValidationError):prepare(self.write([task(label='malicious')]),self.root/'out')

    def test_empty_dataset(self):
        with self.assertRaises(ValidationError):prepare(self.write([]),self.root/'out')

    def test_seeded_server_splits_no_leakage(self):
        rows=[task(i) for i in range(10)]+[task(10,server='server0',task='Other task')]
        p=self.write(rows)
        a=prepare(p,self.root/'a',split_groups=True);b=prepare(p,self.root/'b',split_groups=True)
        self.assertEqual(a['output_sha256'],b['output_sha256'])
        self.assertEqual(set(a['group_assignment'].values()),{'train','validation','test'})

    def test_too_few_groups(self):
        with self.assertRaises(ValidationError):prepare(self.write([task()]),self.root/'out',split_groups=True)

    def test_acquisition_rejects_unapproved_host_and_no_hash(self):
        with self.assertRaises(ValidationError):acquire('https://evil.example/tool.zip',self.root/'x','a'*64,license_note='test')
        with self.assertRaises(ValidationError):acquire('https://codeload.github.com/x/y/zip/main',self.root/'x','',license_note='test')

    def test_archive_path_traversal_and_links(self):
        p=self.root/'bad.zip'
        with zipfile.ZipFile(p,'w') as z:z.writestr('../escape','bad')
        with self.assertRaises(ValidationError):inventory_zip(p)
        p=self.root/'link.zip'
        with zipfile.ZipFile(p,'w') as z:
            i=zipfile.ZipInfo('link');i.external_attr=0o120777<<16;z.writestr(i,'/etc/passwd')
        with self.assertRaises(ValidationError):inventory_zip(p)

    def test_archive_inventory_no_extraction(self):
        p=self.root/'ok.zip'
        with zipfile.ZipFile(p,'w') as z:z.writestr('folder/tool.py','print("never executed")')
        self.assertEqual(inventory_zip(p)[0]['name'],'folder/tool.py')
        self.assertFalse((self.root/'folder').exists())


class MetricTests(unittest.TestCase):
    def test_tsr_requires_both_conditions(self):
        r=summarize([result(),result('t2',target_invoked=False),result('t3',objective_achieved=False)])
        self.assertAlmostEqual(r[0]['TSR_percent'],100/3)

    def test_unknown_labels_are_not_failures(self):
        with self.assertRaises(ValidationError):summarize([result(objective_achieved=None)])

    def test_review_required(self):
        with self.assertRaises(ValidationError):summarize([result(reviewed=False)])

    def test_duplicate_results_rejected(self):
        with self.assertRaises(ValidationError):summarize([result(),result()])

    def test_missing_tasks_rejected(self):
        with self.assertRaises(ValidationError):summarize([result()],expected_tasks=['t1','t2'])

    def test_overhead_uses_three_way_success_intersection(self):
        rows=[result(variant=v,latency_seconds=2 if v=='full' else 1) for v in ['original','lite','full']]
        rows += [result('failed',variant=v,objective_achieved=(v!='lite'),latency_seconds=1000) for v in ['original','lite','full']]
        r=overhead(rows)
        self.assertEqual(r[1]['matched_successful_tasks'],['t1'])
        self.assertEqual(r[1]['relative_percent']['latency_seconds'],100)
        self.assertIsNone(r[0]['relative_percent']['cost_usd'])

    def test_unmatched_overhead_fails(self):
        with self.assertRaises(ValidationError):overhead([result()])

    def test_zero_cost_not_invented_ratio(self):
        rows=[result(variant=v,cost_usd=0) for v in ['original','lite','full']]
        self.assertIsNone(overhead(rows)[0]['relative_percent']['cost_usd'])

    def test_bad_metric_value(self):
        for bad in [float('nan'),-1,True]:
            with self.subTest(value=bad):
                with self.assertRaises(ValidationError):summarize([result(latency_seconds=bad)])
