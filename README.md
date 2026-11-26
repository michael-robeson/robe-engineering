# Robe Engineering Capability Catalog

A private, personal inventory of reusable Copilot skills, agents, and
instructions. The catalog describes capabilities; it does not install them,
grant permissions, or replace their owning instructions.

> Maintained by [Robe Land](https://github.com/robe-land).
>
> Original work is licensed under [LICENSE](LICENSE). Third-party
> materials retain their applicable licenses and copyright notices; see
> the notices accompanying those materials and the repository's
> third-party attribution index, where applicable.

## Contents

- [catalog.json](catalog.json): machine-readable inventory.
- [evaluations/](evaluations/): focused reviews and outstanding decisions.
- [agents/sources/](agents/sources/): original and archived agent material, kept outside Copilot discovery paths.
- [agents/adopted/](agents/adopted/): canonical sources for approved agent implementations.
- [skills/sources/](skills/sources/): candidate skill sources with recorded provenance.
- [skills/adopted/](skills/adopted/): canonical sources for approved reusable skills.
- [docs/decisions/](docs/decisions/): shared engineering decisions.
- [.github/copilot-instructions.md](.github/copilot-instructions.md): persistent repository instructions.
- [prompts/](prompts/): reusable prompt templates.

The inventory was first captured from the local machine on 2026-11-21 and
reorganized on 2026-11-23. Paths beginning `~/` are observed locations on
that machine, not promises that a capability is installed or loaded
elsewhere. Repository revision values refer to the last commit observed for
that file; provider-managed cache names are not upstream versions. `null`
means unknown or not verified.

`catalog.json` is the authoritative inventory for agents and skills. It
records evaluation status, provenance, source revision or its unknown state,
and current and original locations. Evaluation documents provide supporting
evidence. Candidate files under `agents/sources/` are not approved or
activated; only deliberately installed approved implementations are used.
Repository-scoped skills remain in their owning repositories and are
referenced here rather than copied.

The ADR Generator's committed Engineering original and archived Platform
candidate are kept separately under `agents/sources/`; the adopted portable
implementation remains under `agents/adopted/`. The catalog and evaluation
record their verified content relationships without asserting a derivation
between the two originals. The adopted
[Specification Authoring skill](skills/adopted/specification-authoring/SKILL.md)
and optional template provide reusable documentation guidance; the skill's
provenance and evaluation are recorded in
[evaluations/specification-authoring.md](evaluations/specification-authoring.md).
The decisions directory contains the lifecycle integration decision record.

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
eng-lifecycle start --repo .
eng-lifecycle commit --repo . --message "Implement increment" --path src
```

`start` initiates a feature and prints the generated or reused branch. For an
already active feature, use `continue` with that branch; it never creates or
switches branches. For later `commit`, `review`, `architecture-review`,
`approve`, `status`, `integrate`, and `resume` commands, pass the feature
branch to `--feature`.

Install the repository pre-commit hook separately:

```sh
sh scripts/install-hooks.sh
```

The CLI stores only review evidence and approval metadata under Git's
actual git directory. It derives branch, commit, worktree, review, and
candidate state from Git. Routine development uses the existing checkout;
the CLI does not create linked worktrees. `start` is for new work: it reuses a
clean generated local-only branch when one is checked out. Otherwise, it
requires a clean checkout of the configured base, fast-forwards it from
`origin`, and creates a collision-resistant local-only branch automatically.
It never stashes or switches directories to bypass a dirty checkout or
unrelated branch.

`continue --repo . --feature <branch>` resumes work on the existing current
feature branch, including with uncommitted changes. It reports the worktree
changes without staging or modifying them. Establish that changes belong to
the active feature before editing or committing; if ownership is uncertain,
preserve the changes and ask only about that ambiguity. Use scoped commits and
do not include unrelated paths. The CLI refuses a pre-populated index.
Readiness review still requires a clean committed candidate, so unresolved
unrelated work must be kept out of the candidate without stashing or resetting
it. `resume` remains exclusively for recovering an interrupted
post-approval integration.

The repository's `.github/lifecycle.json` defines commands as shell-like
strings or argument arrays, executed directly without a shell. Readiness
requires at least one check. For a check needing special authorization, declare
its category in `special_authorization` and use an entry such as
`{"argv": ["example-check"], "authorization": "database"}`. Supply
`--authorize database` to `review` or `commit` only after obtaining the
appropriate task-specific authorization. This flag and the repository's
classification are workflow safeguards, not permission enforcement or a
sandbox; commands can have effects beyond what their labels describe.

Readiness review requires a clean committed candidate and matching feature
name. A failed or interrupted review cannot be approved. Perform the
architectural review separately after readiness and record its outcome for the
same candidate:

```sh
eng-lifecycle architecture-review --repo . --feature <branch> \
  --criteria "Acceptance criteria" --decision accepted \
  --reviewer "Reviewer" --evidence "Review findings and disposition"
```

An architectural decision of `changes-requested` cannot be approved. The
architectural-review record, readiness evidence, and approval are bound to the
candidate commit and tree, acceptance criteria, and quality policy. A new
candidate therefore invalidates stale readiness, architectural-review, and
approval evidence; rerun the gates for the changed candidate. A successful
readiness rerun on the same candidate need not invalidate approval merely
because timing or other incidental evidence changed. Policy drift is reported
even when the changed policy file makes the worktree dirty; approval still
requires a clean worktree.

Architectural-review and approval records are local consistency metadata under
Git's actual git directory, not cryptographic signatures or substitutes for
configured GitHub protections.

The exact `APPROVED` message must first be given by the user in Copilot Chat
for that reviewed candidate; task authorization for implementation or
verification does not imply integration approval. Routine authorized
implementation, verification, scoped commits, and lifecycle commands do not
need repeated confirmation. Use `--authorize <category>` for a special check
only when its effects are not already authorized for the task; this flag is a
workflow safeguard, not permission enforcement or a sandbox.

### Post-approval integration

Only run `integrate` or `resume` after explicit user approval of that exact
candidate. They validate the readiness, architectural-review, and approval
evidence, run readiness and integration checks, push the approved commit, create or update its PR,
wait up to ten minutes for required CI, and check review threads and merge
eligibility. They merge only with a matching PR head, then synchronize the
local base and safely delete the merged feature branch. After cleanup, the CLI
creates a collision-resistant, local-only branch using the configured feature
prefix and a UUID4 identifier, from the synchronized base, and reports its
name; no scope or branch name is requested. `resume` reconstructs state from
Git and GitHub after interruption and reuses the same generated branch; it
uses the same approval and criteria. The next `start` reuses this branch when
it is still clean and local-only. No new source commit is created after
approval.

Each target repository must configure a nonempty `required_ci` array and an
explicit `required_review` boolean in `.github/lifecycle.json`. A true
review policy requires an approving GitHub review of the exact approved
candidate by someone other than the PR author; false permits no review but
still blocks changes requested, GitHub-required reviews, and unresolved
review threads. All named CI checks must succeed; missing, skipped, failed,
ambiguous, or pending checks never count as a pass. Checks needing separate
authorization still require the appropriate `--authorize` category. This
repository requires the `lifecycle-verify` GitHub Actions job, which runs
`./scripts/verify` on pull requests targeting `develop`; it does not add an
independent review requirement. The user's explicit candidate approval
authorizes integration but does not bypass GitHub-required reviews or other
protections. This configuration is enforced by the CLI; it does not itself
configure GitHub branch protection. The workflow and check name still need
verification in a real pull request. If a required GitHub review is not yet
available, integration stops; use `resume` after it is satisfied.

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

### Bootstrap integration

The initial integration candidate is stacked on the unmerged Increment 1
candidate. The intended first PR targets `develop` and includes both
increments, including the CI and policy configuration. Before creating that
PR, the user must explicitly approve integration of the reviewed combined
candidate; the earlier Increment 1 approval did not authorize integration.
If the base or candidate changes, produce new readiness evidence and obtain
new approval. The separate Increment 1 branch is not the combined PR's
feature branch and is not automatically cleaned up by this integration.
