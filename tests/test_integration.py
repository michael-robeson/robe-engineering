from __future__ import annotations

import io
import itertools
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from eng_lifecycle.cli import main
from eng_lifecycle.config import LifecycleError
from eng_lifecycle.gitops import run_git
from eng_lifecycle.integration import integration_lock, required_checks


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


class FakeGitHub:
    def __init__(self, repo: Path, bare: Path, parent: Path) -> None:
        self.repo, self.bare, self.parent = repo, bare, parent
        self.pr: dict[str, object] | None = None
        self.created = 0
        self.merged = 0
        self.unresolved = False
        self.review_commit: str | None = None
        self.review_state: str | None = "APPROVED"
        self.review_author = "reviewer"

    def create_pr(self) -> None:
        self.pr = {
            "number": 7,
            "state": "OPEN",
            "baseRefName": "develop",
            "baseRefOid": git(self.repo, "rev-parse", "develop"),
            "headRefName": "feature/example",
            "headRefOid": git(self.repo, "rev-parse", "HEAD"),
            "isCrossRepository": False,
            "isDraft": False,
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "mergeCommit": None,
            "reviewDecision": "APPROVED",
            "author": {"login": "contributor"},
            "statusCheckRollup": [
                {"name": "unit", "status": "COMPLETED", "conclusion": "SUCCESS"}
            ],
            "url": "https://github.com/example/repo/pull/7",
        }

    def json_call(self, root: Path, args: list[str]) -> object:
        if args[:2] == ["pr", "list"]:
            return [] if self.pr is None else [self.pr.copy()]
        if args[:2] == ["pr", "view"]:
            if self.pr is None:
                raise AssertionError("Missing simulated PR")
            return self.pr.copy()
        if args[:2] == ["api", "graphql"]:
            if any("latestOpinionatedReviews" in arg for arg in args):
                assert self.pr is not None
                nodes = [] if self.review_state is None else [{
                    "state": self.review_state,
                    "commit": {"oid": self.review_commit or self.pr["headRefOid"]},
                    "author": {"login": self.review_author},
                }]
                return {
                    "data": {"repository": {"pullRequest": {"latestOpinionatedReviews": {
                        "nodes": nodes,
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }}}}
                }
            return {
                "data": {"repository": {"pullRequest": {"reviewThreads": {
                    "nodes": [{"isResolved": not self.unresolved}],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }}}}
            }
        raise AssertionError(args)

    def command(self, root: Path, args: list[str]) -> str:
        if args[:2] in (["pr", "list"], ["pr", "view"], ["api", "graphql"]):
            return json.dumps(self.json_call(root, args))
        if args[:2] == ["pr", "create"]:
            self.created += 1
            self.create_pr()
            return ""
        if args[:2] == ["pr", "merge"]:
            if self.pr is None:
                raise AssertionError("Missing simulated PR")
            self.merged += 1
            clone = self.parent / "merge-clone"
            subprocess.run(
                ["git", "clone", "-b", "develop", str(self.bare), str(clone)],
                check=True, capture_output=True, text=True,
            )
            git(clone, "config", "user.name", "Integration Test")
            git(clone, "config", "user.email", "integration@example.invalid")
            git(clone, "merge", "--no-ff", "origin/feature/example", "-m", "Merge feature")
            git(clone, "push", "origin", "develop")
            self.pr["state"] = "MERGED"
            self.pr["mergeCommit"] = {"oid": git(clone, "rev-parse", "HEAD")}
            return ""
        raise AssertionError(args)


class IntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.bare = self.base / "origin.git"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "develop")
        git(self.repo, "config", "user.name", "Integration Test")
        git(self.repo, "config", "user.email", "integration@example.invalid")
        (self.repo / ".github").mkdir()
        config = {
            "schema": 1, "base": "develop", "feature_prefix": "feature/",
            "merge_strategy": "merge", "commit_gate": {"commands": []},
            "readiness_gate": {"commands": [["python3", "-c", "pass"]]},
            "integration_gate": {"commands": []}, "required_ci": ["unit"],
            "required_review": True, "special_authorization": ["database"],
        }
        (self.repo / ".github" / "lifecycle.json").write_text(json.dumps(config), encoding="utf-8")
        (self.repo / "README.md").write_text("initial\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "Initial")
        subprocess.run(["git", "init", "--bare", str(self.bare)], check=True, capture_output=True)
        git(self.repo, "remote", "add", "origin", str(self.bare))
        git(self.repo, "push", "-u", "origin", "develop")
        self.criteria = self.base / "criteria.txt"
        self.criteria.write_text("A verified change\n", encoding="utf-8")
        self.args = [
            "--repo", str(self.repo), "--feature", "example", "--criteria-file", str(self.criteria)
        ]
        git(self.repo, "switch", "-c", "feature/example")
        (self.repo / "feature.txt").write_text("feature\n", encoding="utf-8")
        self.assertEqual(main([
            "commit", "--repo", str(self.repo), "--message", "Feature", "--path", "feature.txt"
        ]), 0)
        self.assertEqual(main(["review", *self.args]), 0)
        self.candidate = git(self.repo, "rev-parse", "HEAD")
        self.fake = FakeGitHub(self.repo, self.bare, self.base)
        self.patchers = [
            patch("eng_lifecycle.integration.origin_repository", return_value=("github.com", "example", "repo")),
            patch("eng_lifecycle.integration.gh", side_effect=self.fake.command),
        ]
        for item in self.patchers:
            item.start()

    def tearDown(self) -> None:
        for item in self.patchers:
            item.stop()
        self.temp.cleanup()

    def approve(self) -> None:
        self.assertEqual(main(["approve", *self.args, "--message", "APPROVED"]), 0)

    def update_policy(self, **changes: object) -> None:
        path = self.repo / ".github" / "lifecycle.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        for key, value in changes.items():
            if value is None:
                config.pop(key, None)
            else:
                config[key] = value
        path.write_text(json.dumps(config), encoding="utf-8")
        git(self.repo, "add", ".github/lifecycle.json")
        git(self.repo, "commit", "-m", "Update integration policy")
        self.assertEqual(main(["review", *self.args]), 0)
        self.candidate = git(self.repo, "rev-parse", "HEAD")

    def call(self, command: str = "integrate") -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            result = main([command, *self.args])
        return result, output.getvalue()

    def remote_feature(self) -> str:
        return git(self.repo, "ls-remote", "--heads", "origin", "refs/heads/feature/example")

    def working_branch(self, output: str) -> str:
        result = json.loads(output)
        branch = result["working_branch"]
        self.assertRegex(branch, r"^feature/next-[0-9a-f]{32}$")
        return branch

    def test_integration_merges_synchronizes_and_cleans_up(self) -> None:
        self.approve()
        result, output = self.call()
        self.assertEqual(result, 0, output)
        self.assertEqual(self.fake.created, 1)
        self.assertEqual(self.fake.merged, 1)
        working_branch = self.working_branch(output)
        self.assertEqual(git(self.repo, "branch", "--show-current"), working_branch)
        self.assertEqual(self.remote_feature(), "")
        self.assertEqual(git(self.repo, "branch", "--list", "feature/example"), "")
        self.assertNotEqual(git(self.repo, "branch", "--list", working_branch), "")
        self.assertEqual(
            git(self.repo, "ls-remote", "--heads", "origin", f"refs/heads/{working_branch}"),
            "",
        )
        git(self.repo, "merge-base", "--is-ancestor", self.candidate, "HEAD")
        result, output = self.call("resume")
        self.assertEqual(result, 0, output)
        self.assertEqual(self.working_branch(output), working_branch)
        self.assertEqual(self.fake.created, 1)
        self.assertEqual(self.fake.merged, 1)

    def test_resume_after_working_branch_creation_interruption_reuses_branch(self) -> None:
        self.approve()
        original = run_git
        interrupted = False

        def create_then_interrupt(root: Path, args: list[str], **kwargs):
            nonlocal interrupted
            result = original(root, args, **kwargs)
            if (
                not interrupted
                and args[:2] == ["switch", "-c"]
                and args[2].startswith("feature/next-")
            ):
                interrupted = True
                raise LifecycleError("interrupted after working branch creation")
            return result

        with patch("eng_lifecycle.integration.run_git", side_effect=create_then_interrupt):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("interrupted", output)
        working_branch = git(self.repo, "branch", "--show-current")
        self.assertRegex(working_branch, r"^feature/next-[0-9a-f]{32}$")
        result, output = self.call("resume")
        self.assertEqual(result, 0, output)
        self.assertEqual(self.working_branch(output), working_branch)
        self.assertEqual(
            git(
                self.repo,
                "branch",
                "--format=%(refname:short)",
                "--list",
                "feature/next-*",
            ).splitlines(),
            [working_branch],
        )

    def test_generated_branch_collision_retries_without_overwriting(self) -> None:
        self.approve()
        local_collision = "a" * 32
        remote_collision = "b" * 32
        selected = "c" * 32
        local_branch = f"feature/next-{local_collision}"
        remote_branch = f"feature/next-{remote_collision}"
        git(self.repo, "branch", local_branch, "develop")
        local_tip = git(self.repo, "rev-parse", f"refs/heads/{local_branch}")
        git(self.repo, "push", "origin", f"develop:refs/heads/{remote_branch}")
        remote_tip = git(self.repo, "ls-remote", "--heads", "origin", f"refs/heads/{remote_branch}").split()[0]
        generated = iter((local_collision, remote_collision, selected))
        with patch(
            "eng_lifecycle.integration.uuid.uuid4",
            side_effect=lambda: SimpleNamespace(hex=next(generated)),
        ):
            result, output = self.call()
        self.assertEqual(result, 0, output)
        self.assertEqual(self.working_branch(output), f"feature/next-{selected}")
        self.assertEqual(
            git(self.repo, "rev-parse", f"refs/heads/{local_branch}"),
            local_tip,
        )
        self.assertEqual(
            git(self.repo, "ls-remote", "--heads", "origin", f"refs/heads/{remote_branch}").split()[0],
            remote_tip,
        )

    def test_resume_does_not_replace_work_on_generated_branch(self) -> None:
        self.approve()
        result, output = self.call()
        self.assertEqual(result, 0, output)
        working_branch = self.working_branch(output)
        (self.repo / "later.txt").write_text("keep this work\n", encoding="utf-8")
        git(self.repo, "add", "later.txt")
        git(self.repo, "commit", "-m", "Work after integration")
        work_commit = git(self.repo, "rev-parse", "HEAD")
        result, output = self.call("resume")
        self.assertEqual(result, 2)
        self.assertIn("working branch changed", output)
        self.assertEqual(git(self.repo, "branch", "--show-current"), working_branch)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), work_commit)
        self.assertEqual((self.repo / "later.txt").read_text(encoding="utf-8"), "keep this work\n")

    def test_no_approval_blocks_all_remote_actions(self) -> None:
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("missing", output.lower())
        self.assertEqual(self.remote_feature(), "")
        self.assertEqual(self.fake.created, 0)

    def test_missing_policy_blocks_before_push(self) -> None:
        self.update_policy(required_ci=[])
        self.approve()
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("required_ci", output)
        self.assertEqual(self.remote_feature(), "")

    def test_absent_ci_policy_blocks_before_push(self) -> None:
        self.update_policy(required_ci=None)
        self.approve()
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("required_ci", output)
        self.assertEqual(self.remote_feature(), "")

    def test_missing_review_policy_blocks_before_push(self) -> None:
        self.update_policy(required_review=None)
        self.approve()
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("required_review", output)
        self.assertEqual(self.remote_feature(), "")

    def test_unsupported_merge_strategy_blocks_before_push(self) -> None:
        self.update_policy(merge_strategy="squash")
        self.approve()
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("merge commits only", output)
        self.assertEqual(self.remote_feature(), "")

    def test_divergent_local_base_blocks_before_push(self) -> None:
        self.approve()
        tree = git(self.repo, "rev-parse", "develop^{tree}")
        base = git(self.repo, "rev-parse", "develop")
        other = git(self.repo, "commit-tree", tree, "-p", base, "-m", "Unpushed base change")
        git(self.repo, "update-ref", "refs/heads/develop", other, base)
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("Local base is ahead", output)
        self.assertEqual(self.remote_feature(), "")
        self.assertEqual(self.fake.merged, 0)

    def test_remote_base_change_blocks_before_push(self) -> None:
        self.approve()
        clone = self.base / "other-base"
        subprocess.run(
            ["git", "clone", "-b", "develop", str(self.bare), str(clone)],
            check=True, capture_output=True, text=True,
        )
        git(clone, "config", "user.name", "Integration Test")
        git(clone, "config", "user.email", "integration@example.invalid")
        (clone / "base.txt").write_text("new base\n", encoding="utf-8")
        git(clone, "add", "base.txt")
        git(clone, "commit", "-m", "Advance base")
        git(clone, "push", "origin", "develop")
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("Remote base changed", output)
        self.assertEqual(self.remote_feature(), "")
        self.assertEqual(self.fake.merged, 0)

    def test_final_verification_failure_blocks_push(self) -> None:
        self.update_policy(integration_gate={"commands": [["python3", "-c", "raise SystemExit(4)"]]})
        self.approve()
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("Integration check failed", output)
        self.assertEqual(self.remote_feature(), "")

    def test_final_verification_has_no_interactive_input(self) -> None:
        self.update_policy(integration_gate={"commands": [[
            "python3", "-c", "import sys; assert sys.stdin.read() == ''",
        ]]})
        self.approve()
        result, output = self.call()
        self.assertEqual(result, 0, output)

    def test_final_verification_mutating_candidate_blocks_push(self) -> None:
        self.update_policy(integration_gate={"commands": [[
            "python3", "-c", "open('README.md', 'w').write('changed')",
        ]]})
        self.approve()
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("worktree is dirty", output.lower())
        self.assertEqual(self.remote_feature(), "")

    def test_unauthorized_integration_check_is_not_run(self) -> None:
        marker = self.base / "sensitive-check-ran"
        self.update_policy(integration_gate={"commands": [{
            "argv": ["python3", "-c", f"open({str(marker)!r}, 'w').write('ran')"],
            "authorization": "database",
        }]})
        self.approve()
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("requires authorization", output)
        self.assertFalse(marker.exists())
        self.assertEqual(self.remote_feature(), "")

    def test_missing_check_times_out_without_merge(self) -> None:
        self.approve()
        self.fake.create_pr()
        assert self.fake.pr is not None
        self.fake.pr["statusCheckRollup"] = []
        with patch("eng_lifecycle.integration.monotonic", side_effect=itertools.count(0, 1000)):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("Timed out", output)
        self.assertEqual(self.fake.merged, 0)

    def test_pending_ci_and_unknown_mergeability_are_polled(self) -> None:
        self.approve()
        self.fake.create_pr()
        original = self.fake.command
        views = 0

        def eventually_ready(root: Path, args: list[str]) -> str:
            nonlocal views
            if args[:2] == ["pr", "view"]:
                views += 1
                assert self.fake.pr is not None
                if views == 1:
                    self.fake.pr["statusCheckRollup"] = []
                elif views == 2:
                    self.fake.pr["statusCheckRollup"] = [
                        {"name": "unit", "status": "COMPLETED", "conclusion": "SUCCESS"}
                    ]
                    self.fake.pr["mergeable"] = "UNKNOWN"
                else:
                    self.fake.pr["mergeable"] = "MERGEABLE"
            return original(root, args)

        with patch("eng_lifecycle.integration.gh", side_effect=eventually_ready), \
                patch("eng_lifecycle.integration.sleep") as sleep:
            result, output = self.call()
        self.assertEqual(result, 0, output)
        self.assertEqual(sleep.call_count, 2)

    def test_skipped_and_duplicate_required_checks_fail_closed(self) -> None:
        pr: dict[str, object] = {"statusCheckRollup": [
            {"name": "unit", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "unit", "status": "COMPLETED", "conclusion": "SKIPPED"},
        ]}
        with self.assertRaisesRegex(LifecycleError, "failed or was skipped"):
            required_checks(pr, ["unit"])
        pr["statusCheckRollup"] = [
            {"name": "unit", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "unit", "status": "COMPLETED", "conclusion": "SUCCESS"},
        ]
        with self.assertRaisesRegex(LifecycleError, "Ambiguous duplicate"):
            required_checks(pr, ["unit"])

    def test_missing_pull_request_base_sha_fails_closed(self) -> None:
        self.approve()
        self.fake.create_pr()
        assert self.fake.pr is not None
        self.fake.pr["baseRefOid"] = None
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("baseRefOid", output)
        self.assertEqual(self.remote_feature(), "")

    def test_failing_ci_and_unresolved_reviews_block_merge(self) -> None:
        self.approve()
        self.fake.create_pr()
        assert self.fake.pr is not None
        self.fake.pr["statusCheckRollup"] = [
            {"name": "unit", "status": "COMPLETED", "conclusion": "FAILURE"}
        ]
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("required CI", output)
        self.assertEqual(self.fake.merged, 0)
        self.fake.pr["statusCheckRollup"] = [
            {"name": "unit", "status": "COMPLETED", "conclusion": "SUCCESS"}
        ]
        self.fake.unresolved = True
        result, output = self.call("resume")
        self.assertEqual(result, 2)
        self.assertIn("unresolved", output)
        self.assertEqual(self.fake.merged, 0)

    def test_missing_required_review_blocks_merge(self) -> None:
        self.approve()
        self.fake.create_pr()
        assert self.fake.pr is not None
        self.fake.pr["reviewDecision"] = None
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("review policy", output)
        self.assertEqual(self.fake.merged, 0)

    def test_self_review_does_not_satisfy_required_review(self) -> None:
        self.approve()
        self.fake.create_pr()
        self.fake.review_author = "Contributor"
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("No independent approving", output)
        self.assertEqual(self.fake.merged, 0)

    def test_unverifiable_pr_author_blocks_integration(self) -> None:
        self.approve()
        self.fake.create_pr()
        assert self.fake.pr is not None
        self.fake.pr["author"] = None
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("author cannot be verified", output)
        self.assertEqual(self.remote_feature(), "")

    def test_partial_graphql_error_blocks_merge(self) -> None:
        self.approve()
        self.fake.create_pr()
        original = self.fake.json_call

        def partial(root: Path, args: list[str]) -> str:
            response = original(root, args)
            if args[:2] == ["api", "graphql"]:
                assert isinstance(response, dict)
                response["errors"] = [{"message": "Incomplete data"}]
            return json.dumps(response)

        with patch("eng_lifecycle.integration.gh", side_effect=partial):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("state cannot be verified", output)
        self.assertEqual(self.fake.merged, 0)

    def test_stale_review_on_older_commit_blocks_merge(self) -> None:
        self.approve()
        self.fake.create_pr()
        self.fake.review_commit = git(self.repo, "rev-parse", "develop")
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("bound to the approved candidate", output)
        self.assertEqual(self.fake.merged, 0)

    def test_candidate_review_rechecked_before_merge(self) -> None:
        self.approve()
        self.fake.create_pr()
        original = self.fake.command
        reviews = 0

        def stale_on_recheck(root: Path, args: list[str]) -> str:
            nonlocal reviews
            if args[:2] == ["api", "graphql"] and any("latestOpinionatedReviews" in arg for arg in args):
                reviews += 1
                if reviews == 2:
                    self.fake.review_commit = git(self.repo, "rev-parse", "develop")
            return original(root, args)

        with patch("eng_lifecycle.integration.gh", side_effect=stale_on_recheck):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("bound to the approved candidate", output)
        self.assertEqual(self.fake.merged, 0)

    def test_paginated_review_changes_requested_block_merge(self) -> None:
        self.approve()
        self.fake.create_pr()
        original = self.fake.command

        def paginated(root: Path, args: list[str]) -> str:
            if args[:2] == ["api", "graphql"] and any("latestOpinionatedReviews" in arg for arg in args):
                if "cursor=next" in args:
                    nodes = [{"state": "CHANGES_REQUESTED"}]
                    page = {"hasNextPage": False, "endCursor": None}
                else:
                    nodes = [{"state": "APPROVED", "commit": {"oid": self.candidate},
                              "author": {"login": "reviewer"}}]
                    page = {"hasNextPage": True, "endCursor": "next"}
                return json.dumps({"data": {"repository": {"pullRequest": {
                    "latestOpinionatedReviews": {"nodes": nodes, "pageInfo": page}
                }}}})
            return original(root, args)

        with patch("eng_lifecycle.integration.gh", side_effect=paginated):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("changes requested", output)
        self.assertEqual(self.fake.merged, 0)

    def test_malformed_review_response_blocks_merge(self) -> None:
        self.approve()
        self.fake.create_pr()
        original = self.fake.command

        def malformed(root: Path, args: list[str]) -> str:
            if args[:2] == ["api", "graphql"] and any("latestOpinionatedReviews" in arg for arg in args):
                return json.dumps({"data": {"repository": {"pullRequest": {
                    "latestOpinionatedReviews": {
                        "nodes": [{"state": "APPROVED", "commit": None, "author": None}],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }}}})
            return original(root, args)

        with patch("eng_lifecycle.integration.gh", side_effect=malformed):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("no commit or author", output)
        self.assertEqual(self.fake.merged, 0)

    def test_concurrent_integration_blocked_and_lock_released(self) -> None:
        self.approve()
        other = self.base / "other-worktree"
        git(self.repo, "worktree", "add", "--detach", str(other))
        with integration_lock(other, "feature/example"):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("already running", output)
        self.assertEqual(self.remote_feature(), "")
        result, output = self.call("resume")
        self.assertEqual(result, 0, output)

    def test_paginated_unresolved_thread_blocks_merge(self) -> None:
        self.approve()
        self.fake.create_pr()
        original = self.fake.command

        def paginated(root: Path, args: list[str]) -> str:
            if args[:2] == ["api", "graphql"] and any("reviewThreads" in arg for arg in args):
                second = "cursor=next" in args
                return json.dumps({"data": {"repository": {"pullRequest": {"reviewThreads": {
                    "nodes": [{"isResolved": not second}],
                    "pageInfo": {"hasNextPage": not second, "endCursor": None if second else "next"},
                }}}}})
            return original(root, args)

        with patch("eng_lifecycle.integration.gh", side_effect=paginated):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("unresolved", output)
        self.assertEqual(self.fake.merged, 0)

    def test_review_pagination_without_cursor_fails_closed(self) -> None:
        self.approve()
        self.fake.create_pr()
        original = self.fake.command

        def malformed(root: Path, args: list[str]) -> str:
            if args[:2] == ["api", "graphql"] and any("latestOpinionatedReviews" in arg for arg in args):
                return json.dumps({"data": {"repository": {"pullRequest": {
                    "latestOpinionatedReviews": {
                        "nodes": [], "pageInfo": {"hasNextPage": True, "endCursor": None},
                    }
                }}}})
            return original(root, args)

        with patch("eng_lifecycle.integration.gh", side_effect=malformed):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("review pagination", output)
        self.assertEqual(self.fake.merged, 0)

    def test_review_change_after_checks_blocks_merge(self) -> None:
        self.approve()
        self.fake.create_pr()
        original = self.fake.command
        views = 0

        def changed_review(root: Path, args: list[str]) -> str:
            nonlocal views
            if args[:2] == ["pr", "view"]:
                views += 1
                if views == 2:
                    assert self.fake.pr is not None
                    self.fake.pr["reviewDecision"] = "CHANGES_REQUESTED"
            return original(root, args)

        with patch("eng_lifecycle.integration.gh", side_effect=changed_review):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("review policy", output)
        self.assertEqual(self.fake.merged, 0)

    def test_ci_regression_after_checks_blocks_merge(self) -> None:
        self.approve()
        self.fake.create_pr()
        original = self.fake.command
        views = 0

        def changed_checks(root: Path, args: list[str]) -> str:
            nonlocal views
            if args[:2] == ["pr", "view"]:
                views += 1
                if views == 2:
                    assert self.fake.pr is not None
                    self.fake.pr["statusCheckRollup"] = [
                        {"name": "unit", "status": "COMPLETED", "conclusion": "FAILURE"}
                    ]
            return original(root, args)

        with patch("eng_lifecycle.integration.gh", side_effect=changed_checks):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("required CI", output)
        self.assertEqual(self.fake.merged, 0)

    def test_explicit_no_review_policy_allows_unreviewed_pr(self) -> None:
        self.update_policy(required_review=False)
        self.approve()
        self.fake.create_pr()
        assert self.fake.pr is not None
        self.fake.pr["reviewDecision"] = None
        self.fake.review_state = None
        result, output = self.call()
        self.assertEqual(result, 0, output)
        self.assertEqual(self.fake.merged, 1)

    def test_optional_review_does_not_bypass_github_required_review(self) -> None:
        self.update_policy(required_review=False)
        self.approve()
        self.fake.create_pr()
        assert self.fake.pr is not None
        self.fake.pr["reviewDecision"] = "REVIEW_REQUIRED"
        self.fake.review_state = None
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("review policy", output)
        self.assertEqual(self.fake.merged, 0)

    def test_optional_review_with_missing_decision_fails_closed(self) -> None:
        self.update_policy(required_review=False)
        self.approve()
        self.fake.create_pr()
        assert self.fake.pr is not None
        del self.fake.pr["reviewDecision"]
        self.fake.review_state = None
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("review decision", output)
        self.assertEqual(self.fake.merged, 0)

    def test_optional_review_does_not_bypass_failed_ci(self) -> None:
        self.update_policy(required_review=False)
        self.approve()
        self.fake.create_pr()
        assert self.fake.pr is not None
        self.fake.pr["reviewDecision"] = None
        self.fake.review_state = None
        self.fake.pr["statusCheckRollup"] = [
            {"name": "unit", "status": "COMPLETED", "conclusion": "FAILURE"}
        ]
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("required CI", output)
        self.assertEqual(self.fake.merged, 0)

    def test_optional_review_still_blocks_requested_changes(self) -> None:
        self.update_policy(required_review=False)
        self.approve()
        self.fake.create_pr()
        assert self.fake.pr is not None
        self.fake.pr["reviewDecision"] = None
        self.fake.review_state = "CHANGES_REQUESTED"
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("changes requested", output)
        self.assertEqual(self.fake.merged, 0)

    def test_resume_after_merge_and_local_sync(self) -> None:
        self.approve()
        with patch("eng_lifecycle.integration.remote_feature_tip", side_effect=LifecycleError("interrupted")):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("interrupted", output)
        self.assertEqual(self.fake.merged, 1)
        self.assertEqual(git(self.repo, "branch", "--show-current"), "develop")
        self.assertNotEqual(self.remote_feature(), "")
        result, output = self.call("resume")
        self.assertEqual(result, 0, output)
        self.assertEqual(self.fake.merged, 1)
        self.assertEqual(self.remote_feature(), "")

    def test_remote_branch_race_is_blocked_by_lease(self) -> None:
        self.approve()
        remote_change = self.base / "remote-change"
        original_run_git = run_git

        def race(
            root: Path, args: list[str], *, check: bool = True, capture_output: bool = True
        ):
            if args and args[0] == "push" and any(arg.startswith("--force-with-lease=") for arg in args):
                subprocess.run(
                    ["git", "clone", "-b", "feature/example", str(self.bare), str(remote_change)],
                    check=True, capture_output=True, text=True,
                )
                git(remote_change, "config", "user.name", "Integration Test")
                git(remote_change, "config", "user.email", "integration@example.invalid")
                (remote_change / "later.txt").write_text("later\n", encoding="utf-8")
                git(remote_change, "add", "later.txt")
                git(remote_change, "commit", "-m", "Remote advanced")
                git(remote_change, "push", "origin", "feature/example")
            return original_run_git(root, args, check=check, capture_output=capture_output)

        with patch("eng_lifecycle.integration.run_git", side_effect=race):
            result, output = self.call()
        self.assertEqual(result, 2, output)
        self.assertIn("stale info", output)
        self.assertNotEqual(self.remote_feature(), "")
        self.assertNotEqual(self.remote_feature().split()[0], self.candidate)
        self.assertNotEqual(git(self.repo, "branch", "--list", "feature/example"), "")

    def test_resume_after_pr_creation_interruption_does_not_duplicate(self) -> None:
        self.approve()
        original = self.fake.command

        def interrupted(root: Path, args: list[str]) -> str:
            result = original(root, args)
            if args[:2] == ["pr", "create"]:
                raise LifecycleError("interrupted after PR creation")
            return result

        with patch("eng_lifecycle.integration.gh", side_effect=interrupted):
            result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("interrupted", output)
        self.assertEqual(self.fake.created, 1)
        result, output = self.call("resume")
        self.assertEqual(result, 0, output)
        self.assertEqual(self.fake.created, 1)
        self.assertEqual(self.fake.merged, 1)

    def test_other_worktree_blocks_branch_cleanup(self) -> None:
        self.approve()
        other = self.base / "other-worktree"
        git(self.repo, "worktree", "add", "--force", str(other), "feature/example")
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("another worktree", output)
        self.assertEqual(self.fake.merged, 1)
        self.assertNotEqual(self.remote_feature(), "")
        self.assertNotEqual(git(self.repo, "branch", "--list", "feature/example"), "")

    def test_changed_candidate_blocks_push(self) -> None:
        self.approve()
        (self.repo / "feature.txt").write_text("changed\n", encoding="utf-8")
        git(self.repo, "add", "feature.txt")
        git(self.repo, "commit", "-m", "Change approved content")
        result, output = self.call()
        self.assertEqual(result, 2)
        self.assertIn("feature branch differs", output)
        self.assertEqual(self.remote_feature(), "")


if __name__ == "__main__":
    unittest.main()
