# Robe Engineering Capability Catalog

A private, personal inventory of reusable Copilot skills, agents, and
instructions. The catalog describes capabilities; it does not install them,
grant permissions, or replace their owning instructions.

## Contents

- [catalog.json](catalog.json): machine-readable inventory.
- [evaluations/](evaluations/): focused reviews and outstanding decisions.
- [agents/](agents/): personal-agent candidates under evaluation, not installed.

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

- Personal Copilot skills and agents can eventually be maintained here and
  installed in harness-supported user locations after review. Candidate files
  in this repository are not installed or adopted merely by being present.
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
