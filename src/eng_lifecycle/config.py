from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any


class LifecycleError(RuntimeError):
    pass


class LifecycleConfig:
    def __init__(self, root: Path, raw: dict[str, Any]) -> None:
        self.root = root
        self.raw = raw

    @property
    def base(self) -> str:
        return str(self.raw["base"])

    @property
    def feature_prefix(self) -> str:
        return str(self.raw["feature_prefix"])

    @property
    def merge_strategy(self) -> str:
        return str(self.raw["merge_strategy"])

    def gate_commands(self, gate: str) -> list[list[str]]:
        section = self.raw.get(gate)
        if not isinstance(section, dict):
            raise LifecycleError(f"Configuration gate '{gate}' must be an object")
        commands = section.get("commands", [])
        if not isinstance(commands, list):
            raise LifecycleError(f"Configuration gate '{gate}.commands' must be an array")
        parsed: list[list[str]] = []
        for item in commands:
            if isinstance(item, str):
                parsed.append(shlex.split(item))
            elif isinstance(item, list) and all(isinstance(arg, str) for arg in item):
                parsed.append(item)
            else:
                raise LifecycleError(
                    f"Configuration gate '{gate}.commands' entries must be "
                    "strings or string arrays"
                )
        return parsed

    def policy_bytes(self) -> bytes:
        canonical = json.dumps(
            self.raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return canonical


def load_config(root: Path) -> LifecycleConfig:
    root = root.resolve()
    config_path = root / ".github" / "lifecycle.json"
    if not config_path.is_file():
        raise LifecycleError(
            f"Missing repository lifecycle configuration: {config_path}"
        )
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise LifecycleError(f"Invalid JSON in {config_path}: {error}") from error
    if not isinstance(raw, dict):
        raise LifecycleError("Lifecycle configuration must be a JSON object")

    for key in ("schema", "base", "feature_prefix", "merge_strategy"):
        if key not in raw:
            raise LifecycleError(f"Missing lifecycle configuration field: {key}")
    if raw["schema"] != 1:
        raise LifecycleError(
            f"Unsupported lifecycle configuration schema: {raw['schema']}"
        )
    if not isinstance(raw["base"], str) or not raw["base"]:
        raise LifecycleError("base must be a non-empty string")
    if not isinstance(raw["feature_prefix"], str) or not raw["feature_prefix"]:
        raise LifecycleError("feature_prefix must be a non-empty string")
    if raw["merge_strategy"] not in ("merge", "squash", "rebase"):
        raise LifecycleError("merge_strategy must be merge, squash, or rebase")
    for gate in ("commit_gate", "readiness_gate", "integration_gate"):
        if gate not in raw:
            raise LifecycleError(
                f"Missing lifecycle configuration gate: {gate}"
            )

    config = LifecycleConfig(root, raw)
    config.gate_commands("commit_gate")
    config.gate_commands("readiness_gate")
    config.gate_commands("integration_gate")
    if "required_ci" in raw:
        if not isinstance(raw["required_ci"], list) or not all(
            isinstance(name, str) and name for name in raw["required_ci"]
        ):
            raise LifecycleError("required_ci must be an array of names")
    if "special_authorization" in raw:
        if not isinstance(raw["special_authorization"], list) or not all(
            isinstance(name, str) and name
            for name in raw["special_authorization"]
        ):
            raise LifecycleError(
                "special_authorization must be an array of names"
            )
    return config
