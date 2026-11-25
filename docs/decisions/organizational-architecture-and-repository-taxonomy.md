# Organizational architecture and repository taxonomy

**Status:** Accepted  
**Accepted:** 2026-11-24

## Context

Robe Land needs clear ownership boundaries for engineering enablement,
platform capabilities, composable services, products, and organizational
configuration. Repository names should communicate those boundaries without
turning every logical component or runtime role into a separate repository.

The accepted
[shared-resource publication ADR](./shared-resource-publication.md)
currently assigns canonical engineering resources to `robe-engineering` and
publication to `.github`. This ADR establishes `robe-engineer` as the target
name for the Engineering Enablement layer; it does not rename the current
repository or change that accepted ownership decision.

## Decision

### Logical layers and repository names

The following naming convention applies to all new and existing repositories.
For existing repositories, the prescribed name is the target for a migration
that must be separately authorized; this ADR does not itself authorize or
perform a rename.

| Layer | Repository name | Responsibility |
| --- | --- | --- |
| Engineering Enablement | `robe-engineer` | Canonical engineering resources and cross-cutting development capabilities. |
| Platform | `robe-platform-<capability>` | Reusable technical and runtime capabilities that remain independent of business-service semantics. |
| Service | `robe-svc-<domain>-<capability>[-provider]` | A cohesive, composable service owned and evolved around a domain capability; the provider suffix is optional. |
| Application | `robe-app-<product>` | Product composition and product-specific workflows. |
| Presentation | `robe-ui-<product>` | A product's presentation layer only when it is independently maintained. |
| Shared runtime library | `robe-lib-<capability>` | A cohesive runtime library reused by multiple capabilities. |
| Organizational publication and configuration | `.github` | Organization-level configuration and the separately governed publication surface. |

These are logical ownership conventions, not mandatory deployment
boundaries. A repository does not have to map to one process, container,
deployment, or runtime role. Create or split a repository only when a durable
ownership boundary or genuinely independent lifecycle justifies it.

### Service organization and provider boundaries

Organize services by domain, then capability, and use a provider suffix only
when the service is specifically coupled to that provider. For example:

| Domain | Capability path | Illustrative repository name |
| --- | --- | --- |
| Communication | Email -> Gmail | `robe-svc-communication-email-gmail` |
| Persistence | `<capability>` -> optional `<provider>` | `robe-svc-persistence-<capability>[-provider]` |
| Commerce | `<capability>` -> optional `<provider>` | `robe-svc-commerce-<capability>[-provider]` |

The Persistence and Commerce entries illustrate the naming pattern only;
they do not authorize creating repositories or selecting capabilities or
providers. Keep provider-specific protocols and behavior behind the
provider-specific service boundary. Do not introduce a provider-neutral
abstraction solely in anticipation of hypothetical providers; introduce one
when concrete requirements justify it.

### Ownership and composition

1. Each service owns its externally consumed contracts, internal state and
   data model, and provider-specific integration behavior. Keep provider
   protocols and implementation details behind that service's boundary.
2. Assign each repository a cohesive capability owner and a clear lifecycle.
   Services may be composed by applications and may evolve independently.
3. Applications compose services and platform capabilities to deliver a
   product. Product-specific orchestration belongs with the application
   unless a durable, independently owned service capability warrants
   separation.
4. Platform capabilities provide reusable technical foundations and must
   not depend on business services or encode their business-specific
   semantics.
5. Shared runtime libraries provide focused reusable code; they are not a
   default location for unrelated functionality.
6. Producers and consumers describe runtime roles, not repository types.
   A capability may produce, consume, or do both without changing its
   repository boundary.
7. Keep the Workbench and reference implementations within the Event
   Platform. Do not create separate repositories for them merely to reflect
   their logical roles.

### Existing repositories and scope

The naming convention establishes target names for existing repositories as
well as names for new ones. Existing physical names and boundaries remain
until a separately authorized migration. This ADR does not require physical
deployment separation, create repositories, move content, change publication
ownership, or initiate implementation.

The accepted shared-resource publication ADR remains authoritative for
canonical resource ownership and the approval and publication of agents and
skills. This ADR describes the broader logical architecture; it does not
supersede that publication workflow.

## Consequences

The taxonomy makes capability ownership and provider-specific boundaries
easier to communicate while allowing a logical capability to remain inside an
existing repository when that is the simpler lifecycle. Repository creation,
renaming, migration, and deployment separation remain separate decisions
requiring concrete justification.

