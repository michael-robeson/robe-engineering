from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from eng_lifecycle.cli import main
from eng_lifecycle.config import load_config
from eng_lifecycle.evidence import sha256_bytes
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
        result = main(["status", "--repo", str(self.repo), "--feature", "x", "--criteria", "check"])
        self.assertEqual(result, 2)

    def test_hook_failure_blocks_commit(self) -> None:
        self.assertEqual(self.start(), 0)
        before = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout
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
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.repo).stdout, before)

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

    def change_policy_only(self, criteria: Path) -> None:
        commit = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout
        tree = run("git", "rev-parse", "HEAD^{tree}", cwd=self.repo).stdout
        criteria_bytes = criteria.read_bytes()
        policy = load_config(self.repo).policy_bytes()
        self.write_config('python3 -c "print(\'changed policy\')"')
        self.assertNotEqual(load_config(self.repo).policy_bytes(), policy)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.repo).stdout, commit)
        self.assertEqual(run("git", "rev-parse", "HEAD^{tree}", cwd=self.repo).stdout, tree)
        self.assertEqual(criteria.read_bytes(), criteria_bytes)

    def test_policy_only_drift_blocks_approval_of_existing_readiness(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        result, criteria = self.review()
        self.assertEqual(result, 0)
        directory = next((git_dir(self.repo) / "engineering-lifecycle").iterdir())
        evidence = (directory / "evidence.json").read_bytes()
        review = (directory / "review.json").read_bytes()
        self.change_policy_only(criteria)
        error = io.StringIO()
        with redirect_stderr(error):
            self.assertEqual(self.approve(criteria), 2)
        self.assertIn("quality policy changed", error.getvalue())
        self.assertEqual((directory / "evidence.json").read_bytes(), evidence)
        self.assertEqual((directory / "review.json").read_bytes(), review)
        self.assertFalse((directory / "approval.json").exists())

    def test_policy_only_drift_invalidates_existing_approval_status(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        result, criteria = self.review()
        self.assertEqual(result, 0)
        self.assertEqual(self.approve(criteria), 0)
        self.change_policy_only(criteria)
        output = io.StringIO()
        with redirect_stdout(output):
            result = main([
                "status", "--repo", str(self.repo), "--feature", "increment-one",
                "--criteria-file", str(criteria),
            ])
        self.assertEqual(result, 1)
        status = json.loads(output.getvalue())
        self.assertFalse(status["valid"])
        self.assertIn("quality policy changed", status["reasons"][0])

    def test_dirty_worktree_still_blocks_approval_after_evidence_validation(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        result, criteria = self.review()
        self.assertEqual(result, 0)
        (self.repo / "dirty.txt").write_text("dirty", encoding="utf-8")
        error = io.StringIO()
        with redirect_stderr(error):
            self.assertEqual(self.approve(criteria), 2)
        self.assertIn("worktree is dirty", error.getvalue().lower())
        self.assertFalse(list((git_dir(self.repo) / "engineering-lifecycle").rglob("approval.json")))

    def test_policy_drift_is_reported_before_changed_base(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        result, criteria = self.review()
        self.assertEqual(result, 0)
        self.assertEqual(self.approve(criteria), 0)
        commit = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout
        tree = run("git", "rev-parse", "HEAD^{tree}", cwd=self.repo).stdout
        criteria_bytes = criteria.read_bytes()
        path = self.repo / ".github" / "lifecycle.json"
        policy = json.loads(path.read_text(encoding="utf-8"))
        policy["base"] = "other-base"
        path.write_text(json.dumps(policy), encoding="utf-8")
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.repo).stdout, commit)
        self.assertEqual(run("git", "rev-parse", "HEAD^{tree}", cwd=self.repo).stdout, tree)
        self.assertEqual(criteria.read_bytes(), criteria_bytes)
        error = io.StringIO()
        with redirect_stderr(error):
            self.assertEqual(self.approve(criteria), 2)
        self.assertIn("quality policy changed", error.getvalue())
        output = io.StringIO()
        with redirect_stdout(output):
            result = main([
                "status", "--repo", str(self.repo), "--feature", "increment-one",
                "--criteria-file", str(criteria),
            ])
        self.assertEqual(result, 1)
        self.assertIn("quality policy changed", json.loads(output.getvalue())["reasons"][0])

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
        run("git", "push", "origin", "develop", cwd=self.repo)
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
        criteria = self.base / "linked-criteria.txt"
        criteria.write_text("Linked worktree criterion\n", encoding="utf-8")
        common_args = ["--repo", str(worktree), "--feature", "linked", "--criteria-file", str(criteria)]
        self.assertEqual(main(["review", *common_args]), 0)
        self.assertEqual(main(["approve", *common_args, "--message", "APPROVED"]), 0)
        self.assertEqual(main(["status", *common_args]), 0)
        self.assertTrue(list((actual / "engineering-lifecycle").rglob("approval.json")))

    def test_scoped_commit_rejects_existing_staged_changes(self) -> None:
        self.assertEqual(self.start(), 0)
        (self.repo / "unrelated.txt").write_text("unrelated", encoding="utf-8")
        run("git", "add", "unrelated.txt", cwd=self.repo)
        before = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout
        index = run("git", "write-tree", cwd=self.repo).stdout
        self.assertEqual(self.commit(), 2)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.repo).stdout, before)
        self.assertEqual(run("git", "write-tree", cwd=self.repo).stdout, index)

    def test_hook_validates_staged_blobs_not_worktree(self) -> None:
        self.assertEqual(self.start(), 0)
        hook = Path(__file__).resolve().parents[1] / ".githooks" / "check-staged.py"
        source = self.repo / "sample.py"
        source.write_text("def broken(:\n", encoding="utf-8")
        run("git", "add", "sample.py", cwd=self.repo)
        source.write_text("value = 1\n", encoding="utf-8")
        self.assertNotEqual(run("python3", str(hook), cwd=self.repo, check=False).returncode, 0)
        run("git", "add", "sample.py", cwd=self.repo)
        source.write_text("def broken(:\n", encoding="utf-8")
        self.assertEqual(run("python3", str(hook), cwd=self.repo, check=False).returncode, 0)

    def test_wrong_feature_rejected_for_all_review_commands(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        result, criteria = self.review()
        self.assertEqual(result, 0)
        for command in ("review", "approve", "status"):
            args = [command, "--repo", str(self.repo), "--feature", "wrong", "--criteria-file", str(criteria)]
            if command == "approve":
                args += ["--message", "APPROVED"]
            self.assertEqual(main(args), 2)

    def test_empty_and_malformed_required_checks_fail(self) -> None:
        self.assertEqual(self.start(), 0)
        path = self.repo / ".github" / "lifecycle.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        for commands in ([], [""], ["'"], [123], [{"argv": ["true"], "authorization": "unknown"}]):
            config["readiness_gate"]["commands"] = commands
            path.write_text(json.dumps(config), encoding="utf-8")
            self.assertEqual(main(["review", "--repo", str(self.repo), "--feature", "increment-one", "--criteria", "check"]), 2)

    def test_authorized_check_is_not_run_without_authorization(self) -> None:
        self.assertEqual(self.start(), 0)
        path = self.repo / ".github" / "lifecycle.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        marker = self.base / "ran"
        config["readiness_gate"]["commands"] = [{
            "argv": ["python3", "-c", f"open({str(marker)!r}, 'w').write('ran')"],
            "authorization": "database",
        }]
        path.write_text(json.dumps(config), encoding="utf-8")
        run("git", "add", ".github/lifecycle.json", cwd=self.repo)
        run("git", "commit", "-m", "Configure authorized check", cwd=self.repo)
        args = ["review", "--repo", str(self.repo), "--feature", "increment-one", "--criteria", "check"]
        self.assertEqual(main(args), 1)
        self.assertFalse(marker.exists())
        self.assertEqual(main(["approve", "--repo", str(self.repo), "--feature", "increment-one", "--criteria", "check", "--message", "APPROVED"]), 2)
        self.assertEqual(main([*args, "--authorize", "database"]), 0)
        self.assertTrue(marker.exists())

    def test_interrupted_review_invalidates_previous_success(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        result, criteria = self.review()
        self.assertEqual(result, 0)
        self.assertEqual(self.approve(criteria), 0)
        with patch("eng_lifecycle.cli.run_command", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.review()
        self.assertEqual(self.approve(criteria), 2)
        self.assertEqual(main(["status", "--repo", str(self.repo), "--feature", "increment-one", "--criteria-file", str(criteria)]), 1)

    def test_tampered_review_or_evidence_cannot_be_approved(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        result, criteria = self.review()
        self.assertEqual(result, 0)
        directory = next((git_dir(self.repo) / "engineering-lifecycle").iterdir())
        evidence_path = directory / "evidence.json"
        review_path = directory / "review.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["commands"] = []
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review["evidence_sha256"] = sha256_bytes(evidence_path.read_bytes())
        review_path.write_text(json.dumps(review), encoding="utf-8")
        self.assertEqual(self.approve(criteria), 2)
        self.assertFalse((directory / "approval.json").exists())

    def test_fresh_successful_review_preserves_approval(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        result, criteria = self.review()
        self.assertEqual(result, 0)
        self.assertEqual(self.approve(criteria), 0)
        self.assertEqual(self.review()[0], 0)
        self.assertEqual(main(["status", "--repo", str(self.repo), "--feature", "increment-one", "--criteria-file", str(criteria)]), 0)

    def test_readiness_check_mutating_worktree_fails(self) -> None:
        self.assertEqual(self.start(), 0)
        self.write_config('python3 -c "open(\'unexpected\', \'w\').write(\'x\')"')
        run("git", "add", ".github/lifecycle.json", cwd=self.repo)
        run("git", "commit", "-m", "Configure mutating check", cwd=self.repo)
        self.assertEqual(self.review()[0], 2)
        self.assertEqual(self.approve(self.base / "acceptance.txt"), 2)

    def test_start_rejects_local_ahead_and_dirty_state(self) -> None:
        (self.repo / "README.md").write_text("ahead\n", encoding="utf-8")
        run("git", "add", "README.md", cwd=self.repo)
        run("git", "commit", "-m", "Local ahead", cwd=self.repo)
        before = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout
        self.assertEqual(self.start(), 2)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.repo).stdout, before)
        (self.repo / "dirty").write_text("dirty", encoding="utf-8")
        self.assertEqual(self.start(), 2)

    def test_start_fast_forwards_remote_ahead(self) -> None:
        other = self.base / "other"
        run("git", "clone", "-b", "develop", str(self.bare), str(other))
        run("git", "config", "user.name", "Lifecycle Test", cwd=other)
        run("git", "config", "user.email", "lifecycle@example.invalid", cwd=other)
        (other / "new").write_text("remote", encoding="utf-8")
        run("git", "add", "new", cwd=other)
        run("git", "commit", "-m", "Remote ahead", cwd=other)
        run("git", "push", "origin", "develop", cwd=other)
        remote = run("git", "rev-parse", "HEAD", cwd=other).stdout
        self.assertEqual(self.start(), 0)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.repo).stdout, remote)

    def test_start_rejects_diverged_and_in_progress_git_state(self) -> None:
        other = self.base / "other"
        run("git", "clone", "-b", "develop", str(self.bare), str(other))
        run("git", "config", "user.name", "Lifecycle Test", cwd=other)
        run("git", "config", "user.email", "lifecycle@example.invalid", cwd=other)
        (other / "remote").write_text("remote", encoding="utf-8")
        run("git", "add", "remote", cwd=other)
        run("git", "commit", "-m", "Remote", cwd=other)
        run("git", "push", "origin", "develop", cwd=other)
        (self.repo / "local").write_text("local", encoding="utf-8")
        run("git", "add", "local", cwd=self.repo)
        run("git", "commit", "-m", "Local", cwd=self.repo)
        before = run("git", "rev-parse", "HEAD", cwd=self.repo).stdout
        self.assertEqual(self.start(), 2)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.repo).stdout, before)
        (git_dir(self.repo) / "MERGE_HEAD").write_text(before, encoding="utf-8")
        self.assertEqual(self.start(), 2)

    def test_missing_or_mismatched_review_evidence_is_rejected(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        _, criteria = self.review()
        directory = next((git_dir(self.repo) / "engineering-lifecycle").iterdir())
        evidence = directory / "evidence.json"
        original = evidence.read_text(encoding="utf-8")
        evidence.unlink()
        self.assertEqual(self.approve(criteria), 2)
        evidence.write_text(original + " ", encoding="utf-8")
        self.assertEqual(self.approve(criteria), 2)
        self.assertFalse((directory / "approval.json").exists())

    def test_semantically_invalid_approval_record_is_rejected(self) -> None:
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.commit(), 0)
        _, criteria = self.review()
        self.assertEqual(self.approve(criteria), 0)
        approval = next((git_dir(self.repo) / "engineering-lifecycle").rglob("approval.json"))
        record = json.loads(approval.read_text(encoding="utf-8"))
        record["approved_at"] = ""
        approval.write_text(json.dumps(record), encoding="utf-8")
        self.assertEqual(main(["status", "--repo", str(self.repo), "--feature", "increment-one", "--criteria-file", str(criteria)]), 1)

    def test_verification_entrypoint_propagates_unit_test_failure(self) -> None:
        fixture = self.base / "verification"
        (fixture / "scripts").mkdir(parents=True)
        (fixture / "src").mkdir()
        (fixture / "tests").mkdir()
        script = Path(__file__).resolve().parents[1] / "scripts" / "verify"
        shutil.copy2(script, fixture / "scripts" / "verify")
        (fixture / "tests" / "test_failure.py").write_text(
            "import unittest\n"
            "class Failure(unittest.TestCase):\n"
            "    def test_failure(self):\n"
            "        self.fail('expected failure')\n",
            encoding="utf-8",
        )
        result = run("sh", str(fixture / "scripts" / "verify"), cwd=self.base, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected failure", result.stderr)

    def test_verification_entrypoint_propagates_compile_failure(self) -> None:
        fixture = self.base / "verification"
        (fixture / "scripts").mkdir(parents=True)
        (fixture / "src").mkdir()
        (fixture / "tests").mkdir()
        script = Path(__file__).resolve().parents[1] / "scripts" / "verify"
        shutil.copy2(script, fixture / "scripts" / "verify")
        (fixture / "src" / "broken.py").write_text("def broken(:\n", encoding="utf-8")
        result = run("sh", str(fixture / "scripts" / "verify"), cwd=self.base, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SyntaxError", result.stdout)


if __name__ == "__main__":
    unittest.main()
