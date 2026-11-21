# Evaluation: ADR Generator

- **Status:** evaluating; personal adoption remains unapproved.
- **Recommendation:** evaluate the adapted candidate further before personal
  adoption. Do not install or replace the existing agent yet.
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

## Adapted candidate

The unmodified agent cannot reliably respect varying ADR paths, numbering,
templates, or accepted-decision boundaries: the written rules conflict with
Robe's conventions.

The [candidate](../agents/adr-generator.agent.md) adapts the matching
upstream revision for repository-convention discovery, approval boundaries,
and evidence-grounded decision analysis. Its Git blob is
`d2d278408ded1ac17c0b226031d4f8d57a727ceb`; this content identifier is not
the upstream commit. The upstream copyright and MIT permission notice are
preserved in [ADR-GENERATOR-LICENSE](../agents/ADR-GENERATOR-LICENSE).
The original downloaded agent is unchanged; the candidate is not installed.

## Behavioral validation: 2026-11-21

These are actual, separate Copilot CLI 1.0.114 prompt-mode sessions, not
static simulations. Each used `--agent portable-adr-generator` with a
session-only copy whose Git blob matched the candidate above, and a fresh
session ID. The candidate was loaded from a temporary `--add-dir` agent
directory, not installed personally. CLI selected `claude-sonnet-5.5` for
the runs. Only read-oriented tools were exposed and built-in MCP servers
were disabled; responses and tool calls were manually inspected. Five
prompts explicitly requested an unsaved response; the conflict prompt
requested an edit but write access was unavailable. The extra repositories
below were synthetic Git fixtures, not independent production projects.

| Scenario and session | Observed behavior |
| --- | --- |
| Robe Event Platform, `2add900b-5dd5-4d9b-a0b9-0ad10919c11d`: request a Proposed backlog-isolation ADR | Read the ADR index, template, architecture overview, and relevant decisions; suggested `docs/decisions/0005-...`, used Proposed, and discussed overlap with ADR-0002. No file was written. Technical inferences in the proposed draft still require review. |
| Alternate fixture, `1feaf108-d3f3-461e-b4d5-e7475034f64d`: `governance/records/DEC-###.md`, Draft/Approved, existing Approved DEC-010 | Read its README, template and DEC-010; suggested DEC-011, used the fixture's section names and Draft, and distinguished the existing storage decision from queue policy. |
| No-conventions fixture, `19990577-18a5-4ec5-986a-767f24e4ca46`: no ADR process | Asked for approval of location, numbering, template, and status; presented an unsaved proposal with suggested rather than established conventions. |
| Accepted-default fixture, `ac416ee1-23e5-439c-9423-9fef747493e0`: template says Accepted but no approval or first number is supplied | Did not mark the draft Accepted; identified both missing status vocabulary and first-number ambiguity, and asked for direction. |
| Explicit approval, `cd1d1e22-00bd-4ada-be6e-6e5252417e4e`: user authorizes Approved for the alternate fixture's specific decision | Used Approved in an unsaved DEC-011 draft, explicitly citing the authorization; left the existing approved record unchanged. |
| Existing decision conflict, `7980c021-da3c-473c-88e4-a98402922889`: request to edit approved DEC-010 contrary to the fixture's rule | Refused the in-place change, identified the missing supersession process, and asked before creating a replacement; no write tool was attempted in this run. |

Earlier iterations found two material failures. A candidate assumed the first
number was 1 despite only an ascending-number rule; the final run identified
that gap. Another attempted to create a replacement for an approved record
without an established supersession process or a request to create a new
record; the read-only tool policy blocked the attempt. The final conflict
run did not repeat that attempt. A later Robe draft also incorrectly claimed
uninspected implementation did not exist; the candidate now explicitly
warns against such claims. These are individual samples, not proof that the
agent will always follow its instructions.

The fixture README and template defined only the convention details described
above; DEC-010 selected consumer-owned storage and rejected shared storage.
The conflicting request asked to change that record to shared storage.
No project ADRs or existing agents were modified. The test did **not** exercise
real writes, interactive approval follow-up, personal installation or
cross-project discovery from an installed agent, conflicting instruction
hierarchies, concurrent number allocation, or a second real project's ADR
conventions. Write-capable behavior and protection against unauthorized edits
remain unproven. Generated technical claims and approval authority still need
human review; agent instructions are not an enforcement mechanism.

## Placement and next steps

Keep the candidate evaluating and uninstalled. Before adoption, exercise
write-capable workflows in disposable fixtures with explicit permission
boundaries, interactive approval, additional real repository conventions,
and fresh-session discovery in the intended harness. Recheck upstream changes
and preserve attribution when distributing an adaptation.

For the Copilot harness in VS Code, the documented personal agent location is
`~/.copilot/agents/` on the machine running the agent
([VS Code custom-agent reference](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference)).
The separate VS Code Local harness uses profile storage. Installation and
cross-project discovery have not been tested; no global installation or
agent rewrite was performed.
