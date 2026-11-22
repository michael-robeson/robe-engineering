from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit

from .approval import read_json
from .cli import (
    branch_name,
    json_text,
    read_criteria,
    storage,
    validate_approval_record,
    validate_evidence,
)
from .config import LifecycleConfig, LifecycleError, load_config
from .evidence import feature_storage_dir, run_command, sha256_bytes, write_json
from .gitops import (
    current_branch,
    ensure_clean,
    ensure_no_git_operation,
    head_commit,
    repository_root,
    run_git as shared_run_git,
)

PR_FIELDS = (
    "number,state,baseRefName,baseRefOid,headRefName,headRefOid,"
    "isCrossRepository,isDraft,mergeable,mergeStateStatus,mergeCommit,"
    "reviewDecision,statusCheckRollup,url,author"
)


def run_git(
    root: Path, args: list[str], *, check: bool = True, capture_output: bool = True
) -> subprocess.CompletedProcess[str]:
    return shared_run_git(
        root, args, check=check, capture_output=capture_output, non_interactive=True
    )


def gh(root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["gh", *args], cwd=root, capture_output=True, text=True, check=False,
            stdin=subprocess.DEVNULL, timeout=60,
        )
    except subprocess.TimeoutExpired as error:
        raise LifecycleError(f"GitHub command timed out: {' '.join(args[:2])}") from error
    if result.returncode:
        raise LifecycleError(
            f"GitHub command failed: {(result.stderr or result.stdout).strip()}"
        )
    return result.stdout


def gh_json(root: Path, args: list[str]) -> object:
    try:
        result = json.loads(gh(root, args))
    except json.JSONDecodeError as error:
        raise LifecycleError("GitHub returned invalid JSON") from error
    if isinstance(result, dict) and "errors" in result:
        errors = result["errors"]
        if not isinstance(errors, list) or errors:
            raise LifecycleError("GitHub returned errors; state cannot be verified")
    return result


def origin_repository(root: Path) -> tuple[str, str, str]:
    url = run_git(root, ["remote", "get-url", "origin"]).stdout.strip()
    if url.startswith("git@"):
        match = re.fullmatch(r"git@([^:]+):([^/]+)/([^/]+?)(?:\.git)?", url)
        if not match:
            raise LifecycleError("Unsupported origin URL")
        host, owner, name = match.groups()
    else:
        try:
            parsed = urlsplit(url)
        except ValueError as error:
            raise LifecycleError("Invalid origin URL") from error
        if parsed.scheme not in ("https", "ssh") or not parsed.hostname:
            raise LifecycleError("Origin must be a GitHub HTTPS or SSH URL")
        host = parsed.hostname
        parts = parsed.path.strip("/").removesuffix(".git").split("/")
        if len(parts) != 2:
            raise LifecycleError("Origin must identify one GitHub repository")
        owner, name = parts
    if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in (host, owner, name)):
        raise LifecycleError("Invalid origin repository identity")
    return host, owner, name


def policy(config: LifecycleConfig) -> tuple[list[str], bool]:
    required = config.raw.get("required_ci")
    review = config.raw.get("required_review")
    if (
        not isinstance(required, list)
        or not required
        or not all(isinstance(item, str) and item.strip() == item and item for item in required)
        or len(set(required)) != len(required)
    ):
        raise LifecycleError("Integration requires nonempty, unique required_ci names")
    if type(review) is not bool:
        raise LifecycleError("Integration requires an explicit boolean required_review policy")
    if config.merge_strategy != "merge":
        raise LifecycleError("Automatic integration currently supports merge commits only")
    return required, review


def approved_candidate(
    root: Path, config: LifecycleConfig, branch: str, args: argparse.Namespace
) -> tuple[str, str, list[str]]:
    directory = storage(root, branch)
    record = read_json(directory / "approval.json")
    validate_approval_record(record)
    candidate = record["candidate_commit"]
    tree = record["candidate_tree"]
    if not isinstance(candidate, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", candidate):
        raise LifecycleError("Invalid approved candidate commit")
    if not isinstance(tree, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", tree):
        raise LifecycleError("Invalid approved candidate tree")
    criteria, criteria_hash = read_criteria(args)
    expected: dict[str, object] = {
        "repository": str(root),
        "branch": branch,
        "base": config.base,
        "candidate_commit": candidate,
        "candidate_tree": tree,
        "acceptance_criteria_sha256": criteria_hash,
        "quality_policy_sha256": sha256_bytes(config.policy_bytes()),
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise LifecycleError(f"Approval does not match current {key}")
    validate_evidence(config, directory, {**expected, "acceptance_criteria": criteria})
    actual_tree = run_git(root, ["rev-parse", "--verify", f"{candidate}^{{tree}}"]).stdout.strip()
    if actual_tree != tree:
        raise LifecycleError("Approved commit does not match approved tree")
    ref = run_git(root, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], check=False)
    if ref.returncode == 0:
        tip = run_git(root, ["rev-parse", f"refs/heads/{branch}"]).stdout.strip()
        if tip != candidate:
            raise LifecycleError("Local feature branch differs from approved candidate")
    elif ref.returncode != 1:
        raise LifecycleError("Unable to inspect local feature branch")
    ensure_no_git_operation(root)
    ensure_clean(root)
    return candidate, tree, criteria


def find_pr(root: Path, repository: str, branch: str) -> dict[str, object] | None:
    result = gh_json(root, [
        "pr", "list", "--repo", repository, "--state", "all", "--head", branch,
        "--limit", "100", "--json", PR_FIELDS,
    ])
    if not isinstance(result, list) or len(result) >= 100:
        raise LifecycleError("Ambiguous pull request listing")
    if not all(isinstance(item, dict) for item in result):
        raise LifecycleError("Invalid pull request listing")
    if len(result) > 1:
        raise LifecycleError("Multiple pull requests match the feature branch")
    return result[0] if result else None


def pull_request(root: Path, repository: str, number: int) -> dict[str, object]:
    result = gh_json(root, [
        "pr", "view", str(number), "--repo", repository, "--json", PR_FIELDS,
    ])
    if not isinstance(result, dict):
        raise LifecycleError("Invalid pull request response")
    return result


def pr_author(pr: dict[str, object]) -> str:
    author = pr.get("author")
    if not isinstance(author, dict):
        raise LifecycleError("Pull request author cannot be verified")
    login = author.get("login")
    if not isinstance(login, str) or not login.strip():
        raise LifecycleError("Pull request author cannot be verified")
    return login


def validate_pr(
    pr: dict[str, object], branch: str, base: str, candidate: str | None
) -> int:
    number = pr.get("number")
    if type(number) is not int or number < 1:
        raise LifecycleError("Invalid pull request number")
    pr_author(pr)
    for field in ("baseRefOid", "headRefOid"):
        oid = pr.get(field)
        if not isinstance(oid, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid):
            raise LifecycleError(f"Pull request is missing a valid {field}")
    if (
        pr.get("headRefName") != branch
        or pr.get("baseRefName") != base
        or (candidate is not None and pr.get("headRefOid") != candidate)
        or pr.get("isCrossRepository") is not False
    ):
        raise LifecycleError("Pull request does not match the approved branch, base, and commit")
    return number


def validate_review_policy(pr: dict[str, object], required: bool) -> None:
    if pr.get("state") != "OPEN" or pr.get("isDraft") is not False:
        raise LifecycleError("Pull request is not open and ready for review")
    decision = pr.get("reviewDecision")
    if decision not in (None, "", "APPROVED", "REVIEW_REQUIRED", "CHANGES_REQUESTED"):
        raise LifecycleError("Unknown pull request review decision")
    if decision in ("CHANGES_REQUESTED", "REVIEW_REQUIRED") or (required and decision != "APPROVED"):
        raise LifecycleError("Pull request does not meet the review policy")


def unresolved_threads(root: Path, host: str, owner: str, name: str, number: int) -> bool:
    query = (
        "query($owner:String!,$name:String!,$number:Int!,$cursor:String) {"
        " repository(owner:$owner,name:$name) { pullRequest(number:$number) {"
        " reviewThreads(first:100,after:$cursor) {"
        " nodes { isResolved } pageInfo { hasNextPage endCursor } } } } }"
    )
    cursor: str | None = None
    seen: set[str] = set()
    while True:
        args = [
            "api", "graphql", "--hostname", host, "-f", f"query={query}",
            "-f", f"owner={owner}", "-f", f"name={name}", "-F", f"number={number}",
        ]
        if cursor is not None:
            args.extend(["-f", f"cursor={cursor}"])
        response = gh_json(root, args)
        try:
            if not isinstance(response, dict):
                raise TypeError("response is not an object")
            threads = response["data"]["repository"]["pullRequest"]["reviewThreads"]
            nodes = threads["nodes"]
            page = threads["pageInfo"]
            has_next = page["hasNextPage"]
            end_cursor = page["endCursor"]
        except (KeyError, TypeError) as error:
            raise LifecycleError("Unable to determine review thread state") from error
        if not isinstance(nodes, list) or type(has_next) is not bool:
            raise LifecycleError("Invalid review thread state")
        for node in nodes:
            if not isinstance(node, dict) or type(node.get("isResolved")) is not bool:
                raise LifecycleError("Invalid review thread state")
            if not node["isResolved"]:
                return True
        if not has_next:
            return False
        if not isinstance(end_cursor, str) or not end_cursor or end_cursor in seen:
            raise LifecycleError("Invalid review thread pagination")
        seen.add(end_cursor)
        cursor = end_cursor


def validate_review_opinions(
    root: Path, host: str, owner: str, name: str, number: int,
    candidate: str, required: bool, pr_author: str,
) -> None:
    query = (
        "query($owner:String!,$name:String!,$number:Int!,$cursor:String) {"
        " repository(owner:$owner,name:$name) { pullRequest(number:$number) {"
        " latestOpinionatedReviews(first:100,after:$cursor) {"
        " nodes { state commit { oid } author { login } }"
        " pageInfo { hasNextPage endCursor } } } } }"
    )
    cursor: str | None = None
    seen: set[str] = set()
    approved = False
    while True:
        args = [
            "api", "graphql", "--hostname", host, "-f", f"query={query}",
            "-f", f"owner={owner}", "-f", f"name={name}", "-F", f"number={number}",
        ]
        if cursor is not None:
            args.extend(["-f", f"cursor={cursor}"])
        response = gh_json(root, args)
        try:
            if not isinstance(response, dict):
                raise TypeError("response is not an object")
            reviews = response["data"]["repository"]["pullRequest"]["latestOpinionatedReviews"]
            nodes = reviews["nodes"]
            page = reviews["pageInfo"]
            has_next, end_cursor = page["hasNextPage"], page["endCursor"]
        except (KeyError, TypeError) as error:
            raise LifecycleError("Unable to determine pull request reviews") from error
        if not isinstance(nodes, list) or type(has_next) is not bool:
            raise LifecycleError("Invalid pull request review state")
        for node in nodes:
            if not isinstance(node, dict):
                raise LifecycleError("Invalid pull request review")
            state = node.get("state")
            if state == "CHANGES_REQUESTED":
                raise LifecycleError("Pull request has changes requested")
            if state == "APPROVED":
                commit = node.get("commit")
                author = node.get("author")
                if not isinstance(commit, dict) or not isinstance(author, dict):
                    raise LifecycleError("Approval review has no commit or author")
                oid, login = commit.get("oid"), author.get("login")
                if (
                    not isinstance(oid, str)
                    or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid)
                    or not isinstance(login, str)
                    or not login.strip()
                ):
                    raise LifecycleError("Approval review has no commit or author")
                if oid == candidate and login.casefold() != pr_author.casefold():
                    approved = True
            elif state != "DISMISSED":
                raise LifecycleError("Unknown pull request review state")
        if not has_next:
            break
        if not isinstance(end_cursor, str) or not end_cursor or end_cursor in seen:
            raise LifecycleError("Invalid pull request review pagination")
        seen.add(end_cursor)
        cursor = end_cursor
    if required and not approved:
        raise LifecycleError("No independent approving GitHub review is bound to the approved candidate")


def required_checks(pr: dict[str, object], names: list[str]) -> str:
    checks = pr.get("statusCheckRollup")
    if checks is None:
        return "pending"
    if not isinstance(checks, list):
        raise LifecycleError("Invalid CI check response")
    found: dict[str, list[str]] = {name: [] for name in names}
    for check in checks:
        if not isinstance(check, dict):
            raise LifecycleError("Invalid CI check")
        name = check.get("name", check.get("context"))
        if not isinstance(name, str):
            raise LifecycleError("CI check is missing its name")
        if name not in found:
            continue
        if "name" in check:
            status, conclusion = check.get("status"), check.get("conclusion")
            if status != "COMPLETED":
                found[name].append("pending" if status in ("QUEUED", "IN_PROGRESS", "PENDING", "WAITING", "REQUESTED") else "failed")
            else:
                found[name].append("passed" if conclusion == "SUCCESS" else "failed")
        else:
            state = check.get("state")
            found[name].append("passed" if state == "SUCCESS" else "pending" if state in ("PENDING", "EXPECTED") else "failed")
    if any("failed" in states for states in found.values()):
        raise LifecycleError("A required CI check failed or was skipped")
    if any(len(states) > 1 for states in found.values()):
        raise LifecycleError("Ambiguous duplicate required CI check")
    if any(not states or "pending" in states for states in found.values()):
        return "pending"
    return "passed"


def final_checks(
    root: Path, config: LifecycleConfig, branch: str,
    binding: tuple[str, str, list[str], str], args: argparse.Namespace,
) -> None:
    candidate, _, _, _ = binding
    checks = config.gate_commands("readiness_gate") + config.gate_commands("integration_gate")
    for check in checks:
        if check.authorization and check.authorization not in args.authorize:
            raise LifecycleError(f"Integration check requires authorization: {check.authorization}")
    directory = storage(root, branch)
    write_json(directory / "integration-evidence.json", {
        "schema": 1, "candidate_commit": candidate, "passed": False, "commands": [],
    })
    results = []
    for check in checks:
        result = run_command(root, check.argv, non_interactive=True)
        result["authorization"] = check.authorization
        result["authorized"] = True
        results.append(result)
        if result["exit_code"] != 0:
            write_json(directory / "integration-evidence.json", {
                "schema": 1, "candidate_commit": candidate, "passed": False,
                "commands": results,
            })
            raise LifecycleError(f"Integration check failed: {' '.join(check.argv)}")
        ensure_binding(root, branch, args, binding)
        if current_branch(root) != branch or head_commit(root) != candidate:
            raise LifecycleError("Feature branch changed during integration verification")
    write_json(directory / "integration-evidence.json", {
        "schema": 1, "candidate_commit": candidate, "passed": True, "commands": results,
    })


def ensure_binding(
    root: Path, branch: str, args: argparse.Namespace,
    binding: tuple[str, str, list[str], str],
) -> None:
    current_config = load_config(root)
    candidate, tree, criteria = approved_candidate(root, current_config, branch, args)
    current = (candidate, tree, criteria, sha256_bytes(current_config.policy_bytes()))
    if current != binding:
        raise LifecycleError("Approval binding changed during integration")


def ensure_ready(
    root: Path, repository: str, identity: tuple[str, str, str], number: int,
    branch: str, base: str, candidate: str, required: list[str], review_required: bool,
) -> dict[str, object]:
    deadline = time.monotonic() + 600
    while True:
        pr = pull_request(root, repository, number)
        if validate_pr(pr, branch, base, candidate) != number:
            raise LifecycleError("Pull request identity changed during integration")
        validate_review_policy(pr, review_required)
        state = required_checks(pr, required)
        if state == "passed":
            mergeable = pr.get("mergeable")
            merge_state = pr.get("mergeStateStatus")
            if mergeable not in ("UNKNOWN", "MERGEABLE"):
                raise LifecycleError("Pull request mergeability is not clean")
            if merge_state not in ("UNKNOWN", "CLEAN"):
                raise LifecycleError("Pull request mergeability is not clean")
            if mergeable == "MERGEABLE" and merge_state == "CLEAN":
                host, owner, name = identity
                if unresolved_threads(root, host, owner, name, number):
                    raise LifecycleError("Pull request has unresolved review threads")
                validate_review_opinions(
                    root, host, owner, name, number, candidate, review_required, pr_author(pr)
                )
                return pr
        if time.monotonic() >= deadline:
            raise LifecycleError("Timed out waiting for all required CI checks")
        time.sleep(10)


def remote_feature_tip(root: Path, branch: str) -> str | None:
    result = run_git(root, ["ls-remote", "--heads", "origin", f"refs/heads/{branch}"])
    lines = result.stdout.splitlines()
    if not lines:
        return None
    if len(lines) != 1:
        raise LifecycleError("Ambiguous remote feature branch")
    fields = lines[0].split()
    if len(fields) != 2 or fields[1] != f"refs/heads/{branch}":
        raise LifecycleError("Invalid remote feature branch response")
    return fields[0]


def check_base(root: Path, config: LifecycleConfig, candidate: str) -> str:
    run_git(root, ["fetch", "origin", config.base])
    remote = run_git(root, ["rev-parse", "--verify", "FETCH_HEAD^{commit}"]).stdout.strip()
    local = f"refs/heads/{config.base}"
    for ancestor, descendant, error in (
        (local, remote, "Local base is ahead of or divergent from remote"),
        (remote, candidate, "Remote base changed since the approved candidate"),
    ):
        if run_git(root, ["merge-base", "--is-ancestor", ancestor, descendant], check=False).returncode != 0:
            raise LifecycleError(error)
    return remote


def cleanup(
    root: Path, config: LifecycleConfig, branch: str, candidate: str,
    pr: dict[str, object], identity: tuple[str, str, str], args: argparse.Namespace,
    binding: tuple[str, str, list[str], str],
) -> None:
    ensure_binding(root, branch, args, binding)
    merge = pr.get("mergeCommit")
    if pr.get("state") != "MERGED" or not isinstance(merge, dict):
        raise LifecycleError("Pull request merge has not been verified")
    merge_oid = merge.get("oid")
    if not isinstance(merge_oid, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", merge_oid):
        raise LifecycleError("Pull request has no valid merge commit")
    if origin_repository(root) != identity:
        raise LifecycleError("Origin repository changed before cleanup")
    run_git(root, ["fetch", "origin", config.base])
    remote_base = "FETCH_HEAD"
    for commit in (merge_oid, candidate):
        result = run_git(root, ["merge-base", "--is-ancestor", commit, remote_base], check=False)
        if result.returncode != 0:
            raise LifecycleError("Merged pull request is not present in the remote base")
    if run_git(root, ["merge-base", "--is-ancestor", candidate, merge_oid], check=False).returncode != 0:
        raise LifecycleError("Merge commit does not contain the approved candidate")
    local_base = f"refs/heads/{config.base}"
    if run_git(root, ["merge-base", "--is-ancestor", local_base, remote_base], check=False).returncode != 0:
        raise LifecycleError("Local base is ahead of or divergent from remote")
    worktrees = run_git(root, ["worktree", "list", "--porcelain", "-z"]).stdout
    for entry in worktrees.split("\0\0"):
        fields = entry.split("\0")
        if f"branch refs/heads/{branch}" in fields:
            paths = [field[9:] for field in fields if field.startswith("worktree ")]
            if len(paths) != 1 or Path(paths[0]).resolve() != root:
                raise LifecycleError("Feature branch is checked out in another worktree")
    if current_branch(root) == branch:
        run_git(root, ["switch", config.base])
    elif current_branch(root) != config.base:
        raise LifecycleError("Cleanup requires the feature or base branch")
    run_git(root, ["merge", "--ff-only", remote_base])
    ensure_no_git_operation(root)
    ensure_clean(root)
    ensure_binding(root, branch, args, binding)
    if current_branch(root) != config.base:
        raise LifecycleError("Current branch changed during cleanup")
    local_ref = run_git(root, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], check=False)
    if local_ref.returncode == 0:
        if run_git(root, ["rev-parse", f"refs/heads/{branch}"]).stdout.strip() != candidate:
            raise LifecycleError("Local feature branch changed; refusing deletion")
    elif local_ref.returncode != 1:
        raise LifecycleError("Unable to inspect local feature branch")
    if origin_repository(root) != identity:
        raise LifecycleError("Origin repository changed during cleanup")
    tip = remote_feature_tip(root, branch)
    if tip is not None:
        if tip != candidate:
            raise LifecycleError("Remote feature branch changed; refusing deletion")
        run_git(root, [
            "push", f"--force-with-lease=refs/heads/{branch}:{candidate}",
            "origin", f":refs/heads/{branch}",
        ])
        if remote_feature_tip(root, branch) is not None:
            raise LifecycleError("Remote feature branch deletion was not confirmed")
    if local_ref.returncode == 0:
        if run_git(root, ["rev-parse", f"refs/heads/{branch}"]).stdout.strip() != candidate:
            raise LifecycleError("Local feature branch changed; refusing deletion")
        run_git(root, ["branch", "-d", branch])
    elif local_ref.returncode != 1:
        raise LifecycleError("Unable to inspect local feature branch")


@contextmanager
def integration_lock(root: Path, branch: str) -> Iterator[None]:
    try:
        import fcntl
    except ImportError as error:
        raise LifecycleError("Integration requires POSIX file locking") from error
    common = Path(run_git(root, ["rev-parse", "--git-common-dir"]).stdout.strip())
    if not common.is_absolute():
        common = root / common
    directory = feature_storage_dir(common.resolve(), branch)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "integration.lock").open("a") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise LifecycleError("Another integration is already running for this feature") from error
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def integrate(args: argparse.Namespace) -> int:
    root = repository_root(Path(args.repo))
    config = load_config(root)
    branch = branch_name(args.feature, config.feature_prefix)
    approved_candidate(root, config, branch, args)
    policy(config)
    with integration_lock(root, branch):
        return integrate_locked(root, branch, args)


def integrate_locked(root: Path, branch: str, args: argparse.Namespace) -> int:
    config = load_config(root)
    candidate, tree, criteria = approved_candidate(root, config, branch, args)
    binding = (candidate, tree, criteria, sha256_bytes(config.policy_bytes()))
    required, review_required = policy(config)
    identity = origin_repository(root)
    repository = "/".join(identity)
    current = current_branch(root)
    if current not in (branch, config.base):
        raise LifecycleError("Integration requires the feature or base branch")
    pr = find_pr(root, repository, branch)
    if pr is not None:
        number = validate_pr(pr, branch, config.base, None)
        if pr.get("state") == "MERGED":
            validate_pr(pr, branch, config.base, candidate)
            cleanup(root, config, branch, candidate, pr, identity, args, binding)
            print(json_text({"integrated": True, "candidate_commit": candidate, "pr": number}))
            return 0
        if pr.get("state") != "OPEN":
            raise LifecycleError("Existing pull request is not open")
    if current != branch or head_commit(root) != candidate:
        raise LifecycleError("Unmerged integration requires the approved feature branch")
    base_oid = check_base(root, config, candidate)
    final_checks(root, config, branch, binding, args)
    ensure_binding(root, branch, args, binding)
    if origin_repository(root) != identity:
        raise LifecycleError("Origin repository changed during verification")
    run_git(root, ["push", "origin", f"{candidate}:refs/heads/{branch}"])
    if pr is None:
        body = "Approved candidate: " + candidate + "\n\nAcceptance criteria:\n" + "\n".join(
            f"- {item}" for item in criteria
        )
        gh(root, [
            "pr", "create", "--repo", repository, "--head", branch, "--base", config.base,
            "--title", branch.removeprefix(config.feature_prefix).replace("-", " "),
            "--body", body,
        ])
        pr = find_pr(root, repository, branch)
        if pr is None:
            raise LifecycleError("Created pull request could not be located")
        number = validate_pr(pr, branch, config.base, candidate)
    ready = ensure_ready(
        root, repository, identity, number, branch, config.base, candidate, required, review_required
    )
    if ready.get("baseRefOid") != base_oid:
        raise LifecycleError("Pull request base differs from the verified remote base")
    ensure_binding(root, branch, args, binding)
    latest = pull_request(root, repository, number)
    if validate_pr(latest, branch, config.base, candidate) != number:
        raise LifecycleError("Pull request identity changed during integration")
    validate_review_policy(latest, review_required)
    if latest.get("baseRefOid") != ready.get("baseRefOid"):
        raise LifecycleError("Pull request base changed during verification")
    if required_checks(latest, required) != "passed":
        raise LifecycleError("Required CI checks are no longer passing")
    if latest.get("mergeable") != "MERGEABLE" or latest.get("mergeStateStatus") != "CLEAN":
        raise LifecycleError("Pull request is no longer mergeable")
    if unresolved_threads(root, *identity, number):
        raise LifecycleError("Pull request has unresolved review threads")
    validate_review_opinions(
        root, *identity, number, candidate, review_required, pr_author(latest)
    )
    if origin_repository(root) != identity:
        raise LifecycleError("Origin repository changed during integration")
    if check_base(root, config, candidate) != base_oid:
        raise LifecycleError("Remote base changed during integration")
    ensure_binding(root, branch, args, binding)
    gh(root, [
        "pr", "merge", str(number), "--repo", repository, "--merge",
        "--match-head-commit", candidate,
    ])
    merged = pull_request(root, repository, number)
    if validate_pr(merged, branch, config.base, candidate) != number:
        raise LifecycleError("Pull request identity changed after merge")
    cleanup(root, config, branch, candidate, merged, identity, args, binding)
    print(json_text({"integrated": True, "candidate_commit": candidate, "pr": number}))
    return 0
