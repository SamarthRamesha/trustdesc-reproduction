from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from importlib.resources import files
from tempfile import TemporaryDirectory

from .common.io import dump, load
from .common.models import HTTPModel, ReplayModel
from .dataset import prepare
from .descgen import generate
from .dynver import verify
from .evaluation import summarize, overhead
from .fixtures import replay
from .pipeline import run_pipeline
from .sandbox import ControlledAgent, DisabledRunner
from .slicemin import PythonSlicer


def model_args(parser):
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--replay', type=Path, help='Synthetic/test replay JSON list')
    group.add_argument('--endpoint', help='Explicit chat-completions endpoint')
    parser.add_argument('--model', help='Exact provider model ID, required for HTTP')
    parser.add_argument('--allow-remote', action='store_true')
    parser.add_argument('--allow-paid', action='store_true')
    parser.add_argument('--timeout', type=float, default=30)


def get_model(args):
    if args.replay:
        return ReplayModel(load(args.replay))
    if not args.model:
        raise ValueError('--model must be specified with --endpoint')
    # Only explicitly approved remote mode reads the specifically named variable.
    key = os.environ.get('TRUSTDESC_API_KEY') if args.allow_remote and args.allow_paid else None
    return HTTPModel(args.endpoint, args.model, api_key=key, allow_remote=args.allow_remote,
                     allow_paid=args.allow_paid, timeout=args.timeout)


def main(argv=None):
    p = argparse.ArgumentParser(description='Bounded TRUSTDESC research implementation; no safety certification')
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('slice', help='Static Python slicing; source is never imported')
    s.add_argument('source_root', type=Path); s.add_argument('tool'); s.add_argument('--entry')
    s.add_argument('--output', type=Path, required=True)
    s.add_argument('--debloat-replay', type=Path)
    s.add_argument('--max-passes', type=int, default=3)
    d = sub.add_parser('describe', help='Generate an unverified draft from a slice')
    d.add_argument('slice', type=Path);d.add_argument('--output', type=Path, required=True);model_args(d)
    v = sub.add_parser('verify', help='Plan verification; untrusted execution remains disabled')
    v.add_argument('draft', type=Path);v.add_argument('--output', type=Path, required=True);model_args(v)
    demo = sub.add_parser('demo', help='Run synthetic fixture pipeline; no model inference')
    demo.add_argument('--output', type=Path, required=True)
    data = sub.add_parser('prepare', help='Validate and prepare JSONL research tasks')
    data.add_argument('input', type=Path);data.add_argument('--output', type=Path, required=True)
    data.add_argument('--seed',type=int,default=42);data.add_argument('--group-split',action='store_true')
    ev = sub.add_parser('evaluate', help='Calculate TSR from reviewed task-result JSON list')
    ev.add_argument('results',type=Path);ev.add_argument('--output',type=Path,required=True)
    ev.add_argument('--expected-tasks',type=Path,help='JSON list of expected task IDs')
    ev.add_argument('--with-overhead',action='store_true')
    args = p.parse_args(argv)
    try:
        if args.command == 'slice':
            model = ReplayModel(load(args.debloat_replay)) if args.debloat_replay else None
            result = PythonSlicer(args.source_root).slice(args.tool, explicit_entry=args.entry,
                                                        model=model,max_passes=args.max_passes)
            dump(args.output,result)
            if model:dump(str(args.output)+'.audit.json',model.audit)
        elif args.command == 'describe':
            model=get_model(args)
            try:dump(args.output,generate(load(args.slice),model))
            finally:dump(str(args.output)+'.audit.json',model.audit)
        elif args.command == 'verify':
            model=get_model(args);draft=load(args.draft)
            try:dump(args.output,verify(draft.get('description',draft),model,DisabledRunner()))
            finally:dump(str(args.output)+'.audit.json',model.audit)
        elif args.command == 'demo':
            # Package data, never an imported/executed tool module. This also
            # works when the CLI is installed independently of a source checkout.
            source = files('trustdesc').joinpath('resources/synthetic_server.py.txt').read_text()
            with TemporaryDirectory(prefix='trustdesc-fixture-') as tmp:
                fixture = Path(tmp)
                (fixture/'server.py').write_text(source)
                model=ReplayModel(replay())
                run_pipeline(fixture,'apply_formula',model,ControlledAgent(model),args.output)
        elif args.command == 'prepare':
            prepare(args.input,args.output,seed=args.seed,split_groups=args.group_split)
        elif args.command == 'evaluate':
            records=load(args.results)
            result={'TSR':summarize(records,load(args.expected_tasks) if args.expected_tasks else None),
                    'warning':'Dataset provenance and experimental equivalence must be independently reviewed.'}
            if args.with_overhead:result['overhead']=overhead(records)
            dump(args.output,result)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        p.exit(1,f'{type(exc).__name__}: {exc}\n')
    print(json.dumps({'status':'saved','output':str(args.output),'original_paper_reproduced':False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
