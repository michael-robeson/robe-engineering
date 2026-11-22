from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .approval import read_json
from .config import LifecycleError, load_config
from .evidence import (
    feature_storage_dir,
    run_command,
    sha256_bytes,
    sha256_json,
    write_json,
)
from .gitops import (
    GitError,
    candidate_tree,
    current_branch,
    dirty_porcelain,
    ensure_clean,
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
    if dirty_porcelain(root):
        raise LifecycleError("Refusing to start with a dirty worktree")
    run_git(root, ["fetch", "--prune", "origin"], check=True)
    run_git(root, ["switch", config.base], check=True)
    run_git(
        root,
        ["merge", "--ff-only", f"origin/{config.base}"],
        check=True,
    )
    branch = branch_name(args.feature, config.feature_prefix)
    existing = run_git(
        root,
        ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        check=False,
    )
    if existing.returncode == 0:
        raise LifecycleError(f"Feature branch already exists: {branch}")
    run_git(root, ["switch", "-c", branch], check=True)
    print(json_text({"repository": str(root), "branch": branch, "base": config.base}))
    return 0


def cmd_commit(args: argparse.Namespace) -> int:
    root = repository_root(Path(args.repo))
    config = load_config(root)
    branch = current_branch(root)
    if not branch.startswith(config.feature_prefix):
        raise LifecycleError(
            f"Commit only from a {config.feature_prefix} feature branch"
        )
    if not args.paths:
        raise LifecycleError("At least one --path is required")

    run_git(root, ["add", "--", *args.paths], check=True)
    staged = run_git(root, ["diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0:
        raise LifecycleError("No staged changes to commit")

    gate_results = []
    for argv in config.gate_commands("commit_gate"):
        result = run_command(root, argv)
        gate_results.append(result)
        if result["exit_code"] != 0:
            raise LifecycleError(f"Commit gate failed: {' '.join(argv)}")

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
        text = "\n".join(args.criteria)
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
    if review["schema"] != 1:
        raise LifecycleError("Unsupported review record schema")


def cmd_review(args: argparse.Namespace) -> int:
    root = repository_root(Path(args.repo))
    config = load_config(root)
    branch = current_branch(root)
    if not branch.startswith(config.feature_prefix):
        raise LifecycleError(
            f"Review only from a {config.feature_prefix} feature branch"
        )
    ensure_clean(root)
    candidate = head_commit(root)
    tree = candidate_tree(root)
    criteria, criteria_hash = read_criteria(args)
    policy_hash = sha256_bytes(config.policy_bytes())

    results = []
    for argv in config.gate_commands("readiness_gate"):
        results.append(run_command(root, argv))
    failed = [result for result in results if result["exit_code"] != 0]

    evidence = {
        "schema": 1,
        "repository": str(root),
        "branch": branch,
        "candidate_commit": candidate,
        "candidate_tree": tree,
        "acceptance_criteria_sha256": criteria_hash,
        "acceptance_criteria": criteria,
        "quality_policy_sha256": policy_hash,
        "commands": results,
        "passed": not failed,
        "failed_count": len(failed),
    }
    evidence_hash = write_json(storage(root, branch) / "evidence.json", evidence)
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
    review_hash = write_json(storage(root, branch) / "review.json", review)
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
        "acceptance_criteria_sha256",
        "quality_policy_sha256",
        "review_packet_sha256",
        "evidence_sha256",
    )
    missing = [key for key in required if key not in record]
    if missing:
        raise LifecycleError(
            "Invalid approval record; missing fields: " + ", ".join(missing)
        )
    if record["schema"] != 1:
        raise LifecycleError("Unsupported approval record schema")
    if record["approved"] is not True:
        raise LifecycleError("Approval record is not approved")
    if record["message"] != "APPROVED":
        raise LifecycleError("Approval record message is not APPROVED")
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
    )
    if any(not isinstance(record[field], str) for field in string_fields):
        raise LifecycleError("Invalid approval record; string fields are malformed")
    hash_fields = (
        "candidate_commit",
        "candidate_tree",
        "acceptance_criteria_sha256",
        "quality_policy_sha256",
        "review_packet_sha256",
        "evidence_sha256",
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
    branch = current_branch(root)
    if not branch.startswith(config.feature_prefix):
        raise LifecycleError("Approval only applies to a feature branch")
    ensure_clean(root)
    candidate = head_commit(root)
    tree = candidate_tree(root)
    _, criteria_hash = read_criteria(args)
    policy_hash = sha256_bytes(config.policy_bytes())
    directory = storage(root, branch)
    review = read_json(directory / "review.json")
    evidence = read_json(directory / "evidence.json")
    validate_review(review)
    if review["candidate_commit"] != candidate:
        raise LifecycleError(
            "The reviewed candidate commit changed; approval is not valid"
        )
    if review["candidate_tree"] != tree:
        raise LifecycleError(
            "The reviewed candidate content changed; approval is not valid"
        )
    if review["acceptance_criteria_sha256"] != criteria_hash:
        raise LifecycleError(
            "Acceptance criteria changed after review; approval is not valid"
        )
    if review["quality_policy_sha256"] != policy_hash:
        raise LifecycleError(
            "Quality policy changed after review; approval is not valid"
        )
    if evidence.get("passed") is not True:
        raise LifecycleError("Readiness evidence did not pass")
    if evidence.get("candidate_commit") != candidate:
        raise LifecycleError("Readiness evidence does not belong to the candidate")

    review_bytes = (directory / "review.json").read_bytes()
    evidence_bytes = (directory / "evidence.json").read_bytes()
    record = {
        "schema": 1,
        "approved": True,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "message": "APPROVED",
        "repository": str(root),
        "branch": branch,
        "base": config.base,
        "candidate_commit": candidate,
        "candidate_tree": tree,
        "acceptance_criteria_sha256": criteria_hash,
        "quality_policy_sha256": policy_hash,
        "review_packet_sha256": sha256_bytes(review_bytes),
        "evidence_sha256": sha256_bytes(evidence_bytes),
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
    branch = current_branch(root)
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
    if record["branch"] != branch:
        reasons.append("approval belongs to a different branch")
    if record["candidate_commit"] != candidate:
        reasons.append("candidate commit changed")
    if record["candidate_tree"] != tree:
        reasons.append("candidate content changed")
    if dirty:
        reasons.append("worktree is dirty")
    if sha256_bytes(config.policy_bytes()) != record["quality_policy_sha256"]:
        reasons.append("quality policy changed")
    if args.criteria_file:
        criteria_path = Path(args.criteria_file).resolve()
        if not criteria_path.is_file():
            reasons.append("acceptance criteria file is missing")
        else:
            criteria_hash = sha256_bytes(criteria_path.read_bytes())
            if criteria_hash != record["acceptance_criteria_sha256"]:
                reasons.append("acceptance criteria changed")

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eng-lifecycle")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("--repo", default=".")
    start.add_argument("--feature", required=True)
    start.set_defaults(handler=cmd_start)

    commit = sub.add_parser("commit")
    commit.add_argument("--repo", default=".")
    commit.add_argument("--message", required=True)
    commit.add_argument("--path", dest="paths", action="append", default=[])
    commit.set_defaults(handler=cmd_commit)

    review = sub.add_parser("review")
    review.add_argument("--repo", default=".")
    review.add_argument("--feature", required=True)
    criteria = review.add_mutually_exclusive_group(required=True)
    criteria.add_argument("--criteria")
    criteria.add_argument("--criteria-file")
    review.set_defaults(handler=cmd_review)

    approve = sub.add_parser("approve")
    approve.add_argument("--repo", default=".")
    approve.add_argument("--feature", required=True)
    approve.add_argument("--message", required=True)
    approve.add_argument("--criteria-file", required=True)
    approve.set_defaults(handler=cmd_approve)

    status = sub.add_parser("status")
    status.add_argument("--repo", default=".")
    status.add_argument("--feature", required=True)
    status.add_argument("--criteria-file")
    status.set_defaults(handler=cmd_status)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (LifecycleError, GitError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
