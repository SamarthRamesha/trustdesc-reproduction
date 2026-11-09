from __future__ import annotations
import ast
import copy
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import zipfile

from trustdesc.common.io import digest, ValidationError
from trustdesc.dataset.prepare import prepare
from trustdesc.dataset.acquire import acquire, inventory_zip
from trustdesc.sandbox.fixture_tools import SCHEMAS

NORMALIZE_SOURCE='''@mcp.tool()
def normalize_name(name: str):
    """Normalize a text name by trimming surrounding whitespace and lowercasing it."""
    return {'normalized': name.strip().lower()}
'''
ARGUMENTS=[{'formula':'=SUM(A1:A5)'},{'formula':'SUM(A1:A5)'},{'formula':'=INDIRECT("A1")'},
           {'formula':'=HYPERLINK("x")'},{'name':' Alice '},{'name':''},{'name':'   '},{'name':'BOB'}]


def builtin_dataset(project, workspace):
    project,workspace=Path(project),Path(workspace);workspace.mkdir(parents=True,exist_ok=True)
    manifest=prepare(project/'tests/fixtures/tasks.jsonl',workspace/'prepared')
    tasks=[json.loads(line) for line in (workspace/'prepared/tasks.jsonl').read_text().splitlines()]
    tools=[];roots={}
    for name,source in [('apply_formula',files('trustdesc').joinpath('resources/synthetic_server.py.txt').read_text()),('normalize_name',NORMALIZE_SOURCE)]:
        path=workspace/'source'/name;path.mkdir(parents=True,exist_ok=True);(path/'server.py').write_text(source)
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name)
        tools.append({'id':name,'name':name,'source_ref':name,'entry':None,'language':'python',
                      'backend':'controlled_fixture','origin':'synthetic','license':'Project-authored; export authorized by project owner',
                      'original_description':{'summary':ast.get_docstring(node),'functionalities':[], 'input_schema':copy.deepcopy(SCHEMAS[name])}})
        roots[name]=path
    for row,args in zip(tasks,ARGUMENTS):
        row['tool_id']=row['tool'];row['fixture_arguments']=args
        row['review_criterion']='Observe the requested call and its result or expected validation error; rejection is an objective only for tasks asking to try invalid/unsafe formulas.'
    return {'origin':'synthetic','tools':tools,'tasks':tasks,'manifest':manifest,
            'provenance':'Eight project-authored tasks, not original 208; original condition uses fixture developer docstrings.'},roots


def add_public_source(bundle,roots,project,workspace,*,archive=None):
    """One pinned paper-linked source, STATIC ONLY; no imports/setup execution."""
    project,workspace=Path(project),Path(workspace)
    spec=json.loads((project/'data/manifests/acquired_sources.json').read_text())[0]
    path=Path(archive) if archive else workspace/'public-snapshot.zip'
    if not path.exists():acquire(spec['url'],path,spec['archive_sha256'],license_note=spec['license'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=spec['archive_sha256']:raise ValidationError('Public snapshot checksum mismatch')
    inventory_zip(path)
    destination=workspace/'public-source'
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            parts=Path(info.filename).parts
            if len(parts)>1 and (info.filename.endswith('.py') or parts[-1]=='LICENSE'):
                p=destination/Path(*parts[1:]);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(info))
    tree=ast.parse((destination/'src/arxiv_mcp_server/tools/search.py').read_text())
    description=None
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='search_tool' for t in n.targets) and isinstance(n.value,ast.Call):
            for kw in n.value.keywords:
                if kw.arg=='description':
                    try:description=ast.literal_eval(kw.value)
                    except ValueError:pass
    tool={'id':'arxiv-current-search','name':'search_papers','source_ref':'arxiv-current',
          'entry':'arxiv_mcp_server.tools.search:handle_search','language':'python','backend':'disabled',
          'origin':'external_current_snapshot','license':'Apache-2.0','source_provenance':spec,
          'generation_policy':'static_reference_only',
          'original_description':{'summary':description or 'Original description could not be statically extracted; not invented.',
                                  'functionalities':[],'input_schema':{'type':'object','properties':{}}},
          'metadata_gap':'Input schema not reconstructed; external execution disabled.'}
    bundle['tools'].append(tool);bundle['public_source']=spec;bundle['public_license_text']=(destination/'LICENSE').read_text()
    roots['arxiv-current']=destination/'src'
    return tool


def supplied_bundle(path):
    """Activate genuine/reconstructed resources as data only, never run their code.

    Bundle format is documented and validated. External backend is always disabled.
    A manifest's author provenance is an attestation, not proof of authenticity.
    """
    path=Path(path).resolve();bundle=json.loads(path.read_text());roots={}
    if bundle.get('origin') not in {'author_released','reconstructed'}:raise ValidationError('Supplied benchmark must declare origin')
    if not bundle.get('provenance') or not isinstance(bundle.get('tools'),list) or not isinstance(bundle.get('tasks'),list):
        raise ValidationError('Missing resource provenance/tools/tasks')
    if bundle['origin']=='author_released' and (len(bundle['tools'])!=52 or len(bundle['tasks'])!=208):
        raise ValidationError('Original benchmark candidate requires exactly 52 tools and 208 tasks')
    for source in bundle.get('sources',[]):
        p=(path.parent/source['path']).resolve()
        if not p.is_relative_to(path.parent) or not p.is_dir():raise ValidationError('Source path escapes bundle or is missing')
        if not source.get('revision') or not source.get('license') or not source.get('url'):raise ValidationError('Source requires version/license/URL')
        roots[source['ref']]=p
    ids=set()
    for t in bundle['tools']:
        if t['id'] in ids or t['source_ref'] not in roots or not t.get('original_description'):raise ValidationError('Invalid tool/source/description')
        ids.add(t['id']);t['backend']='disabled'
        t.setdefault('origin',bundle['origin'])
    task_ids=set()
    for t in bundle['tasks']:
        if t['id'] in task_ids or t['tool_id'] not in ids or not isinstance(t.get('task'),str) or not t['task'].strip():raise ValidationError('Invalid task ID/target/text')
        task_ids.add(t['id'])
    bundle['provenance_warning']='Supplied original provenance requires independent human verification; no arbitrary execution or success labels imported.'
    return bundle,roots


def source_hashes(roots):
    return {ref:{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(root.rglob('*.py')) if not p.is_symlink()}
            for ref,root in sorted(roots.items())}
