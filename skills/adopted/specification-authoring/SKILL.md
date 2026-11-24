---
name: specification-authoring
description: Use when asked to create, review, or maintain a specification or when an existing spec is part of the task; provides proportionate, evidence-grounded guidance.
---

# Specification Authoring

Use this skill when a specification is requested or when an existing
specification is part of the work. Do not require a specification for every
implementation increment.

## Authoring method

1. **Establish purpose and ownership.** Identify the outcome, intended readers,
   capability owner, scope, and exclusions. Follow the owning repository's
   documentation location, naming, formatting, and review conventions.
2. **Read authoritative context.** Inspect applicable repository instructions,
   architecture guidance, accepted ADRs, contracts, schemas, and existing
   documentation. Reference authoritative sources instead of restating them.
   If sources conflict or a decision is unresolved, preserve that uncertainty
   and identify the authority needed to resolve it; do not silently amend an
   accepted decision.
3. **Choose proportionate detail.** Include only sections useful to explain
   this capability and evaluate the intended outcome. A small change may need
   only scope, a few requirements, and acceptance criteria. Use the companion
   template as a menu, not a checklist.
4. **Separate kinds of statements.** Make requirements, constraints, and
   recommendations distinguishable. State requirements in clear, observable
   terms. Identify constraints as established boundaries or decisions.
   Present recommendations as guidance, not obligations. Avoid prescribing
   implementation details unless they are an established constraint.
5. **Describe boundaries that matter.** Document relevant interfaces, data
   meaning, ownership, compatibility, failure behavior, and security or
   operational obligations. Link to the owning contract or schema when it is
   authoritative; do not create a competing copy.
6. **Make outcomes verifiable.** Add acceptance criteria that can be checked
   against the requirements. Use requirement identifiers when they materially
   improve traceability across reviews, tests, or multiple interfaces; do not
   add identifiers merely for appearance. Inherit the repository's testing
   conventions, and do not invent frameworks, coverage thresholds, or test
   levels.
7. **Add context selectively.** Include dependencies, assumptions, examples,
   and edge cases when they change interpretation or behavior. Mark proposed
   behavior and unresolved questions as such. Avoid filling gaps with
   unsupported details.
8. **Review and maintain.** Check that the scope and exclusions are clear,
   statements are unambiguous, criteria are testable, references resolve, and
   no authoritative decision or contract is contradicted or duplicated.
   Update the specification when a related change makes it inaccurate; keep
   ownership with the repository that owns the capability.

## Output

Create or update the document at the location and in the format established
by its owning repository. For capabilities owned by `robe-event-platform`,
the specification belongs to that repository and follows its documentation
conventions. This shared skill provides authoring guidance; it does not set
platform architecture, create a platform contract, or establish specification
governance.

