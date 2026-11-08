from __future__ import annotations

import hashlib
import json
from pathlib import Path


class ValidationError(ValueError):
    """Invalid research input or model output; never silently repair it."""


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def dump(path: str | Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def load(path: str | Path):
    return json.loads(Path(path).read_text())


def require_fields(value, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValidationError(f"{label} requires exactly {sorted(fields)}")
    return value


def nonempty(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a nonempty string")
    return value
