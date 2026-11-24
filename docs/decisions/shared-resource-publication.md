# Shared engineering resource ownership, publication, and consumption

**Status:** Accepted  
**Accepted:** 2026-11-24

## Context

Reusable agents and skills need a canonical owner, a controlled publication
point, and consumer paths that match each resource type. `robe-engineering`
maintains canonical resources, evaluations, provenance, and adoption
decisions. `robe-land/.github` publishes approved copies and owns the
publication catalog. The catalog is an index of published versions and their
canonical sources, not a duplicate evaluation record.

Adoption and approval to publish are distinct milestones. A published
resource may be public, so its licensing and attribution must be clear.
Existing local skill links are development conveniences, not distribution.

GitHub Copilot discovers organization agents through the root `agents/`
directory in the organization's `.github` or `.github-private` repository.
Skills have no corresponding organization-wide native discovery location.
GitHub's skill tooling supports repository skill publication and
version-pinned installation; a release is a snapshot of the repository, not
a separate package for each skill. These mechanisms and their limitations
are described in the [GitHub custom agents documentation](https://docs.github.com/copilot/how-tos/administer-copilot/manage-for-organization/prepare-for-custom-agents),
[GitHub skill documentation](https://docs.github.com/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills),
and [`gh skill` publish](https://cli.github.com/manual/gh_skill_publish)
and [install](https://cli.github.com/manual/gh_skill_install) references.

## Decision

1. **Canonical ownership stays in Engineering.** `robe-engineering` is the
   source of truth for resource content, evaluations, provenance, licensing
   evidence, and adoption status. `robe-land/.github` owns the public
   distribution artifacts and publication catalog. Published copies are not
   independently edited.

2. **Publication is a separate, manual approval and release.** Engineering
   must explicitly approve a specific canonical revision for publication.
   The approved copy is transferred to the distribution repository through
   its normal review and merge process. The publication catalog records the
   resource identity and type, canonical source revision, published version
   and path, license and attribution, and publication status. Evaluation
   evidence remains in Engineering. Updates and corrections start in the
   canonical source and require a new approved publication.

3. **Use native discovery and opt-in installation.** Publish agents in the
   organization repository's root `agents/` directory. They are discovered
   as organization agents by supported GitHub Copilot clients, including
   VS Code when organization discovery is available. Publish skills in a
   supported repository skills layout, such as `skills/<name>/SKILL.md`.
   Consumers opt in using supported installation mechanisms. A skill placed
   in `.github/skills/` is project-scoped to that repository, not an
   organization-wide skill. The personal Specification Authoring symlink is
   temporary and is not part of this architecture.

4. **Version each resource independently.** Assign each resource its own
   SemVer version and a resource-qualified Git tag of the form
   `<resource>-v<major>.<minor>.<patch>`, for example
   `specification-authoring-v1.0.0` and
   `portable-adr-generator-v1.0.0`. Record the version and tag in the
   publication catalog. Published tags must not be moved or reused; any
   correction requires a new resource version and tag.

   For skills, use GitHub's supported skill publisher with the
   resource-qualified tag and install the selected skill with that exact tag
   pinned. Do not rely on repository-wide latest-release resolution for
   resource versions. A release still represents the repository snapshot at
   its tag, while the named skill is selected from that snapshot. Validate
   the resource-qualified tag convention against the supported skill
   tooling during the first skill publication. If it is incompatible, stop
   and return the issue for architectural review; do not introduce custom
   distribution tooling or use SemVer build metadata to work around it.

   Organization-level agent discovery follows the current default branch;
   consumers receive its current approved version and cannot select a prior
   version through that native discovery mechanism. The agent's
   resource-qualified tag identifies its release for traceability, not as a
   consumer pin.

5. **Preserve applicable rights.** Independently authored resources use the
   MIT license. Third-party resources retain their applicable license and
   required attribution in the published distribution.

6. **Evolve from the immediate need.** Initially publish and verify
   consumption of the Portable ADR Generator agent and Specification
   Authoring skill. Keep publication manual and defer synchronization
   services, custom installers, and other distribution infrastructure until
   experience demonstrates a need. The existing [lifecycle integration
   decision](./lifecycle-integration.md) remains authoritative for feature
   review and integration mechanics.

## Consequences

Engineering remains the single canonical owner, while the organizational
repository provides a clear public publication point. Resource-qualified
tags support independent version histories in one repository, and pinned
skill installation avoids ambiguity from a repository-wide latest release.

Manual publication requires review of copied content and provenance. GitHub
skill releases remain repository snapshots, and the skill CLI is a preview
feature. Organization agents always resolve to the current default-branch
version; historical tags do not provide agent version selection. Skills
require an explicit consumer installation because there is no native
organization-wide skill discovery mechanism.

## Initial release verification

Before relying on either published resource, verify its discovery,
installation, and behavior in a fresh session using the intended Copilot
harness. For the first skill release, verify both publication and exact-tag
installation with the supported GitHub skill tooling. Review the agent's
display name and tool access, organization Copilot policy, and publication
repository protections as part of first-release verification. These checks
do not block acceptance of this decision.
