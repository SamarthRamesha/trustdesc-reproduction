"""Task preparation without inventing annotations or benchmark provenance."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import random

from trustdesc.common.io import ValidationError, canonical, digest, dump, nonempty

FIELDS = {'id', 'server', 'tool', 'task', 'origin', 'source', 'commit', 'license', 'label'}


def prepare(input_path, output_dir, *, seed=42, split_groups=False):
    input_path, output_dir = Path(input_path), Path(output_dir)
    raw = input_path.read_bytes()
    records, ids, contents, duplicates = [], set(), {}, 0
    for line_number, line in enumerate(raw.decode('utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f'Invalid JSON at line {line_number}') from exc
        if not isinstance(record, dict) or set(record) != FIELDS:
            raise ValidationError(f'Task fields must be exactly {sorted(FIELDS)} at line {line_number}')
        for k in ('id', 'server', 'tool', 'task', 'source', 'license'):
            nonempty(record[k], k)
        if record['origin'] not in {'synthetic', 'author_released', 'reconstructed'}:
            raise ValidationError('Unknown task origin')
        if record['label'] is not None and type(record['label']) is not bool:
            raise ValidationError('Label must be a boolean or null (unknown)')
        if record['origin'] != 'synthetic' and record['commit'] is None:
            raise ValidationError('Non-synthetic data requires a pinned version/commit identifier')
        if record['commit'] is not None:
            nonempty(record['commit'], 'commit')
        if record['id'] in ids:
            raise ValidationError('Duplicate task ID; do not silently overwrite')
        ids.add(record['id'])
        record['task'] = ' '.join(record['task'].split())
        identity = digest([record['server'], record['tool'], record['task']])
        if identity in contents:
            previous = contents[identity]
            if any(previous[k] != record[k] for k in ['label', 'origin', 'source', 'commit', 'license']):
                raise ValidationError('Duplicate content has conflicting labels or provenance')
            duplicates += 1
            continue
        contents[identity] = record
        records.append(record)
    if not records:
        raise ValidationError('Dataset has no records')
    servers = sorted({r['server'] for r in records})
    assignment = {s: 'evaluation' for s in servers}
    if split_groups:
        if len(servers) < 3:
            raise ValidationError('Group split needs at least three servers')
        order = servers[:]
        random.Random(seed).shuffle(order)
        n_test = max(1, round(len(order) * .15))
        n_validation = max(1, round(len(order) * .15))
        assignment = {s: ('test' if i < n_test else 'validation' if i < n_test + n_validation else 'train') for i, s in enumerate(order)}
    for r in records:
        r['split'] = assignment[r['server']]
    records.sort(key=lambda r: r['id'])
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized = ''.join(canonical(r) + '\n' for r in records)
    (output_dir/'tasks.jsonl').write_text(normalized)
    stats = {'records': len(records), 'duplicates_removed': duplicates, 'servers': len(servers),
             'tools': len({(r['server'], r['tool']) for r in records}),
             'origin_counts': dict(Counter(r['origin'] for r in records)),
             'missing_labels': sum(r['label'] is None for r in records),
             'split_counts': dict(Counter(r['split'] for r in records))}
    manifest = {'schema_version': 1, 'input_sha256': hashlib.sha256(raw).hexdigest(),
                'output_sha256': hashlib.sha256(normalized.encode()).hexdigest(), 'seed': seed,
                'group_assignment': assignment, 'stats': stats,
                'split_policy': 'server-group 70/15/15 rounded; our extension' if split_groups else 'evaluation only; no invented paper training split',
                'license_policy': 'Retain per-record license/source. Non-synthetic acquisition requires separate license review.'}
    dump(output_dir/'manifest.json', manifest)
    return manifest
