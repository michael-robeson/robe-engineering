# Repository inspection and verification

## Starting feature work

Use the existing working checkout for routine feature development. Do not
create a linked Git worktree unless the developer explicitly requests one.
Before implementation, run `eng-lifecycle start --repo .` from the repository
root. The command does not take a feature name or scope; it reports the
generated or reused branch.

If the checkout is already on a clean, generated, local-only
`feature/next-<uuid>` branch, continue on it. Otherwise, branch creation is
allowed only from a clean checkout of the configured base: the command
fast-forwards that base from `origin` and creates a collision-resistant,
local-only branch automatically. If the checkout is dirty, on another branch,
or the base cannot be safely synchronized, preserve all work and stop. Do not
ask for a routine branch name or feature scope, stash or reset changes, or
silently switch directories or create an alternative worktree.

For routine read-only Git inspection, use predictable individual commands
such as `git status --short --branch` and `git --no-pager diff --stat`.
Set the repository root using the terminal tool's working-directory option
when available, rather than adding `git -C`, `env --chdir`, or absolute
executable paths. If that option is unavailable, explain the limitation and
use the least intrusive explicit repository targeting needed.

Run `./scripts/verify` from the repository root for the required local
verification. Invoke the entry point directly rather than assembling ad hoc
shell commands, environment assignments, output redirection, or compound
shell logic. Preserve command exit codes and report actual results.

Invoke lifecycle operations with `eng-lifecycle` from `PATH`, not an
absolute or session-specific virtual-environment path. Follow the
[developer setup](../README.md#engineering-lifecycle-cli-setup) to install
and activate the editable package. If the terminal cannot access the
executable, report the setup limitation instead of substituting a wrapper
or changing permission settings.

Verification does not approve a feature or authorize PR integration. Follow
the lifecycle's separate readiness and explicit approval requirements. Do not
change permission settings or bypass security controls to avoid prompts.
