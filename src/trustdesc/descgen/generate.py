from __future__ import annotations

from trustdesc.common.io import ValidationError, digest, nonempty, require_fields
from .prompts import GENERATE
from .sanitize import sanitize


def prose_paths(description):
    result = {('summary',): description['summary']}
    result.update({('functionalities', i): s for i, s in enumerate(description['functionalities'])})

    def walk(value, path):
        if isinstance(value, dict):
            for k, v in value.items():
                if k == 'description':
                    result[(*path, k)] = v
                else:
                    walk(v, (*path, k))
        elif isinstance(value, list):
            for i, v in enumerate(value): walk(v, (*path, i))
    walk(description['input_schema'], ('input_schema',))
    return result


def validate_description(value):
    require_fields(value, {'summary', 'functionalities', 'input_schema', 'claims'}, 'description')
    nonempty(value['summary'], 'summary')
    fs = value['functionalities']
    if not isinstance(fs, list) or not all(isinstance(f, str) and f.strip() for f in fs):
        raise ValidationError("functionalities must be a list of nonempty strings")
    schema = value['input_schema']
    if not isinstance(schema, dict) or schema.get('type') != 'object' or not isinstance(schema.get('properties'), dict):
        raise ValidationError("input_schema must be an object schema with properties")
    required = schema.get('required', [])
    if not isinstance(required, list) or not all(isinstance(x, str) for x in required) or len(set(required)) != len(required) or not set(required).issubset(schema['properties']):
        raise ValidationError("Invalid required input properties")
    claims = value['claims']
    if not isinstance(claims, list):
        raise ValidationError("claims must be a list")
    paths, seen, ids = prose_paths(value), set(), set()
    for c in claims:
        require_fields(c, {'id', 'text', 'target'}, 'claim')
        nonempty(c['id'], 'claim id')
        nonempty(c['text'], 'claim text')
        if not isinstance(c['target'], list) or not all(type(x) in {str, int} for x in c['target']):
            raise ValidationError("Claim target must be a list of keys/indices")
        target = tuple(c['target'])
        if c['id'] in ids or target in seen or target not in paths or paths[target] != c['text']:
            raise ValidationError("Duplicate, missing or mismatched claim target")
        ids.add(c['id']); seen.add(target)
    if set(paths) != seen:
        raise ValidationError("Every description prose field must be covered by exactly one claim")
    return value


def generate(slice_result, model):
    if not slice_result.get('source', '').strip():
        raise ValidationError("Empty code slice")
    sanitized = sanitize(slice_result['source'], model)
    payload = {"tool": slice_result['tool'], "code": sanitized['source'],
               "analysis_warnings": slice_result.get('warnings', [])}
    result = validate_description(model.complete('description', GENERATE, payload))
    return {"description": result, "sanitized": sanitized,
            "model": model.model_id, "model_mode": model.mode,
            "prompt_hash": digest(GENERATE), "input_hash": digest(payload),
            "status": "unverified_draft", "unsupported_claims": "requires_DynVer_and_review"}
