from __future__ import annotations
from pathlib import Path,PurePosixPath
import hashlib
import json
import zipfile

from trustdesc.common.io import ValidationError
from .data import builtin_dataset,add_public_source,supplied_bundle


def prepare_inputs(project,workspace,*,acquire_public=False,public_archive=None,resource_bundle=None):
    project,workspace=Path(project),Path(workspace)
    if resource_bundle:
        bundle,roots=supplied_bundle(resource_bundle)
        acquisition={'status':'supplied_resources','provenance':bundle['provenance'],'original_authenticity':'requires independent verification'}
    else:
        bundle,roots=builtin_dataset(project,workspace)
        acquisition={'status':'synthetic_inputs_ready','public_source':'not_requested','original_artifact':'not_recovered'}
        if acquire_public:
            try:
                add_public_source(bundle,roots,project,workspace,archive=public_archive)
                acquisition['public_source']='pinned_snapshot_acquired_static_only'
            except Exception as exc:
                acquisition.update(public_source='unavailable',error_type=type(exc).__name__,error=str(exc))
    return bundle,roots,acquisition


def extract_resource_bundle(archive,sha256,destination):
    """Read-only acquisition/preparation: never executes/imports bundle contents."""
    archive,destination=Path(archive),Path(destination)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=sha256:raise ValidationError('Resource bundle checksum mismatch')
    if destination.exists() and any(destination.iterdir()):raise ValidationError('Resource extraction destination must be fresh')
    with zipfile.ZipFile(archive) as z:
        if len(z.infolist())>20000 or sum(i.file_size for i in z.infolist())>128_000_000:raise ValidationError('Resource bundle exceeds bound')
        if len(set(z.namelist()))!=len(z.namelist()):raise ValidationError('Duplicate resource members')
        for i in z.infolist():
            p=PurePosixPath(i.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in i.filename or ((i.external_attr>>16)&0o170000)==0o120000:raise ValidationError('Unsafe resource member')
        z.extractall(destination)
    candidates=list(destination.rglob('bundle.json'))
    if len(candidates)!=1:raise ValidationError('Resource archive must contain exactly one bundle.json')
    return candidates[0]
