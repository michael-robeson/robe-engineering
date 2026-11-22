# Lifecycle integration

The shared CLI implements the approved lifecycle using Git, GitHub CLI, and
repository-owned policy. Approval is bound to the committed candidate,
acceptance criteria, and quality policy; it is a local workflow safeguard,
not proof of identity. Git and GitHub are the sources of operational state,
not a persistent phase machine.

Integration requires an explicit repository review policy, named required
checks, current successful readiness evidence, and final verification.
Where review is required, at least one current approving GitHub review must
refer to the exact approved candidate. Requested changes and unresolved
threads block integration even when review is optional.
Missing or ambiguous state, failed checks, unresolved review threads, changed
approved content, and conflicts block the operation. Repository configuration
classifies checks that require separate authorization. The current remote
base must be an ancestor of the approved candidate; a changed base requires a
new candidate and approval rather than silently integrating an unreviewed
combination.

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
