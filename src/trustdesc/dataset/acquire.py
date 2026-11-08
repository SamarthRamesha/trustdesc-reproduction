"""Bounded public acquisition. Bytes are quarantined; no imports/extraction/run."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import urllib.parse
import urllib.request
import zipfile

from trustdesc.common.io import ValidationError, dump, nonempty
from trustdesc.common.models import NoRedirect

ALLOWED = {'codeload.github.com', 'raw.githubusercontent.com', 'arxiv.org', 'anonymous.4open.science'}


def acquire(url, output, expected_sha256, *, license_note, max_bytes=25_000_000):
    u = urllib.parse.urlparse(url)
    if u.scheme != 'https' or u.hostname not in ALLOWED or u.username or u.password or u.query or u.fragment:
        raise ValidationError('Use a public HTTPS artifact URL on the explicit allowlist')
    if not re.fullmatch('[0-9a-f]{64}', expected_sha256):
        raise ValidationError('An independently recorded SHA-256 is required')
    nonempty(license_note, 'license review note')
    output = Path(output)
    if output.exists():
        raise ValidationError('Acquisition refuses to overwrite existing evidence')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, headers={'User-Agent': 'trustdesc-phase1-research/0.1'})
    with opener.open(request, timeout=25) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValidationError('Artifact exceeds download size limit')
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise ValidationError(f'Checksum mismatch: observed {actual}')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    dump(str(output)+'.manifest.json', {'url': url, 'sha256': actual, 'bytes': len(data),
                                      'license_note': license_note, 'status': 'quarantined_not_executed'})
    return actual


def inventory_zip(path):
    """Inspect names/sizes only; never extract. Reject links and traversal."""
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > 10000 or sum(i.file_size for i in infos) > 100_000_000:
            raise ValidationError('Expanded archive exceeds inspection limits')
        for i in infos:
            p = Path(i.filename)
            kind = (i.external_attr >> 16) & 0o170000
            if p.is_absolute() or '..' in p.parts or '\\' in i.filename or kind == 0o120000:
                raise ValidationError('Unsafe archive member')
        return [{'name': i.filename, 'bytes': i.file_size} for i in infos]
