from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid

from trustdesc.common.io import canonical, digest, ValidationError


def now(): return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, root, secrets=()):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.secrets=[s for s in secrets if s]

    def clean(self, value):
        if isinstance(value,dict):
            return {self.clean(k):self.clean(v) for k,v in value.items() if k.lower() not in {'api_key','authorization','access_token','password','github_token'}}
        if isinstance(value,list):return [self.clean(v) for v in value]
        if isinstance(value,str):
            for secret in self.secrets:value=value.replace(secret,'[REDACTED]')
            value=re.sub(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|sk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{24,})','[REDACTED]',value)
        return value

    def write(self, relative, value):
        path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        tmp.write_text(json.dumps(self.clean(value),indent=2,ensure_ascii=False,allow_nan=False)+'\n')
        tmp.replace(path)
        self.track(relative)

    def track(self, relative):
        relative=Path(relative)
        if relative.is_absolute() or '..' in relative.parts:raise ValidationError('Invalid output path')
        path=self.root/'OUTPUT_INDEX.json'
        names=set(json.loads(path.read_text())) if path.exists() else set()
        names.update([relative.as_posix(),'OUTPUT_INDEX.json'])
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(sorted(names),indent=2)+'\n');tmp.replace(path)

    def text(self, relative, content):
        path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(self.clean(content));self.track(relative)

    def read(self, relative):return json.loads((self.root/relative).read_text())

    def job(self, key, operation, *, retry_failed=False):
        identity=digest(key);folder=Path('checkpoints')/identity
        marker=self.root/folder/'state.json'
        if marker.exists():
            state=json.loads(marker.read_text())
            if state['status']=='completed':
                data=(self.root/folder/'result.json').read_bytes()
                if hashlib.sha256(data).hexdigest()!=state['result_sha256']:raise ValidationError('Checkpoint checksum mismatch')
                return json.loads(data)
            if state['status'] in {'failed','blocked','unavailable'} and not retry_failed:
                return self.read(folder/'result.json')
            attempt=state['attempt']+1
        else:attempt=1
        self.write(folder/'state.json',{'key':key,'status':'started','attempt':attempt,'started_at':now()})
        try:
            result=operation()
            result.setdefault('status','completed')
        except Exception as exc:
            result={'status':getattr(exc,'experiment_status','failed'),'error_type':type(exc).__name__,'error':str(exc)}
        result['recorded_at']=now()
        self.write(folder/f'attempt-{attempt}.json',result)
        self.write(folder/'result.json',result)
        content=(self.root/folder/'result.json').read_bytes()
        self.write(folder/'state.json',{'key':key,'status':result['status'],'attempt':attempt,
                                      'completed_at':now(),'result_sha256':hashlib.sha256(content).hexdigest()})
        return self.read(folder/'result.json')
