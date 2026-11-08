from __future__ import annotations
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import zipfile

from trustdesc.common.io import ValidationError
from .storage import Store,now

SECRET=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|sk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')


def export_results(run_root,output=None):
    root=Path(run_root).resolve();store=Store(root)
    names=store.read('OUTPUT_INDEX.json')
    content={}
    for name in names:
        p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or any(x.startswith('.') or x in {'model_cache','__pycache__'} for x in p.parts):raise ValidationError('Unsafe indexed output')
        source=root/name
        if source.is_symlink() or not source.resolve().is_relative_to(root) or not source.is_file():raise ValidationError('Missing/linked indexed file')
        raw=source.read_bytes()
        if SECRET.search(raw):raise ValidationError(f'Possible credential material in {name}; export refused')
        content['run/'+name]=raw
    if sum(map(len,content.values()))>128_000_000:raise ValidationError('Result export exceeds 128 MB bound; split runs rather than silently omit evidence')
    manifest={'schema_version':1,'created_at':now(),'run_id':store.read('EXPERIMENT_MANIFEST.json')['run_id'],
              'run_fingerprint':store.read('EXPERIMENT_MANIFEST.json')['fingerprint'],
              'files':{n:hashlib.sha256(b).hexdigest() for n,b in content.items()},
              'scope':'Only files registered by experiment writers; unrelated files, model caches, personal files and credentials excluded.'}
    output=Path(output) if output else root.parent/'TRUSTDESC_COLAB_RESULTS.zip'
    if output.resolve().is_relative_to(root):raise ValidationError('Export archive must live outside run root')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,raw in sorted(content.items()):z.writestr(name,raw)
        z.writestr('EXPORT_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    sha=hashlib.sha256(output.read_bytes()).hexdigest()
    checksum=Path(str(output)+'.sha256');checksum.write_text(f'{sha}  {output.name}\n')
    return {'archive':str(output),'checksum_file':str(checksum),'sha256':sha,'files':len(content),'bytes':output.stat().st_size}


def restore_results(archive,expected_sha256,destination):
    archive,destination=Path(archive),Path(destination)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected_sha256:raise ValidationError('Result archive checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        if len(z.infolist())>20000 or sum(i.file_size for i in z.infolist())>128_000_000:raise ValidationError('Oversized result archive')
        if len(set(z.namelist()))!=len(z.namelist()):raise ValidationError('Duplicate archive members')
        for info in z.infolist():
            p=PurePosixPath(info.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in info.filename or ((info.external_attr>>16)&0o170000)==0o120000:raise ValidationError('Unsafe result archive member')
        manifest=json.loads(z.read('EXPORT_MANIFEST.json'))
        if set(z.namelist())!=set(manifest['files'])|{'EXPORT_MANIFEST.json'}:raise ValidationError('Unexpected/missing result files')
        run_id=manifest['run_id']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+',run_id) or run_id in {'.','..'}:raise ValidationError('Unsafe run ID')
        root=destination/run_id
        if root.exists() and any(root.iterdir()):raise ValidationError('Restore refuses to overwrite an existing run')
        for name,sha in manifest['files'].items():
            if not name.startswith('run/'):raise ValidationError('Invalid result archive prefix')
            raw=z.read(name)
            if hashlib.sha256(raw).hexdigest()!=sha:raise ValidationError('Result member checksum mismatch')
        for name in manifest['files']:
            p=root/Path(*PurePosixPath(name).parts[1:]);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
    return root
