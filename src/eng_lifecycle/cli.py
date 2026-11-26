from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .approval import read_json
from .config import LifecycleConfig, LifecycleError, load_config
from .evidence import (
    feature_storage_dir,
    run_command,
    sha256_bytes,
    write_json,
)
from .gitops import (
    GitError,
    candidate_tree,
    current_branch,
    dirty_porcelain,
    ensure_clean,
    ensure_no_git_operation,
    git_dir,
    head_commit,
    repository_root,
    run_git,
)


def branch_name(feature: str, prefix: str) -> str:
    if feature.startswith(prefix):
        feature = feature[len(prefix):]
    slug = feature.strip().strip("/")
    if not slug or slug in (".", ".."):
        raise LifecycleError("Feature name must be a non-empty path-safe name")
    parts = slug.split("/")
    if any(
        not part
        or part in (".", "..")
        or any(ch.isspace() for ch in part)
        for part in parts
    ):
        raise LifecycleError("Feature name must be a non-empty path-safe name")
    if not all(ch.isalnum() or ch in ("-", "_", "/") for ch in slug):
        raise LifecycleError(
            "Feature name may contain only letters, digits, hyphens, "
            "underscores, and slashes"
        )
    return prefix + slug


def storage(root: Path, feature: str) -> Path:
    config = load_config(root)
    branch = branch_name(feature, config.feature_prefix)
    return feature_storage_dir(git_dir(root), branch)


def json_text(value: object) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)


def cmd_start(args: argparse.Namespace) -> int:
    root = repository_root(Path(args.repo))
    config = load_config(root)
    ensure_no_git_operation(root)
    ensure_clean(root)
    branch = current_branch(root)
    generated_pattern = re.escape(config.feature_prefix) + r"next-[0-9a-f]{32}"
    if re.fullmatch(generated_pattern, branch):
        remote = run_git(
            root, ["ls-remote", "--heads", "origin", f"refs/heads/{branch}"]
        )
        if remote.stdout.strip():
            raise LifecycleError("Generated working branch is not local-only")
        print(json_text({"repository": str(root), "branch": branch, "base": config.base}))
        return 0
    if branch != config.base:
        raise LifecycleError(
            f"Start requires checkout of {config.base} or a generated disposable feature branch"
        )
    run_git(root, ["fetch", "origin", config.base])
    remote = "FETCH_HEAD"
    result = run_git(root, ["merge-base", "--is-ancestor", "HEAD", remote], check=False)
    if result.returncode != 0:
        raise LifecycleError("Local base is ahead of or divergent from origin")
    run_git(root, ["merge", "--ff-only", remote])
    for _ in range(10):
        branch = f"{config.feature_prefix}next-{uuid.uuid4().hex}"
        run_git(root, ["check-ref-format", "--branch", branch])
        existing = run_git(
            root,
            ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            check=False,
        )
        if existing.returncode == 0:
            continue
        if existing.returncode != 1:
            raise LifecycleError("Unable to inspect generated working branch")
        remote = run_git(
            root, ["ls-remote", "--heads", "origin", f"refs/heads/{branch}"]
        )
        if remote.stdout.strip():
            continue
        run_git(root, ["switch", "-c", branch])
        print(json_text({"repository": str(root), "branch": branch, "base": config.base}))
        return 0
    raise LifecycleError("Unable to allocate a unique working branch")


def cmd_continue(args: argparse.Namespace) -> int:
    root = repository_root(Path(args.repo))
    config = load_config(root)
    ensure_no_git_operation(root)
    branch = current_branch(root)
    feature = branch_name(args.feature, config.feature_prefix)
    if branch != feature:
        raise LifecycleError("Feature identifier does not match the current branch")
    if not branch.startswith(config.feature_prefix):
        raise LifecycleError(
            f"Continue requires a {config.feature_prefix} feature branch"
        )
    changes = dirty_porcelain(root).splitlines()
    print(
        json_text(
            {
                "repository": str(root),
                "branch": branch,
                "base": config.base,
                "worktree_clean": not changes,
                "changes": changes,
                "ownership_verified": False,
            }
        )
    )
    return 0


def cmd_commit(args: argparse.Namespace) -> int:
    root = repository_root(Path(args.repo))
    config = load_config(root)
    ensure_no_git_operation(root)
    branch = current_branch(root)
    if not branch.startswith(config.feature_prefix):
        raise LifecycleError(
            f"Commit only from a {config.feature_prefix} feature branch"
        )
    if not args.paths:
        raise LifecycleError("At least one --path is required")
    checks = config.gate_commands("commit_gate")
    for check in checks:
        if check.authorization and check.authorization not in args.authorize:
            raise LifecycleError(f"Commit check requires authorization: {check.authorization}")

    existing = run_git(root, ["diff", "--cached", "--quiet"], check=False)
    if existing.returncode != 0:
        raise LifecycleError("Refusing scoped commit with existing staged changes")
    run_git(root, ["add", "--", *args.paths], check=True)
    staged = run_git(root, ["diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0:
        raise LifecycleError("No staged changes to commit")
    if staged.returncode != 1:
        raise LifecycleError("Unable to inspect staged changes")

    gate_results = []
    staged_tree = run_git(root, ["write-tree"]).stdout.strip()
    for check in checks:
        result = run_command(root, check.argv)
        gate_results.append(result)
        if result["exit_code"] != 0:
            raise LifecycleError(f"Commit gate failed: {' '.join(check.argv)}")
    if run_git(root, ["write-tree"]).stdout.strip() != staged_tree:
        raise LifecycleError("Commit gate changed the staged snapshot")

    run_git(
        root,
        [
            "commit",
            "-m",
            args.message,
            "-m",
            "Co-authored-by: Copilot "
            "<223556219+Copilot@users.noreply.github.com>",
        ],
        check=True,
        capture_output=True,
    )
    candidate = head_commit(root)
    record = {
        "schema": 1,
        "branch": branch,
        "candidate_commit": candidate,
        "candidate_tree": candidate_tree(root),
        "quality_policy_sha256": sha256_bytes(config.policy_bytes()),
        "commit_gate": gate_results,
    }
    record_hash = write_json(storage(root, branch) / "commit.json", record)
    print(
        json_text(
            {
                "candidate_commit": candidate,
                "candidate_tree": record["candidate_tree"],
                "branch": branch,
                "metadata_sha256": record_hash,
            }
        )
    )
    return 0


def read_criteria(args: argparse.Namespace) -> tuple[list[str], str]:
    if getattr(args, "criteria_file", None):
        path = Path(args.criteria_file).resolve()
        if not path.is_file():
            raise LifecycleError(
                f"Acceptance criteria file does not exist: {path}"
            )
        text = path.read_text(encoding="utf-8")
    elif getattr(args, "criteria", None):
        text = args.criteria
    else:
        raise LifecycleError(
            "Acceptance criteria are required via --criteria or --criteria-file"
        )
    criteria = [line for line in text.splitlines() if line.strip()]
    if not criteria:
        raise LifecycleError("Acceptance criteria may not be empty")
    return criteria, sha256_bytes(text.encode("utf-8"))


def validate_review(review: dict[str, object]) -> None:
    required = (
        "schema",
        "branch",
        "base",
        "candidate_commit",
        "candidate_tree",
        "acceptance_criteria",
        "acceptance_criteria_sha256",
        "quality_policy_sha256",
        "ready",
        "evidence_sha256",
    )
    missing = [key for key in required if key not in review]
    if missing:
        raise LifecycleError(
            "Invalid review record; missing fields: " + ", ".join(missing)
        )
    if type(review["schema"]) is not int or review["schema"] != 1 or review["ready"] is not True:
        raise LifecycleError("Review is incomplete or unsuccessful")


def feature_branch(root: Path, prefix: str, feature: str) -> str:
    branch = current_branch(root)
    if branch != branch_name(feature, prefix):
        raise LifecycleError("Feature identifier does not match the current branch")
    return branch


def validate_evidence(
    config: LifecycleConfig, directory: Path, expected: dict[str, object]
) -> dict[str, object]:
    # The local record is a consistency safeguard, not an authenticated signature.
    review = read_json(directory / "review.json")
    evidence = read_json(directory / "evidence.json")
    validate_review(review)
    if review.get("evidence_sha256") != sha256_bytes(
        (directory / "evidence.json").read_bytes()
    ):
        raise LifecycleError("Review and evidence hashes do not match")
    if (
        review.get("quality_policy_sha256") != expected.get("quality_policy_sha256")
        or evidence.get("quality_policy_sha256") != expected.get("quality_policy_sha256")
    ):
        raise LifecycleError("Review or evidence quality policy changed")
    for key, value in expected.items():
        if review.get(key) != value or evidence.get(key) != value:
            raise LifecycleError(f"Review or evidence does not match current {key}")
    if review.get("acceptance_criteria") != evidence.get("acceptance_criteria"):
        raise LifecycleError("Review and evidence criteria do not match")
    if type(evidence.get("schema")) is not int or evidence.get("schema") != 1 or evidence.get("passed") is not True:
        raise LifecycleError("Readiness evidence is incomplete or unsuccessful")
    if type(evidence.get("failed_count")) is not int or evidence.get("failed_count") != 0:
        raise LifecycleError("Readiness evidence reports failed checks")
    checks = config.gate_commands("readiness_gate")
    results = evidence.get("commands")
    if not isinstance(results, list) or len(results) != len(checks):
        raise LifecycleError("Readiness evidence is missing required checks")
    for check, result in zip(checks, results):
        if (
            not isinstance(result, dict)
            or result.get("argv") != check.argv
            or result.get("exit_code") != 0
            or type(result.get("exit_code")) is not int
            or result.get("authorization") != check.authorization
            or (check.authorization and result.get("authorized") is not True)
            or not all(isinstance(result.get(field), str) for field in ("stdout", "stderr", "started_at", "ended_at"))
            or type(result.get("duration_seconds")) not in (int, float)
            or result["duration_seconds"] < 0
        ):
            raise LifecycleError("Readiness evidence contains a failed or skipped check")
    return review


def validate_architecture_review(
    directory: Path, expected: dict[str, object]
) -> dict[str, object]:
    path = directory / "architecture-review.json"
    record = read_json(path)
    required = (
        "schema",
        "repository",
        "branch",
        "base",
        "candidate_commit",
        "candidate_tree",
        "acceptance_criteria",
        "acceptance_criteria_sha256",
        "quality_policy_sha256",
        "decision",
        "reviewer",
        "reviewed_at",
        "evidence",
        "evidence_sha256",
    )
    missing = [key for key in required if key not in record]
    if missing:
        raise LifecycleError(
            "Invalid architectural review; missing fields: " + ", ".join(missing)
        )
    if type(record["schema"]) is not int or record["schema"] != 1:
        raise LifecycleError("Unsupported architectural review schema")
    if record["decision"] != "accepted":
        raise LifecycleError("Architectural review has not accepted this candidate")
    if not isinstance(record["reviewer"], str) or not record["reviewer"].strip():
        raise LifecycleError("Architectural review reviewer is malformed")
    if not isinstance(record["evidence"], str) or not record["evidence"].strip():
        raise LifecycleError("Architectural review evidence is empty")
    if record["evidence_sha256"] != sha256_bytes(
        record["evidence"].encode("utf-8")
    ):
        raise LifecycleError("Architectural review evidence hash does not match")
    reviewed_at = record["reviewed_at"]
    if not isinstance(reviewed_at, str):
        raise LifecycleError("Architectural review time is malformed")
    try:
        timestamp = datetime.fromisoformat(reviewed_at)
        if timestamp.tzinfo is None:
            raise ValueError("timezone missing")
    except ValueError as error:
        raise LifecycleError("Architectural review time is malformed") from error
    for key, value in expected.items():
        if record.get(key) != value:
            raise LifecycleError(
                f"Architectural review does not match current {key}"
            )
    return record


def cmd_review(args: argparse.Namespace) -> int:
    root = repository_root(Path(args.repo))
    config = load_config(root)
    branch = feature_branch(root, config.feature_prefix, args.feature)
    ensure_no_git_operation(root)
    ensure_clean(root)
    candidate = head_commit(root)
    tree = candidate_tree(root)
    criteria, criteria_hash = read_criteria(args)
    policy_hash = sha256_bytes(config.policy_bytes())

    directory = storage(root, branch)
    write_json(directory / "review.json", {"schema": 1, "ready": False})
    results = []
    for check in config.gate_commands("readiness_gate"):
        if check.authorization and check.authorization not in args.authorize:
            result = {
                "argv": check.argv,
                "exit_code": None,
                "authorization": check.authorization,
                "authorized": False,
                "error": "Special authorization required",
            }
        else:
            result = run_command(root, check.argv)
            result["authorization"] = check.authorization
            result["authorized"] = True
        results.append(result)
    failed = [result for result in results if result["exit_code"] != 0]
    ensure_no_git_operation(root)
    ensure_clean(root)
    if (
        current_branch(root) != branch
        or head_commit(root) != candidate
        or candidate_tree(root) != tree
        or sha256_bytes(load_config(root).policy_bytes()) != policy_hash
        or read_criteria(args)[1] != criteria_hash
    ):
        raise LifecycleError("Candidate, criteria, or policy changed during readiness checks")

    evidence = {
        "schema": 1,
        "repository": str(root),
        "branch": branch,
        "base": config.base,
        "candidate_commit": candidate,
        "candidate_tree": tree,
        "acceptance_criteria_sha256": criteria_hash,
        "acceptance_criteria": criteria,
        "quality_policy_sha256": policy_hash,
        "commands": results,
        "passed": not failed,
        "failed_count": len(failed),
    }
    evidence_hash = write_json(directory / "evidence.json", evidence)
    review = {
        "schema": 1,
        "repository": str(root),
        "branch": branch,
        "base": config.base,
        "candidate_commit": candidate,
        "candidate_tree": tree,
        "acceptance_criteria_sha256": criteria_hash,
        "acceptance_criteria": criteria,
        "quality_policy_sha256": policy_hash,
        "ready": not failed,
        "evidence_sha256": evidence_hash,
    }
    review_hash = write_json(directory / "review.json", review)
    print(
        json_text(
            {
                "candidate_commit": candidate,
                "candidate_tree": tree,
                "acceptance_criteria_count": len(criteria),
                "ready": not failed,
                "failed_count": len(failed),
                "quality_policy_sha256": policy_hash,
                "acceptance_criteria_sha256": criteria_hash,
                "review_packet_sha256": review_hash,
                "evidence_sha256": evidence_hash,
            }
        )
    )
    return 0 if not failed else 1


def cmd_architecture_review(args: argparse.Namespace) -> int:
    root = repository_root(Path(args.repo))
    config = load_config(root)
    branch = feature_branch(root, config.feature_prefix, args.feature)
    ensure_no_git_operation(root)
    ensure_clean(root)
    candidate = head_commit(root)
    tree = candidate_tree(root)
    criteria, criteria_hash = read_criteria(args)
    policy_hash = sha256_bytes(config.policy_bytes())
    directory = storage(root, branch)
    expected: dict[str, object] = {
        "repository": str(root),
        "branch": branch,
        "base": config.base,
        "candidate_commit": candidate,
        "candidate_tree": tree,
        "acceptance_criteria_sha256": criteria_hash,
        "acceptance_criteria": criteria,
        "quality_policy_sha256": policy_hash,
    }
    validate_evidence(config, directory, expected)
    reviewer = args.reviewer.strip()
    evidence = args.evidence.strip()
    if not reviewer:
        raise LifecycleError("Architectural review reviewer may not be empty")
    if not evidence:
        raise LifecycleError("Architectural review evidence may not be empty")
    record = {
        **expected,
        "schema": 1,
        "decision": args.decision,
        "reviewer": reviewer,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "evidence": evidence,
        "evidence_sha256": sha256_bytes(evidence.encode("utf-8")),
    }
    review_hash = write_json(directory / "architecture-review.json", record)
    print(
        json_text(
            {
                "candidate_commit": candidate,
                "candidate_tree": tree,
                "decision": args.decision,
                "architectural_review_sha256": review_hash,
            }
        )
    )
    return 0


def validate_approval_record(record: dict[str, object]) -> None:
    required = (
        "schema",
        "approved",
        "approved_at",
        "message",
        "repository",
        "branch",
        "base",
        "candidate_commit",
        "candidate_tree",
        "acceptance_criteria",
        "acceptance_criteria_sha256",
        "quality_policy_sha256",
        "review_packet_sha256",
        "evidence_sha256",
        "architectural_review_sha256",
    )
    missing = [key for key in required if key not in record]
    if missing:
        raise LifecycleError(
            "Invalid approval record; missing fields: " + ", ".join(missing)
        )
    if type(record["schema"]) is not int or record["schema"] != 2:
        raise LifecycleError("Unsupported approval record schema")
    if record["approved"] is not True:
        raise LifecycleError("Approval record is not approved")
    if record["message"] != "APPROVED":
        raise LifecycleError("Approval record message is not APPROVED")
    criteria = record["acceptance_criteria"]
    if not isinstance(criteria, list) or not criteria or not all(
        isinstance(item, str) and item.strip() for item in criteria
    ):
        raise LifecycleError("Invalid approval record; acceptance criteria are malformed")
    string_fields = (
        "approved_at",
        "repository",
        "branch",
        "base",
        "candidate_commit",
        "candidate_tree",
        "acceptance_criteria_sha256",
        "quality_policy_sha256",
        "review_packet_sha256",
        "evidence_sha256",
        "architectural_review_sha256",
    )
    if any(not isinstance(record[field], str) for field in string_fields):
        raise LifecycleError("Invalid approval record; string fields are malformed")
    timestamp = record["approved_at"]
    if not isinstance(timestamp, str):
        raise LifecycleError("Invalid approval record; malformed approval time")
    try:
        approved_at = datetime.fromisoformat(timestamp)
        if approved_at.tzinfo is None:
            raise ValueError("timezone missing")
    except ValueError as error:
        raise LifecycleError("Invalid approval record; malformed approval time") from error
    hash_fields = (
        "candidate_commit",
        "candidate_tree",
        "acceptance_criteria_sha256",
        "quality_policy_sha256",
        "review_packet_sha256",
        "evidence_sha256",
        "architectural_review_sha256",
    )
    import re

    for field in hash_fields:
        value = record[field]
        if field in ("candidate_commit", "candidate_tree"):
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", str(value)):
            raise LifecycleError(
                f"Invalid approval record; malformed {field}"
            )


def cmd_approve(args: argparse.Namespace) -> int:
    root = repository_root(Path(args.repo))
    config = load_config(root)
    if args.message != "APPROVED":
        raise LifecycleError("Approval message must be exactly APPROVED")
    branch = feature_branch(root, config.feature_prefix, args.feature)
    ensure_no_git_operation(root)
    candidate = head_commit(root)
    tree = candidate_tree(root)
    criteria, criteria_hash = read_criteria(args)
    policy_hash = sha256_bytes(config.policy_bytes())
    directory = storage(root, branch)
    expected: dict[str, object] = {
        "repository": str(root),
        "branch": branch,
        "base": config.base,
        "candidate_commit": candidate,
        "candidate_tree": tree,
        "acceptance_criteria": criteria,
        "acceptance_criteria_sha256": criteria_hash,
        "quality_policy_sha256": policy_hash,
    }
    validate_evidence(config, directory, expected)
    validate_architecture_review(directory, expected)
    ensure_clean(root)

    review_bytes = (directory / "review.json").read_bytes()
    evidence_bytes = (directory / "evidence.json").read_bytes()
    architecture_review_bytes = (
        directory / "architecture-review.json"
    ).read_bytes()
    record = {
        "schema": 2,
        "approved": True,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "message": "APPROVED",
        "repository": str(root),
        "branch": branch,
        "base": config.base,
        "candidate_commit": candidate,
        "candidate_tree": tree,
        "acceptance_criteria": criteria,
        "acceptance_criteria_sha256": criteria_hash,
        "quality_policy_sha256": policy_hash,
        "review_packet_sha256": sha256_bytes(review_bytes),
        "evidence_sha256": sha256_bytes(evidence_bytes),
        "architectural_review_sha256": sha256_bytes(
            architecture_review_bytes
        ),
    }
    approval_hash = write_json(directory / "approval.json", record)
    print(
        json_text(
            {
                "approved": True,
                "candidate_commit": candidate,
                "candidate_tree": tree,
                "approval_record_sha256": approval_hash,
            }
        )
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = repository_root(Path(args.repo))
    config = load_config(root)
    branch = feature_branch(root, config.feature_prefix, args.feature)
    directory = storage(root, branch)
    approval_path = directory / "approval.json"
    if not approval_path.is_file():
        print(
            json_text(
                {"approved": False, "valid": False, "reason": "no approval record"}
            )
        )
        return 1
    try:
        record = read_json(approval_path)
        validate_approval_record(record)
    except LifecycleError as error:
        print(json_text({"approved": False, "valid": False, "reason": str(error)}))
        return 1

    reasons = []
    candidate = head_commit(root)
    tree = candidate_tree(root)
    dirty = dirty_porcelain(root)
    try:
        ensure_no_git_operation(root)
        criteria, criteria_hash = read_criteria(args)
        expected: dict[str, object] = {
            "repository": str(root),
            "branch": branch,
            "base": config.base,
            "candidate_commit": candidate,
            "candidate_tree": tree,
            "acceptance_criteria": criteria,
            "acceptance_criteria_sha256": criteria_hash,
            "quality_policy_sha256": sha256_bytes(config.policy_bytes()),
        }
        if record.get("quality_policy_sha256") != expected["quality_policy_sha256"]:
            raise LifecycleError("Approval quality policy changed")
        for key, value in expected.items():
            if record.get(key) != value:
                raise LifecycleError(f"Approval does not match current {key}")
        if dirty:
            raise LifecycleError("worktree is dirty")
        validate_evidence(config, directory, {**expected, "acceptance_criteria": criteria})
        validate_architecture_review(
            directory, {**expected, "acceptance_criteria": criteria}
        )
        architecture_review_hash = sha256_bytes(
            (directory / "architecture-review.json").read_bytes()
        )
        if record.get("architectural_review_sha256") != architecture_review_hash:
            raise LifecycleError(
                "Approval does not match current architectural review"
            )
    except (LifecycleError, GitError, OSError, UnicodeError) as error:
        reasons.append(str(error))

    result = {
        "approved": not reasons,
        "valid": not reasons,
        "branch": branch,
        "candidate_commit": candidate,
        "candidate_tree": tree,
        "approval_record": str(approval_path),
        "reasons": reasons,
    }
    print(json_text(result))
    return 0 if not reasons else 1


def cmd_integrate(args: argparse.Namespace) -> int:
    from .integration import integrate

    return integrate(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eng-lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("--repo", default=".")
    start.set_defaults(handler=cmd_start)

    commit = sub.add_parser("commit")
    commit.add_argument("--repo", default=".")
    commit.add_argument("--message", required=True)
    commit.add_argument("--path", dest="paths", action="append", default=[])
    commit.add_argument("--authorize", action="append", default=[])
    commit.set_defaults(handler=cmd_commit)

    review = sub.add_parser("review")
    review.add_argument("--repo", default=".")
    review.add_argument("--feature", required=True)
    criteria = review.add_mutually_exclusive_group(required=True)
    criteria.add_argument("--criteria")
    criteria.add_argument("--criteria-file")
    review.add_argument("--authorize", action="append", default=[])
    review.set_defaults(handler=cmd_review)

    approve = sub.add_parser("approve")
    approve.add_argument("--repo", default=".")
    approve.add_argument("--feature", required=True)
    approve.add_argument("--message", required=True)
    criteria = approve.add_mutually_exclusive_group(required=True)
    criteria.add_argument("--criteria")
    criteria.add_argument("--criteria-file")
    approve.set_defaults(handler=cmd_approve)

    status = sub.add_parser("status")
    status.add_argument("--repo", default=".")
    status.add_argument("--feature", required=True)
    criteria = status.add_mutually_exclusive_group(required=True)
    criteria.add_argument("--criteria")
    criteria.add_argument("--criteria-file")
    status.set_defaults(handler=cmd_status)

    continue_feature = sub.add_parser("continue")
    continue_feature.add_argument("--repo", default=".")
    continue_feature.add_argument("--feature", required=True)
    continue_feature.set_defaults(handler=cmd_continue)

    architecture_review = sub.add_parser("architecture-review")
    architecture_review.add_argument("--repo", default=".")
    architecture_review.add_argument("--feature", required=True)
    criteria = architecture_review.add_mutually_exclusive_group(required=True)
    criteria.add_argument("--criteria")
    criteria.add_argument("--criteria-file")
    architecture_review.add_argument(
        "--decision", choices=("accepted", "changes-requested"), required=True
    )
    architecture_review.add_argument("--reviewer", required=True)
    architecture_review.add_argument("--evidence", required=True)
    architecture_review.set_defaults(handler=cmd_architecture_review)

    for name in ("integrate", "resume"):
        command = sub.add_parser(name)
        command.add_argument("--repo", default=".")
        command.add_argument("--feature", required=True)
        criteria = command.add_mutually_exclusive_group(required=True)
        criteria.add_argument("--criteria")
        criteria.add_argument("--criteria-file")
        command.add_argument("--authorize", action="append", default=[])
        command.set_defaults(handler=cmd_integrate)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (LifecycleError, GitError, OSError, UnicodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
