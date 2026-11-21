# Evaluation: Provider-managed capabilities

- **Status:** discovered
- **Observed:** 2026-11-21 in VS Code plugin caches and session inventory.
- **Upstream identity, exact version, and license:** not verified per
  capability. A cache directory or session label is not a verified release.

The cached skills cover GitHub workflows, Python/Pylance workflows,
TypeScript setup and updates, customization migration, and canvas creation.
Some overlap with repository procedures; for example, pull-request creation
overlaps the PR step of each feature-lifecycle skill but does not replace
its project-specific review, verification, or cleanup requirements.

VS Code's generated Plan, Ask, and Explore files and the session's built-in
agents are runtime-managed. Their exact availability varies by harness,
session, and installed extensions. Inspect the active customizations in a
fresh session before relying on one. No cached file should be copied or
treated as an independently versioned personal installation without
separately verifying its origin, license, and intended maintenance model.
