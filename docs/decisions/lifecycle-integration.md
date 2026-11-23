# Lifecycle integration

The shared CLI implements the approved lifecycle using Git, GitHub CLI, and
repository-owned policy. Approval is bound to the committed candidate,
acceptance criteria, and quality policy; it is a local workflow safeguard,
not proof of identity. Git and GitHub are the sources of operational state,
not a persistent phase machine.

Integration requires an explicit repository review policy, named required
checks, current successful readiness evidence, and final verification.
Where review is required, at least one current approving GitHub review by
someone other than the PR author must refer to the exact approved candidate.
An unverifiable PR author, partial GitHub API errors, requested changes, and
unresolved threads block integration even when review is optional.
Missing or ambiguous state, failed checks, unresolved review threads, changed
approved content, and conflicts block the operation. Repository configuration
classifies checks that require separate authorization. The current remote
base must be an ancestor of the approved candidate; a changed base requires a
new candidate and approval rather than silently integrating an unreviewed
combination.

Routine feature development uses the existing working checkout; the
implementation does not create linked Git worktrees. Startup reuses a clean,
generated, local-only feature branch if one is already checked out. When a
branch is needed, startup requires the clean configured base, synchronizes it
with a fast-forward from `origin`, and generates a collision-resistant
local-only name automatically. It does not request a feature scope or branch
name. Dirty work, an unrelated checked-out branch, or unsafe base
synchronization is preserved and reported as a blocker rather than prompting
the developer to switch directories or creating an alternative worktree.

Following a verified merge and safe local synchronization, cleanup removes
only the reviewed branch. Remote deletion uses an expected-SHA lease so a
branch that advanced after verification is not deleted. Local deletion uses
Git's non-forced merged-branch check. The initial implementation supports
merge commits for automatic integration and cleanup; squash and rebase require
a separate safe cleanup design.

An interruption is resumed from Git and GitHub state using the existing
approval and minimal local recovery information. A per-feature operating
system lock shared by worktrees prevents concurrent integration; it releases
automatically on process exit. Integration requires POSIX file locking.
Tool permissions and GitHub
authentication remain external prerequisites. Neither this decision nor the
CLI grants permission to bypass them.

GitHub's merge API can atomically match the PR head but does not bind the
base SHA or review state. Server-side protections are needed to close races
between the final checks and the merge request.

For this repository, the configured CI requirement is the
`lifecycle-verify` pull-request job running `./scripts/verify`; the local
policy does not add an independent GitHub review requirement. The user's
explicit candidate approval authorizes integration but does not bypass any
GitHub-required review or other protection. Configuration alone does not
establish server-side branch protection. The initial workflow and its
reported check name require a real GitHub integration exercise.

The initial integration is intended as a combined Increment 1 and Increment 2
PR against `develop`. Increment 1's earlier approval did not authorize its
integration; the combined candidate requires its own explicit integration
authorization after review. The separate Increment 1 feature branch is not
automatically deleted by the combined integration.

After a verified merge, synchronization, and safe cleanup of the integrated
feature branch, the CLI creates a new local-only working branch from the
synchronized base. Its name is `feature/next-<uuid4-hex>` (using the
repository-configured feature prefix), so users do not need to supply a scope
or branch name for this disposable branch. The UUID provides collision
resistance; the CLI also checks local and remote refs and never overwrites an
existing branch or pushes the new one.

The standard startup command reuses this branch while it remains clean and
local-only. Neither startup nor integration creates a linked worktree.

The CLI records the generated name and synchronized base commit in Git
metadata before creating the branch. `resume` reuses that record after an
interruption, returns the same branch after successful creation, and refuses
to switch away from unrelated work or to reuse a branch whose tip has changed.
This keeps branch creation idempotent without weakening the existing merge,
base-synchronization, or branch-cleanup checks. Creating this local branch does
not authorize commits, publishing, pull-request creation, approval, or further
integration.
