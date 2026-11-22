# Repository inspection and verification

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
