# Robe Engineering Capability Catalog

A private, personal inventory of reusable Copilot skills, agents, and
instructions. The catalog describes capabilities; it does not install them,
grant permissions, or replace their owning instructions.

## Contents

- [catalog.json](catalog.json): machine-readable inventory.
- [evaluations/](evaluations/): focused reviews and outstanding decisions.
- [agents/](agents/): source files for personal-agent candidates under evaluation.

The initial inventory was captured from the local machine on 2026-11-21.
Paths beginning `~/` are observed locations on that machine, not promises
that a capability is installed or loaded elsewhere. Repository revision
values refer to the last commit observed for that file; provider-managed
cache names are not upstream versions. `null` means unknown or not verified.

## Lifecycle

1. **Discover:** record name, type, source and license if known, revision,
   intended scope, observed location, and overlap. Do not execute or install
   an unreviewed capability.
2. **Evaluate:** inspect its instructions and any scripts, permissions,
   dependencies, and applicable license; compare project conventions and
   existing capabilities. Record risks and evidence in `evaluations/`.
3. **Adopt:** confirm the intended scope and supported harness location;
   verify discovery and behavior in a fresh session. Record the approved
   source revision, customization, installation location, and review date.
   Catalog status alone does not install or activate anything.
4. **Update:** compare upstream changes against the recorded revision and
   local customizations, review safety and compatibility, then verify again.
5. **Retire:** record why and when a capability was retired. Remove or disable
   an installation only with appropriate authorization; retain the catalog
   history and provenance.

Statuses are `discovered`, `evaluating`, `adopted`, and `retired`. They
describe review status, not proof of activation. Never store credentials,
tokens, private runtime data, or sensitive payloads in the catalog.

## Scope and ownership

- Personal Copilot skills and agents can be maintained here and installed in
  harness-supported user locations after review. A specifically authorized
  trial installation may remain under `evaluating`; candidate files are not
  installed or adopted merely by being present.
- Project-specific instructions and skills remain authoritative in their
  owning repositories. Their records here are references, not copies.
- Provider-managed runtime and plugin capabilities remain managed by their
  providers. Cache paths are observations, not stable installation APIs.
- Avoid duplicating an existing capability under the same name across scopes
  unless activation and precedence have been reviewed in the target harness.

The [ADR Generator evaluation](evaluations/adr-generator.md) documents a
proposed personal placement and its conflicts with repository conventions.
The [provider capabilities evaluation](evaluations/provider-capabilities.md)
records discovery and provenance limits.

## Engineering lifecycle CLI setup

The CLI requires Python 3.11 or newer. From the repository root, create a
local virtual environment and install the package in editable mode:

```sh
python3 -m venv .venv
```

Activate it in each development terminal before using the CLI. For Bash or
other POSIX-compatible shells:

```sh
. .venv/bin/activate
```

For Fish:

```fish
source .venv/bin/activate.fish
```

With the environment activated, install the CLI using its `python` and check
that its executable is on `PATH`:

```sh
python -m pip install -e .
eng-lifecycle --help
```

Activation affects only the current shell and its child processes. For a new
terminal, activate the same environment again; from another repository, use
the activation script in this repository's `.venv` by its path.

Alternatively, if `~/.local/bin` is on `PATH`, expose the installed command
to new terminals without activation. From this repository's root:

```sh
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/.venv/bin/eng-lifecycle" "$HOME/.local/bin/eng-lifecycle"
```

The link points to this checkout and its virtual environment; keep both in
place. Do not replace an existing command without reviewing it. Verify
`eng-lifecycle --help` in a new terminal. If the command is not found,
complete the setup rather than using a session-specific executable path.

## Engineering lifecycle CLI

The local, dependency-light lifecycle CLI supports readiness and
post-approval integration.

Run the required local checks from the repository root:

```sh
./scripts/verify
```

The entry point compiles the Python sources and runs the unit suite. The
lifecycle readiness gate invokes it; verification alone does not record
approval or authorize integration.

```sh
eng-lifecycle start --repo . --feature shared-lifecycle-cli
eng-lifecycle commit --repo . --message "Implement increment" --path src
eng-lifecycle review --repo . --feature shared-lifecycle-cli --criteria-file acceptance.txt
eng-lifecycle approve --repo . --feature shared-lifecycle-cli --criteria-file acceptance.txt --message APPROVED
eng-lifecycle status --repo . --feature shared-lifecycle-cli --criteria-file acceptance.txt
eng-lifecycle integrate --repo . --feature shared-lifecycle-cli --criteria-file acceptance.txt
eng-lifecycle resume --repo . --feature shared-lifecycle-cli --criteria-file acceptance.txt
```

Install the repository pre-commit hook separately:

```sh
sh scripts/install-hooks.sh
```

The CLI stores only review evidence and approval metadata under Git's
actual git directory. It derives branch, commit, worktree, review, and
candidate state from Git. Start requires a clean checkout of the configured
base and refuses local-ahead or divergent history. Scoped commits refuse an
already populated index; installed Git hooks run normally. The supplied hook
checks staged Python blobs, not unstaged working-tree contents.

The repository's `.github/lifecycle.json` defines commands as shell-like
strings or argument arrays, executed directly without a shell. Readiness
requires at least one check. For a check needing special authorization, declare
its category in `special_authorization` and use an entry such as
`{"argv": ["example-check"], "authorization": "database"}`. Supply
`--authorize database` to `review` or `commit` only after obtaining the
appropriate task-specific authorization. This flag and the repository's
classification are workflow safeguards, not permission enforcement or a
sandbox; commands can have effects beyond what their labels describe.

Review requires a clean committed candidate and matching feature name. A
failed or interrupted review cannot be approved. The exact `APPROVED`
message must first be given by the user in Copilot Chat; the local record is
not proof of identity. Approval and status require the same acceptance
criteria and validate the current review, complete check evidence, candidate,
and policy. A successful rerun with the same binding need not invalidate
approval merely because timing or other incidental evidence changed.
Policy drift is reported even when the changed policy file makes the worktree
dirty; approval still requires a clean worktree.

### Post-approval integration

Only run `integrate` or `resume` after explicit user approval of that exact
candidate. They validate the existing approval and evidence, run readiness
and integration checks, push the approved commit, create or update its PR,
wait up to ten minutes for required CI, and check review threads and merge
eligibility. They merge only with a matching PR head, then synchronize the
local base and safely delete the merged feature branch. `resume` reconstructs
state from Git and GitHub after interruption; it uses the same approval and
criteria. No new source commit is created after approval.

Each target repository must configure a nonempty `required_ci` array and an
explicit `required_review` boolean in `.github/lifecycle.json`. A true
review policy requires an approving GitHub review of the exact approved
candidate; false permits no review but still blocks changes requested,
GitHub-required reviews, and unresolved
review threads. All named CI checks must succeed; missing, skipped, failed,
ambiguous, or pending checks never count as a pass. Checks needing separate
authorization still require the appropriate `--authorize` category. The
current catalog repository does not yet configure required CI or a review
policy, so its own integration is blocked until those are decided.

The remote base must remain an ancestor of the approved candidate. Local base
divergence, changed approval bindings, conflicting PRs, and changed branch
tips block the operation. Only merge commits are supported for automatic
integration; squash and rebase are blocked before pushing. Remote cleanup
uses an expected-SHA lease, and local cleanup uses non-forced Git deletion.
GitHub branch protections are needed to close races involving base or review
changes between the final local checks and the merge request. Copilot
permissions and GitHub authentication remain separate prerequisites.
Integration uses a per-feature lock shared by worktrees; the lock is released
when the process exits, including after interruption. This implementation
requires POSIX file locking.
