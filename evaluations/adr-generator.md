# Evaluation: ADR Generator

- **Status:** evaluating; recommendation awaiting approval.
- **Recommendation:** adapt before personal adoption. Do not install or
  replace the existing agent yet.
- **Reviewed:** 2026-11-21.

## Provenance

The local, untracked file is
`~/Projects/robe-event-platform/.github/agents/adr-generator.agent.md`.
Its SHA-256 is
`abbf07c6a768a21baa94a1aed858510c8038cb89866461d47ab64817e9f347ac`;
its Git blob is `c67998f747edfee178183c983d860c3c1e336f80`.
That blob exactly matches
[github/awesome-copilot's ADR Generator at commit 10622d5](https://github.com/github/awesome-copilot/blob/10622d5ce2a34784a94846b9a49ef712ce0c4b33/agents/adr-generator.agent.md).
The latest change reported for that upstream path was commit
`10622d5ce2a34784a94846b9a49ef712ce0c4b33` on 2025-11-02. Matching content
establishes an upstream candidate, not where the local download came from.
No local modifications relative to that blob were observed.

The matching upstream revision includes the
[MIT license](https://github.com/github/awesome-copilot/blob/10622d5ce2a34784a94846b9a49ef712ce0c4b33/LICENSE).
Its copyright and permission notice must accompany copies or substantial
portions, including a future adaptation. Confirm any additional provenance
or licensing requirements before redistribution.

## Read-only drafting-guidance test

Test input: the accepted
[ADR-0003: Persistence Independence](https://github.com/michael-robeson/robe-event-platform/blob/6ee32803c30335516782a35d3e313ea47eaecdda/docs/decisions/0003-persistence-independence.md),
the repository's ADR template and conventions, and the current set of ADR
files. This is a manual, read-only dry run of the agent's written steps,
not an invocation of the agent or evidence of its runtime compliance.
No ADR or new decision was created or changed.

As a drafting check, the agent's context/decision/consequences prompts can
capture ADR-0003's consumer-owned persistence, local transactions, and
independent progress. A useful positive consequence is independent
persistence mappings; a negative consequence is potentially incomplete
projections. A meaningful alternative is centralized generic persistence,
which the ADR discusses as a shared dependency rather than a requirement.
These are checks against the existing text, not new decisions or proof
that a generated draft preserves every nuance.

| Check | Repository expectation | Agent's written instruction | Result |
| --- | --- | --- | --- |
| Directory and numbering | `docs/decisions/`, with ADRs 0001–0004 already present | Search `docs/adr/`; if absent, start at 0001 | Fail: `docs/adr/` is absent, so following that step would restart numbering at 0001 instead of using the repository sequence. |
| Naming and template | `NNNN-short-title.md`; status/date followed by Context, Decision, Consequences | `adr-NNNN-...`, mandatory YAML metadata, coded sections and bullets | Fail: output format conflicts with the repository template. |
| Approval status | New proposals normally start Proposed; an existing accepted decision must not be silently rewritten | Defaults to Proposed unless specified; calls for generating and saving a new file | Partial: safe default for a new proposal, but no explicit protection against rewriting accepted ADRs or claiming approval. |
| Completeness | Meaningful rationale, alternatives, benefits and drawbacks, with open choices explicit | Requests context, rationale, alternatives, consequences and references | Useful, but mandatory counts and rejection reasons can encourage invented detail when evidence is missing. |

The agent also demands stakeholder names and a chosen decision before
drafting; an exploratory proposal may not yet have either. Its instruction
to ask for missing required inputs is safer than guessing, but it does not
explicitly accommodate unresolved choices. Its "repository state as source
of truth" guidance conflicts with its unconditional path and format rules.
The file declares no tools or hooks; omission of a tool list can leave tool
availability to the harness. It contains no executable script, but it
instructs the agent to create files and does not itself enforce read-only
or approval boundaries.

## Portability and next steps

The unmodified agent cannot reliably respect varying ADR paths, numbering,
templates, or accepted-decision boundaries: the written rules conflict with
Robe's conventions. A single adapted agent is a plausible alternative to
per-project copies, but its reliability is **not yet demonstrated**.

If adaptation is approved:

1. Discover each repository's ADR directory, template, existing numbers,
   instruction files, and statuses before drafting. Ask when ambiguous;
   never silently create a new ADR convention or overwrite an existing ADR.
2. Default new proposals to Proposed, preserve accepted records, and change
   status only on explicit authorization. Treat open choices as open and
   never invent rationale, stakeholders, or metrics to fill a checklist.
3. Use the existing template and naming rules; retain the upstream checklist
   as optional guidance rather than fixed section or item counts. Review
   effective tool access and require authorization for any file changes.
4. Verify with fresh sessions in multiple repositories, including conflicting
   templates, missing ADR conventions, existing accepted records, and
   explicit status instructions. Confirm discovery and inspect actual output
   and tool calls before adoption.

For the Copilot harness in VS Code, the documented personal agent location is
`~/.copilot/agents/` on the machine running the agent
([VS Code custom-agent reference](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference)).
The separate VS Code Local harness uses profile storage. Installation and
cross-project discovery have not been tested; no global installation or
agent rewrite was performed.
