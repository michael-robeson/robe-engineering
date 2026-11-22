from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import LifecycleError


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise LifecycleError(f"Required metadata record is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise LifecycleError(f"Invalid JSON metadata record {path}: {error}") from error
    if not isinstance(value, dict):
        raise LifecycleError(f"Metadata record must be a JSON object: {path}")
    return value
