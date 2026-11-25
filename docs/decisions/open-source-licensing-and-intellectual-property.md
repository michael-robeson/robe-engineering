# Open-source licensing and intellectual property

**Status:** Accepted  
**Accepted:** 2026-11-24

## Context

Public repositories need clear licensing, attribution, and provenance. A
repository may contain original Robe Land work alongside third-party
materials, so a repository-level license must not be treated as evidence
that every included file can be relicensed or redistributed.

The accepted
[shared-resource publication ADR](./shared-resource-publication.md)
already keeps canonical ownership, adoption, and publication distinct and
requires third-party resources to retain applicable licenses and attribution.
This ADR extends those principles to organization-wide repository visibility
and licensing; it does not replace the publication ADR.

## Decision

### Visibility and licensing of original work

1. Set public visibility as the default for Robe Land repositories, subject
   to verified rights and applicable security, privacy, contractual, and
   legal restrictions. A private exception must record its scope, owner,
   rationale, and review point.
2. License original Robe Land work under MIT when the rights holder and
   authority to grant that license are established. Every public repository
   must have a root-level `LICENSE` identifying the applicable terms and
   copyright holder(s). Where third-party material is present, the root
   license must distinguish the MIT-licensed original work from third-party
   material governed by separate terms. A repository containing only
   third-party material must point from its root license file to the
   applicable upstream licenses rather than imply that MIT covers that
   material.
3. Where evidence establishes that original work is personally authored and
   owned by Michael Robeson, identify Michael Robeson as its copyright
   holder. Do not infer this ownership for co-authored, assigned,
   employer-owned, client-owned, or third-party work; establish the
   applicable rights before applying a license or notice.
4. A root-level MIT license applies to the original work within its stated
   scope. It does not replace or expand the license of third-party
   dependencies, copied resources, or other separately owned material.

### Consistent attribution and provenance

1. Every public repository must have a root `README` containing this
   consistent attribution block:

   > Maintained by [Robe Land](https://github.com/robe-land).
   >
   > Original work is licensed under [LICENSE](LICENSE). Third-party
   > materials retain their applicable licenses and copyright notices; see
   > the notices accompanying those materials and the repository's
   > third-party attribution index, where applicable.

   The block identifies the repository's purpose nearby and must not imply
   that Robe Land owns all material in the repository.
2. Preserve upstream copyright and license notices with third-party
   materials, including in any distributed copy. Record provenance at the
   most precise practical level: upstream repository and path, pinned
   revision or exact artifact match, license and copyright notice, local
   modifications, and the basis for redistribution. Record acquisition
   route and date when known; label them unresolved when not known.
3. Verify that redistribution is permitted and that applicable license
   conditions are met before making third-party material public or
   publishing it. A source match or an MIT license found upstream does not,
   by itself, establish the local acquisition route, the original author's
   identity, or rights that have not been verified. Where rights remain
   unresolved, do not assert them; hold the material from public
   distribution pending review or remove it from that distribution.

### Keep licensing, adoption, and publication separate

Track three distinct questions:

| Status | Question answered |
| --- | --- |
| Licensing and provenance | What rights and obligations apply, and what evidence supports redistribution? |
| Adoption | Has Robe Land selected the resource as a canonical resource for use? |
| Publication | Has a specific version been approved for distribution, and where is it published? |

A license does not imply adoption or publication. Adoption does not establish
rights or authorize publication. Publication requires verified rights and
the applicable, separate approval process.

The accepted shared-resource publication ADR remains authoritative for
agents and skills: Engineering is the canonical owner, `.github` publishes
approved copies through a manual review and release process, and applicable
third-party licenses and attribution travel with published resources. This
ADR strengthens the organization-wide rights and provenance baseline; it
does not authorize publication, alter resource status, or relax that process.

## Consequences

Public-by-default visibility and a consistent licensing baseline make
Robe Land repositories easier to reuse. Requiring rights evidence and
preserved notices may delay distribution when provenance is incomplete;
that uncertainty must remain explicit rather than being resolved by
assumption.

This ADR establishes policy only. It does not itself change repository
visibility, apply licenses, alter copyright ownership, publish resources,
or begin repository-wide implementation.

