# Evaluation: Specification Authoring

- **Status:** adopted as a canonical Engineering skill, independently
  authored from approved requirements.
- **Reviewed:** 2026-11-24.
- **Scope:** Cross-repository authoring guidance; each specification remains
  owned by the repository responsible for its capability.

## Provenance and rights

The archived candidate is
[Specification.agent.md](../agents/sources/robe-event-platform/specification.agent.md),
originally observed at
`robe-event-platform/.github/agents/specification.agent.md`. Its SHA-256 is
`4f3dd21f43b8ab3bb62e36f8ff3a5d3484bc88fc8ad9698fcad1060a4cb6dbdc`.
Its Git blob exactly matches
[`github/awesome-copilot/agents/specification.agent.md` at commit
`93fc8b9ee3ef56b9b5e7261e6ce92d314cb2c1cf`](https://github.com/github/awesome-copilot/blob/93fc8b9ee3ef56b9b5e7261e6ce92d314cb2c1cf/agents/specification.agent.md).
The upstream repository's MIT notice at that revision is preserved alongside
the archive in
[agents/sources/robe-event-platform/LICENSE](../agents/sources/robe-event-platform/LICENSE);
the per-file blob match and attribution are recorded in
[the source index](../agents/sources/README.md). This establishes an MIT
licensed source match for the archived bytes, but does not establish the
original download route or acquisition date. The upstream notice names
GitHub, Inc.; the file does not identify individual authors.

The previous adopted text, skill blob
`4cdccfea04203ea2ce2000cdad8fa08a71f45387`, has been replaced. The current
skill and template were independently written from the requirements approved
for this work: clear expected behavior; distinct requirements, constraints,
and recommendations; explicit scope; relevant interfaces and data boundaries;
verifiable acceptance checks; and conditional use of identifiers,
dependencies, examples, and edge cases. They also apply the approved
Engineering principles of proportional documentation, authoritative
references, repository-owned conventions, and no blanket specification
requirement. The archived candidate remains preserved for provenance only;
its text is not the source of the current content. The candidate remains
discovered, not adopted, and this rights finding does not authorize its
publication as an Engineering resource.

## Design assessment

The skill is optional and is activated by a specification request or when an
existing specification is part of the task. Its template is an outline rather
than a required form. The guidance directs authors to follow the capability
owner's repository, refer to accepted ADRs/contracts/schemas, and inherit its
testing and documentation conventions instead of prescribing a fixed format
or implementation.

For Platform capabilities, the skill places specification ownership in
`robe-platform-event` and points authors to ADR-0005's implement/accommodate/
defer reasoning without turning deferred concerns into implementation
requirements.

## Discovery experiment

The target `~/.copilot/skills/specification-authoring` did not exist before
the test. A symbolic link was created from that location to the canonical
`~/Projects/robe-engineering/skills/adopted/specification-authoring`
directory. The link resolved to the Engineering checkout, and both
`SKILL.md` and `templates/specification.md` were readable through it. This
adds no copied or separately maintained content.

## Current installation inventory

The current `~/.copilot/skills/specification-authoring` path is a copied
installation pinned to the published `specification-authoring-v1.0.0` tag in
`robe-land/.github`. Its `SKILL.md` records the pinned reference and tree
revision. The path is a directory, not a symbolic link. The symlink
experiment above is retained as historical evidence and does not describe
the current installation.

In fresh Copilot chat `e063bc5b-eeb5-4511-a0b6-c443f5322227`, the submitted
`/specification-authoring` prompt produced an actual `skill` invocation for
`specification-authoring` in the session tool log. The session then read
`~/.copilot/skills/specification-authoring/templates/specification.md`
through the symlink and returned its headings. It produced a brief,
unsaved hypothetical outline, assigned Platform capability documentation to
`robe-event-platform`, and used ADR-0005 to distinguish current requirements
from accommodate/defer topics. Its tool log shows no file writes; the
Workbench was not touched.

The session metadata identified `robe-engineering` as the primary project,
with `robe-event-platform` among its working directories. Therefore this is
verified Copilot discovery, invocation, and template access in a multi-root
session with Platform available, but not in an isolated Platform-only
workspace. The tool-mediated invocation and file access required no manual
VS Code interaction. The visible slash-menu listing and single-root Platform
workspace behavior were not inspected; confirming those specific UI states
requires opening a Platform-only VS Code chat and checking its `/` menu or
Chat: Open Customizations.

The tested personal path is supported by
[VS Code's Agent Skills documentation](https://code.visualstudio.com/docs/agent-customization/agent-skills),
which lists `~/.copilot/skills/` as a personal skill location. This experiment
verifies only this machine's link and session. The absolute symlink depends on
the Engineering checkout remaining at its current path; it is not a
cross-machine distribution mechanism.

