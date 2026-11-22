from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from eng_lifecycle.cli import main
from eng_lifecycle.gitops import git_dir


def run(*args: str, cwd: Path | None = None, check: bool = True):
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


class LifecycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.bare = self.base / "origin.git"
        self.repo.mkdir()
        run("git", "init", "-b", "develop", cwd=self.repo)
        run("git", "config", "user.name", "Lifecycle Test", cwd=self.repo)
        run("git", "config", "user.email", "lifecycle@example.invalid", cwd=self.repo)
        (self.repo / ".github").mkdir()
        self.write_config()
        (self.repo / "README.md").write_text("initial\n", encoding="utf-8")
        run("git", "add", ".", cwd=self.repo)
        run("git", "commit", "-m", "Initial", cwd=self.repo)
        run("git", "init", "--bare", str(self.bare))
        run("git", "remote", "add", "origin", str(self.bare), cwd=self.repo)
        run("git", "push", "-u", "origin", "develop", cwd=self.repo)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_config(self, readiness: str = "python3 -c \"print('ready')\"") -> None:
        config = {
            "schema": 1,
            "base": "develop",
            "feature_prefix": "feature/",
            "merge_strategy": "merge",
            "commit_gate": {"commands": ["python3 -c \"pass\""]},
            "readiness_gate": {"commands": [readiness]},
            "integration_gate": {"commands": []},
            "required_ci": [],
            "special_authorization": ["docker", "database"],
        }
        path = self.repo / ".github" / "lifecycle.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(config, sort_keys=True, indent=2), encoding="utf-8"
        )

    def start(self, name: str = "increment-one") -> int:
        return main(["start", "--repo", str(self.repo), "--feature", name])

    def commit(self, message: str = "Add feature") -> int:
        path = self.repo / "feature.txt"
        path.write_text("feature\n", encoding="utf-8")
        return main(
            [
                "commit",
                "--repo",
                str(self.repo),
                "--message",
                message,
                "--path",
                "feature.txt",
            ]
        )

    def review(self, criteria: str = "Criterion A\nCriterion B\n") -> tuple[int, Path]:
        path = self.base / "acceptance.txt"
        path.write_text(criteria, encoding="utf-8")
        result = main(
            [
                "review",
                "--repo",
                str(self.repo),
                "--feature",
                "increment-one",
                "--criteria-file",
                str(path),
            ]
        )
        return result, path

    def approve(self, criteria: Path, message: str = "APPROVED") -> int:
        return main(
            [
                "approve",
                "--repo",
                str(self.repo),
                "--feature",
                "increment-one",
                "--criteria-file",
                str(criteria),
                "--message",
                message,
            ]
        )

    def test_normal_operation(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        result, criteria = self.review()
        self.assertEqual(result, 0)
        self.assertEqual(self.approve(criteria), 0)
        status = main(
            [
                "status",
                "--repo",
                str(self.repo),
                "--feature",
                "increment-one",
                "--criteria-file",
                str(criteria),
            ]
        )
        self.assertEqual(status, 0)

    def test_missing_configuration(self) -> None:
        (self.repo / ".github" / "lifecycle.json").unlink()
        result = main(["status", "--repo", str(self.repo), "--feature", "x"])
        self.assertEqual(result, 2)

    def test_hook_failure_blocks_commit(self) -> None:
        self.assertEqual(self.start(), 0)
        hooks = self.repo / ".githooks"
        hooks.mkdir()
        hook = hooks / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)
        run("git", "config", "core.hooksPath", ".githooks", cwd=self.repo)
        (self.repo / "feature.txt").write_text("feature\n", encoding="utf-8")
        result = main(
            [
                "commit",
                "--repo",
                str(self.repo),
                "--message",
                "Fail hook",
                "--path",
                "feature.txt",
            ]
        )
        self.assertEqual(result, 2)
        run("git", "status", "--porcelain", cwd=self.repo, check=True)

    def test_candidate_change_invalidates_approval(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        _, criteria = self.review()
        self.assertEqual(self.approve(criteria), 0)
        (self.repo / "feature.txt").write_text("changed\n", encoding="utf-8")
        run("git", "add", "feature.txt", cwd=self.repo)
        run("git", "commit", "-m", "Change candidate", cwd=self.repo)
        self.assertEqual(
            main(
                [
                    "status",
                    "--repo",
                    str(self.repo),
                    "--feature",
                    "increment-one",
                    "--criteria-file",
                    str(criteria),
                ]
            ),
            1,
        )

    def test_dirty_worktree_invalidates_approval(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        _, criteria = self.review()
        self.assertEqual(self.approve(criteria), 0)
        (self.repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        self.assertEqual(
            main(
                [
                    "status",
                    "--repo",
                    str(self.repo),
                    "--feature",
                    "increment-one",
                    "--criteria-file",
                    str(criteria),
                ]
            ),
            1,
        )

    def test_changed_acceptance_criteria_invalidates_approval(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        _, criteria = self.review()
        self.assertEqual(self.approve(criteria), 0)
        criteria.write_text("Changed criterion\n", encoding="utf-8")
        self.assertEqual(
            main(
                [
                    "status",
                    "--repo",
                    str(self.repo),
                    "--feature",
                    "increment-one",
                    "--criteria-file",
                    str(criteria),
                ]
            ),
            1,
        )

    def test_changed_quality_policy_invalidates_approval(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        _, criteria = self.review()
        self.assertEqual(self.approve(criteria), 0)
        self.write_config('python3 -c "print(\'changed policy\')"')
        run("git", "add", ".github/lifecycle.json", cwd=self.repo)
        run("git", "commit", "-m", "Change quality policy", cwd=self.repo)
        self.assertEqual(
            main(
                [
                    "status",
                    "--repo",
                    str(self.repo),
                    "--feature",
                    "increment-one",
                    "--criteria-file",
                    str(criteria),
                ]
            ),
            1,
        )

    def test_invalid_approval_record_is_rejected(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        _, criteria = self.review()
        self.assertEqual(self.approve(criteria), 0)
        directory = git_dir(self.repo) / "engineering-lifecycle"
        approval = next(directory.rglob("approval.json"))
        approval.write_text("{not json", encoding="utf-8")
        result = main(
            [
                "status",
                "--repo",
                str(self.repo),
                "--feature",
                "increment-one",
                "--criteria-file",
                str(criteria),
            ]
        )
        self.assertEqual(result, 1)

    def test_readiness_failure_is_captured(self) -> None:
        self.write_config('python3 -c "raise SystemExit(7)"')
        run("git", "add", ".github/lifecycle.json", cwd=self.repo)
        run("git", "commit", "-m", "Set failing readiness gate", cwd=self.repo)
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        result, _ = self.review()
        self.assertEqual(result, 1)

    def test_approval_requires_exact_message(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        _, criteria = self.review()
        self.assertEqual(self.approve(criteria, "approved"), 2)

    def test_worktree_metadata_uses_actual_git_dir(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        worktree = self.base / "linked-worktree"
        run(
            "git",
            "worktree",
            "add",
            "-b",
            "feature/linked",
            str(worktree),
            "develop",
            cwd=self.repo,
        )
        actual = git_dir(worktree)
        common = run(
            "git",
            "rev-parse",
            "--git-common-dir",
            cwd=worktree,
        ).stdout.strip()
        self.assertNotEqual(str(actual), common)
        self.assertTrue(actual.is_dir())


if __name__ == "__main__":
    unittest.main()
