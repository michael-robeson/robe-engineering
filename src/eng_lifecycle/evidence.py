from __future__ import annotations

import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    data = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256_bytes(data)


def feature_storage_dir(repo_git_dir: Path, feature: str) -> Path:
    feature_hash = sha256_bytes(feature.encode("utf-8"))[:16]
    return repo_git_dir / "engineering-lifecycle" / feature_hash


def run_command(cwd: Path, argv: list[str]) -> dict[str, Any]:
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except FileNotFoundError as error:
        exit_code = 127
        stdout = ""
        stderr = str(error)
    return {
        "argv": argv,
        "started_at": started_at,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.monotonic() - started, 6),
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
    }


def write_json(path: Path, value: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value, sort_keys=True, indent=2, ensure_ascii=False
    ).encode("utf-8")
    path.write_bytes(encoded)
    return sha256_bytes(encoded)
