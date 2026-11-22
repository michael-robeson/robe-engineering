from __future__ import annotations

import os
import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def repository_root(repo: Path) -> Path:
    repo = repo.resolve()
    if not repo.is_dir():
        raise GitError(f"Repository path is not a directory: {repo}")
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip()).resolve()
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or "not a Git repository"
        raise GitError(detail) from error


def git_dir(repo: Path) -> Path:
    root = repository_root(repo)
    result = run_git(root, ["rev-parse", "--absolute-git-dir"], check=True)
    return Path(result.stdout.strip()).resolve()


def run_git(
    root: Path,
    args: list[str],
    *,
    check: bool = True,
    capture_output: bool = True,
    non_interactive: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=check,
            capture_output=capture_output,
            text=True,
            stdin=subprocess.DEVNULL if non_interactive else None,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"} if non_interactive else None,
            timeout=300 if non_interactive else None,
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or "").strip() or (error.stdout or "").strip() or str(error)
        raise GitError(detail) from error
    except subprocess.TimeoutExpired as error:
        raise GitError(f"Git command timed out: {args[0]}") from error


def current_branch(root: Path) -> str:
    return run_git(root, ["branch", "--show-current"], check=True).stdout.strip()


def head_commit(root: Path) -> str:
    return run_git(root, ["rev-parse", "HEAD"], check=True).stdout.strip()


def candidate_tree(root: Path) -> str:
    return run_git(root, ["rev-parse", "HEAD^{tree}"], check=True).stdout.strip()


def dirty_porcelain(root: Path) -> str:
    return run_git(
        root, ["status", "--porcelain=v1", "--untracked-files=all"], check=True
    ).stdout


def ensure_clean(root: Path) -> None:
    dirty = dirty_porcelain(root)
    if dirty:
        raise GitError("Repository worktree is dirty:\n" + dirty.rstrip())


def ensure_no_git_operation(root: Path) -> None:
    for name in (
        "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge",
        "rebase-apply", "BISECT_LOG", "index.lock",
    ):
        path = Path(run_git(root, ["rev-parse", "--git-path", name]).stdout.strip())
        if not path.is_absolute():
            path = root / path
        if path.exists():
            raise GitError(f"Git operation in progress: {name}")
