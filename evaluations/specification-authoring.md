# Evaluation: Specification Authoring

- **Status:** adopted as a canonical shared skill in `robe-engineering`.
- **Reviewed:** 2026-11-23.
- **Scope:** Reusable authoring guidance; specifications remain owned by the
  repository that owns the capability.

## Provenance and license

The source is the archived downloaded
[Specification agent](../agents/sources/robe-event-platform/specification.agent.md),
originally observed at
`robe-event-platform/.github/agents/specification.agent.md`. Its SHA-256 is
`4f3dd21f43b8ab3bb62e36f8ff3a5d3484bc88fc8ad9698fcad1060a4cb6dbdc`, verified
against the preserved source file. The actual download source, upstream
revision, and license are unknown; no license is asserted for the source or
the derived skill. The archived candidate remains unchanged. The adopted
methodology and template are a tailored rewrite rather than a copy of the
agent's template.

## Assessment and adaptation

The source usefully emphasizes clear requirements, explicit constraints,
interfaces, testable acceptance criteria, traceability, dependencies, and
relevant examples or edge cases. Its fixed directory and naming convention,
required section list, prescriptive test strategy, and demand for
self-contained documents conflict with repository-owned documentation
conventions and the need to reference authoritative ADRs, contracts, and
schemas.

The adopted skill retains the useful concepts while making scope and detail
proportionate. Its companion template is optional by section; requirements,
constraints, recommendations, interfaces, criteria, examples, and identifiers
are used only where they add value. Testing follows the owning repository's
conventions. The skill does not prescribe implementation absent an established
constraint, mandate a specification for each increment, or establish
specification governance.

## Discovery and consumption evidence

The canonical source is under `skills/adopted/`, outside the Platform
repository's `.github/skills/` discovery path. Platform architecture
documentation assigns shared skill ownership to `robe-engineering`, but the
repositories do not establish a cross-repository distribution mechanism.
Therefore this evaluation does not claim that the skill is discoverable or
invokable from a Platform workspace. Consumer wiring and its discovery test
remain pending an approved distribution decision; no copy or new mechanism
has been introduced.

