#!/usr/bin/env python3
"""Static-only experiment on one pinned public source snapshot. No source imports.

Acquisition is separate; no registry install, external setup, server start or test
execution occurs. The archive stays excluded from the portable project.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import sys
import time
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from trustdesc.common.io import dump, load
from trustdesc.dataset.acquire import inventory_zip
from trustdesc.slicemin import PythonSlicer, SliceError

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
    spec=load(ROOT/'data/manifests/acquired_sources.json')[0]
    actual=hashlib.sha256(a.archive.read_bytes()).hexdigest()
    if actual!=spec['archive_sha256']:raise ValueError('Pinned snapshot hash mismatch')
    inventory_zip(a.archive)
    destination=ROOT/'data/interim'/f'arxiv-static-source-{time.time_ns()}'
    # Only Python text and LICENSE are extracted; no external agent/config files.
    with zipfile.ZipFile(a.archive) as z:
        for info in z.infolist():
            parts=Path(info.filename).parts
            if len(parts)>1 and (info.filename.endswith('.py') or parts[-1]=='LICENSE'):
                path=destination/Path(*parts[1:]);path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(z.read(info))
    source=destination/'src'
    server=ast.parse((source/'arxiv_mcp_server/server.py').read_text())
    exposed=[]
    for n in server.body:
        if isinstance(n,ast.AsyncFunctionDef) and n.name=='list_tools':
            for item in ast.walk(n):
                if isinstance(item,ast.Return) and isinstance(item.value,ast.List):
                    exposed=[ast.unparse(x) for x in item.value.elts]
    start=time.perf_counter();slicer=PythonSlicer(source)
    try:slicer.slice('search_papers');automatic='resolved'
    except SliceError:automatic='unsupported_dispatch_registration_requires_override'
    sliced=slicer.slice('search_papers',explicit_entry='arxiv_mcp_server.tools.search:handle_search')
    seconds=time.perf_counter()-start
    dump(ROOT/'data/interim/arxiv-search-slice.json',sliced)
    dump(ROOT/'reports/public_static_experiment.json',{
        'experiment_type':'real_public_source_static_only_not_original_benchmark',
        'source':spec,'license_file_sha256':hashlib.sha256((destination/'LICENSE').read_bytes()).hexdigest(),
        'analyzed_python_files':len(sliced['source_hashes']),'tool_list_entries_in_current_source':len(exposed),
        'automatic_entry_status':automatic,'reviewed_entry':sliced['entry'],'reachable_functions':sliced['functions'],
        'reachable_function_count':len(sliced['functions']),'resolved_call_sites':len(sliced['edges']),
        'unresolved_call_sites':len(sliced['unresolved_calls']),'warnings':sliced['warnings'],
        'wall_seconds':seconds,'mode':sliced['mode'],'third_party_code_executed':False,
        'source_hashes':sliced['source_hashes'],
        'limitations':['Current snapshot is not the unknown paper revision.',
                       'Reviewed handler override bypasses automatic dispatch detection.',
                       'Unresolved calls and retained classes/context mean slice completeness is unproven.',
                       'No descriptions, DynVer tasks, paper TSR or attack outcomes measured.']})
    print({'python_files':len(sliced['source_hashes']),'reachable_functions':len(sliced['functions']),
           'current_tool_list_count':len(exposed),'unresolved_calls':len(sliced['unresolved_calls']),'seconds':seconds})

if __name__=='__main__':main()
