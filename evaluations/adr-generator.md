# Evaluation: ADR Generator

- **Status:** evaluating
- **Observed:** 2026-11-21 in
  `~/Projects/robe-event-platform/.github/agents/adr-generator.agent.md`.
- **Upstream publisher, URL, revision, and license:** unknown; identify and
  review before redistributing or installing it.
- **Observed local SHA-256:**
  `abbf07c6a768a21baa94a1aed858510c8038cb89866461d47ab64817e9f347ac`.
  This identifies the inspected local file, not its origin or license.
- **Git state at inventory:** untracked in robe-event-platform.

The agent supplies a useful completeness checklist, alternatives analysis,
consequences, implementation notes, and references. It mandates
`docs/adr/`, `adr-NNNN-...` names, YAML front matter, and coded items.
Robe Event Platform instead uses `docs/decisions/`, `NNNN-...` names, and
its own ADR template. Other projects may differ too. A cross-project agent
would need to discover and respect each repository's conventions and avoid
inventing stakeholder information or implementation decisions.

**Placement decision pending:** after provenance and adaptation review, a
personal Copilot agent could use `~/.copilot/agents/`; repository-specific
versions belong with the owning repository. Do not install globally or
modify the existing file based on this record alone.
