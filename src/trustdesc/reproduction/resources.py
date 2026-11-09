"""Hash-checked acquisition with atomic cache repair and explicit provenance."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import uuid
from trustdesc.common.io import ValidationError
from trustdesc.dataset.acquire import acquire


def fetch_cached(spec, cache):
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    expected = spec['sha256']
    if not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValidationError('Expected SHA-256 missing')
    target = cache / expected
    hit = target.exists()
    if hit and hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        target.rename(cache / (expected + '.corrupt-' + uuid.uuid4().hex))
        hit = False
    if not hit:
        temp = cache / (expected + '.' + uuid.uuid4().hex + '.part')
        try:
            acquire(spec['url'], temp, expected, license_note=spec['license'])
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)
            Path(str(temp) + '.manifest.json').unlink(missing_ok=True)
    raw = target.read_bytes()
    return target, {'name': spec['name'], 'url': spec['url'], 'status': 'acquired_verified',
                    'version': spec['version'], 'sha256': expected, 'bytes': len(raw),
                    'license': spec['license'], 'classification': spec['classification'],
                    'cache_hit': hit, 'redistribute': spec.get('redistribute', False),
                    'timestamp': datetime.now(timezone.utc).isoformat()}


def probe(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'api.github.com', 'anonymous.4open.science', 'hengkai-ye.github.io'}:
        raise ValidationError('Probe URL outside fixed research allowlist')
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'trustdesc-independent-research'})
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ValidationError('Probe response too large')
            result = {'url': url, 'status': 'reachable', 'http_status': response.status,
                      'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    result['repository_names'] = [d.get('full_name') for d in data if isinstance(d, dict)]
                elif isinstance(data, dict):
                    result['service_metadata'] = {k: data[k] for k in ['status', 'message', 'error', 'expired'] if k in data}
            except (ValueError, TypeError):
                pass
            return result
    except Exception as exc:
        return {'url': url, 'status': 'unavailable', 'error_type': type(exc).__name__, 'error': str(exc)}


def acquire_references(project, cache, store, *, network=True):
    specs = json.loads((Path(project) / 'configs/reproduction_resources.json').read_text())
    ledger, inspections = [], []
    for spec in specs:
        if not network:
            ledger.append({**spec, 'status': 'not_attempted_offline_validation'})
            continue
        try:
            path, record = fetch_cached(spec, cache)
            ledger.append(record)
            if spec['format'] == 'json':
                data = json.loads(path.read_text())
                if not isinstance(data, (list, dict)):
                    raise ValidationError('External JSON must be a list or object')
                inspections.append({'name': spec['name'], 'status': 'parsed_json_container', 'rows_or_keys': len(data),
                                    'top_level_type': type(data).__name__, 'sha256': spec['sha256'],
                                    'evaluation_eligible': False, 'reason': 'External benchmark has no authenticated mapping to original TRUSTDESC tools/tasks/traces.'})
            # Only explicitly redistributable small references enter the ZIP.
            if spec.get('redistribute') and path.stat().st_size < 1_000_000:
                store.text(Path('references') / (spec['sha256'][:16] + '-' + Path(spec['name']).name), path.read_text())
        except Exception as exc:
            ledger.append({**spec, 'status': 'unavailable_or_invalid', 'error_type': type(exc).__name__, 'error': str(exc)})
    urls = ['https://anonymous.4open.science/api/repo/ae-trustdesc-13A6',
            'https://api.github.com/orgs/PSU-Security-Universe/repos?per_page=100',
            'https://hengkai-ye.github.io/']
    checks = [probe(u) for u in urls] if network else [{'url': u, 'status': 'not_attempted_offline_validation'} for u in urls]
    for name in ['original 52 tool identities and revisions', 'original 208 tasks', 'original reviewed labels',
                 'original execution traces', 'original prompts', 'original model snapshots/configuration']:
        ledger.append({'name': name, 'url': 'https://anonymous.4open.science/r/ae-trustdesc-13A6',
                       'status': 'not_recovered', 'classification': 'original_paper_material',
                       'version': None, 'sha256': None, 'license': 'unknown',
                       'missing_components': [name], 'note': 'Artifact-to-paper authenticity not established; reachable HTML is not acquisition.'})
    report = {'resources': ledger, 'discovery_checks': checks, 'inspections': inspections,
              'original_artifact_recovered': False, 'original_benchmark_reconstructed': False,
              'policy': 'Public source/metadata only; no external setup scripts or server code executed. Failed resources remain explicit.'}
    store.write('acquisition_report.json', report)
    return report


def validate_bundle(bundle, roots):
    if bundle.get('origin') != 'synthetic':
        raise ValidationError('Automatic task evaluation currently supports explicitly authored fixture data only')
    tools, task_ids = {}, set()
    for t in bundle['tools']:
        if t['id'] in tools or t['source_ref'] not in roots or not t.get('license') or not t.get('origin'):
            raise ValidationError('Invalid or duplicate tool/source provenance')
        tools[t['id']] = t
    for task in bundle['tasks']:
        if task['id'] in task_ids or task['tool_id'] not in tools or task.get('origin') != 'synthetic' or task.get('label') is not None:
            raise ValidationError('Invalid/duplicate task; synthetic labels must remain unset')
        if not isinstance(task.get('task'), str) or not task['task'].strip():
            raise ValidationError('Empty task')
        task_ids.add(task['id'])
    return {'valid': True, 'origin': bundle['origin'], 'tools': len(tools), 'tasks': len(task_ids), 'original_paper_dataset': False}
