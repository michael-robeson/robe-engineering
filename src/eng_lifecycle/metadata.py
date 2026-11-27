from __future__ import annotations

import argparse
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Sequence

from .config import LifecycleError
from .gitops import GitError, repository_root, run_git

CONFIG_PATH = ".github/repository-metadata.json"


@dataclass(frozen=True)
class Badge:
    source: str
    output: str


def safe_path(root: Path, value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise LifecycleError("Metadata paths must be non-empty repository-relative paths")
    path = PurePosixPath(value)
    if path.is_absolute() or any(
        part in ("", ".", "..") or part.lower() == ".git" for part in value.split("/")
    ):
        raise LifecycleError(f"Invalid metadata path: {value}")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise LifecycleError(f"Metadata path contains a symlink: {value}")
    return value


def parse_config(root: Path, content: str) -> list[Badge]:
    try:
        raw = json.loads(content)
    except json.JSONDecodeError as error:
        raise LifecycleError(f"Invalid repository metadata configuration: {error}") from error
    if not isinstance(raw, dict) or set(raw) != {"schema", "badges"} or type(raw["schema"]) is not int or raw["schema"] != 1:
        raise LifecycleError("Repository metadata configuration must use schema 1")
    if not isinstance(raw["badges"], list) or not raw["badges"]:
        raise LifecycleError("Repository metadata badges must be a non-empty array")
    badges = []
    for item in raw["badges"]:
        if not isinstance(item, dict) or set(item) != {"adapter", "source", "output"}:
            raise LifecycleError("Invalid repository metadata badge configuration")
        if item["adapter"] != "python-requires":
            raise LifecycleError(f"Unsupported repository metadata adapter: {item['adapter']}")
        badges.append(Badge(safe_path(root, item["source"]), safe_path(root, item["output"])))
    sources = {badge.source for badge in badges} | {CONFIG_PATH}
    outputs = [badge.output for badge in badges]
    if len(set(outputs)) != len(outputs) or any(output in sources for output in outputs):
        raise LifecycleError("Metadata outputs must be distinct from inputs and each other")
    return badges


def render_badge(content: str, source: str) -> str:
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as error:
        raise LifecycleError(f"Invalid TOML in {source}: {error}") from error
    project = data.get("project")
    requirement = project.get("requires-python") if isinstance(project, dict) else None
    if (
        not isinstance(requirement, str)
        or not requirement.strip()
        or requirement != requirement.strip()
        or any(ord(char) < 32 or ord(char) == 127 for char in requirement)
    ):
        raise LifecycleError(f"{source} must declare a non-empty project.requires-python")
    return json.dumps(
        {"schemaVersion": 1, "label": "python", "message": requirement, "color": "blue"},
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def generated(root: Path, read: Callable[[str], str]) -> list[tuple[str, str]]:
    config = parse_config(root, read(CONFIG_PATH))
    return [(badge.output, render_badge(read(badge.source), badge.source)) for badge in config]


def worktree_read(root: Path, path: str) -> str:
    safe_path(root, path)
    try:
        return (root / path).read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise LifecycleError(f"Missing repository metadata file: {path}") from error


def check(root: Path) -> None:
    for path, expected in generated(root, lambda name: worktree_read(root, name)):
        if worktree_read(root, path) != expected:
            raise LifecycleError(f"Repository metadata is out of date: {path}; regenerate it before committing")


def write_outputs(root: Path, outputs: list[tuple[str, str]]) -> None:
    for path, expected in outputs:
        target = root / path
        tracked = run_git(root, ["ls-tree", "--name-only", "HEAD", "--", f":(literal){path}"])
        base = run_git(root, ["show", f"HEAD:{path}"]) if tracked.stdout else None
        if target.exists():
            if not target.is_file():
                raise LifecycleError(f"Metadata output is not a regular file: {path}")
            current = target.read_text(encoding="utf-8")
            if current != expected and (base is None or current != base.stdout):
                raise LifecycleError(f"Refusing to overwrite modified metadata output: {path}")
        elif base is not None:
            raise LifecycleError(f"Refusing to overwrite deleted metadata output: {path}")
    for path, expected in outputs:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_text(encoding="utf-8") != expected:
            target.write_text(expected, encoding="utf-8")


def prepare_index(root: Path) -> None:
    present = run_git(root, ["ls-files", "--error-unmatch", "--", CONFIG_PATH], check=False)
    if present.returncode == 1:
        return
    if present.returncode != 0:
        raise LifecycleError("Unable to inspect repository metadata configuration in the index")

    def index_read(path: str) -> str:
        safe_path(root, path)
        entry = run_git(root, ["ls-files", "--stage", "--", f":(literal){path}"]).stdout.strip()
        if not entry.startswith(("100644 ", "100755 ")) or "\n" in entry:
            raise LifecycleError(f"Metadata input must be a regular staged file: {path}")
        result = run_git(root, ["show", f":{path}"], check=False)
        if result.returncode:
            raise LifecycleError(f"Cannot read staged metadata input: {path}")
        return result.stdout

    outputs = generated(root, index_read)
    write_outputs(root, outputs)
    run_git(root, ["add", "--", *(f":(literal){path}" for path, _ in outputs)])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eng-metadata")
    parser.add_argument("command", choices=("check", "generate"))
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    try:
        root = repository_root(Path(args.repo))
        if args.command == "check":
            check(root)
        else:
            write_outputs(root, generated(root, lambda name: worktree_read(root, name)))
    except (LifecycleError, GitError, OSError, UnicodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
