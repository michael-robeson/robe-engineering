# Evaluation: ADR Generator

- **Status:** adopted for personal use.
- **Recommendation:** use the adopted portable implementation for personal ADR drafting,
  while retaining repository instructions and explicit authorization for
  accepted status.
- **Reviewed:** 2026-11-21.

## Provenance

The original local, untracked file was
`~/Projects/robe-event-platform/.github/agents/adr-generator.agent.md`; it is
preserved byte-for-byte at
`~/Projects/robe-engineering/agents/sources/robe-event-platform/adr-generator.agent.md`.
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

The previously committed Engineering version at
`agents/adr-generator.agent.md` was last changed in commit
`bc98c0ef7edc5af684d036b4ac4ba9cecb2c986c` and had Git blob
`907bdedcf5c4abeeb01ec4076d3f47e52ad21822`. It is preserved byte-for-byte at
`agents/sources/robe-engineering/adr-generator.agent.md` (SHA-256
`27d232f4d6dc3e536814fdec1f7d980176de817b48633dc42e14f3edf3e1922b`).
The adopted portable implementation is retained separately at
`agents/adopted/portable-adr-generator.agent.md`; its current Git blob and
SHA-256 match the Engineering original exactly.

The archived Platform candidate is a distinct file: its Git blob is
`c67998f747edfee178183c983d860c3c1e336f80`, rather than the Engineering
version's `907bdedcf5c4abeeb01ec4076d3f47e52ad21822`. The Platform candidate
matches the cited upstream revision; the adopted implementation also names
that upstream revision in its attribution. The available records establish
these content identities and differences, but do not establish whether either
local version was derived from the other. All three files are retained, and
no derivation direction is asserted.

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

The archived Platform agent cannot reliably respect varying ADR paths, numbering,
templates, or accepted-decision boundaries: the written rules conflict with
Robe's conventions.

The [adopted implementation](../agents/adopted/portable-adr-generator.agent.md)
provides repository-convention discovery, approval boundaries, and
evidence-grounded decision analysis. At this stage of the evaluation its
Git blob was `d2d278408ded1ac17c0b226031d4f8d57a727ceb`; this content
identifier is not the upstream commit. Its header attributes it to the cited
upstream revision. The adopted source was later updated to blob
`907bdedcf5c4abeeb01ec4076d3f47e52ad21822`, which matches the committed
Engineering original. The available evidence does not establish a derivation
relationship between the Engineering and Platform originals. The upstream
copyright and MIT permission notice are preserved in
[ADR-GENERATOR-LICENSE](../agents/adopted/ADR-GENERATOR-LICENSE). The archived
Platform candidate is unchanged. The adopted implementation was subsequently
installed for the controlled trial described below.

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

## Controlled personal trial: 2026-11-21

The six read-only sessions supported convention discovery and approval
handling in their sampled cases, but earlier iterations had assumed a first
number, attempted an unauthorized replacement, and made an unsupported claim
about uninspected implementation. These remain correctness risks rather than
proof of reliable behavior. To limit their impact in this trial, shell and
MCP tools were unavailable and each write-capable session was granted access
to one named new ADR file only. These restrictions apply to the trial
sessions, not automatically to future uses of the installed agent.

Before installation, two fresh sessions used the staged candidate and
write-capable tools in the synthetic alternate fixture:

- `d4e2eee0-ff74-4846-9cf7-8fd75dab78f0` created the authorized DEC-011
  with Draft status and the fixture template, without editing DEC-010.
- `559439e0-d4f0-4edf-a62b-eed98a89c145` was asked to edit approved
  DEC-010 contrary to the fixture's rule. With write permission for a
  potential new DEC-012 but not DEC-010, it made no write attempt, refused
  the edit, and asked before creating a replacement. This is one sampled
  conflict, not a general guarantee.

The candidate was then copied unchanged to
`~/.copilot/agents/portable-adr-generator.agent.md`; the upstream MIT notice
was copied alongside it as `ADR-GENERATOR-LICENSE`. This is the Copilot CLI
user-agent location, not the VS Code Local profile location. The installed
CLI trial agent's Git blob matches `d2d278408ded1ac17c0b226031d4f8d57a727ceb`.

Fresh Copilot CLI 1.0.114 session `2bd544fd-31dc-44d9-b506-571b81850279`,
opened from a Robe Event Platform worktree on
`feature/adr-generator-trial`, selected `--agent portable-adr-generator`
without a temporary agent directory. It identified the candidate and
upstream attribution and read the repository's ADR index, template, and
instructions. This verifies CLI discovery for this machine and harness, not
automatic discovery in other Copilot harnesses.

Fresh session `6f0e8c1b-5e2e-4056-a980-af82d96de10a` used the installed
agent to create a Proposed ADR on dead-letter remediation and replay. It
read the relevant accepted ADRs and architecture, and created only the
permitted new `docs/decisions/0005-dead-letter-remediation-and-replay.md`.
No accepted ADR was changed. The trial draft is uncommitted and unmerged in
the isolated worktree; it is not an approved platform decision.

The generated draft incorrectly described a dead-lettered message as an
unprocessed outcome, although ADR-0002 explicitly says a transaction may
commit before an acknowledgment is lost. This was not caused by missing
repository evidence or a conflicting instruction: the evidence was available
in the accepted ADR, but the agent made an unsupported inference and failed
to reconcile it with that evidence. The trial reviewer corrected the
statement to say processing is unknown, and removed an unsupported
requirement to settle every open detail before follow-up work. These were
manual changes after the agent invocation, not agent behavior. Other
technical claims and the proposed recovery direction still require review.

## Evidence-grounding review

The dead-letter error exposed a general gap: the candidate asked for factual
support but did not make it operationally distinct whether a statement
describes an implemented capability, an accepted decision, a proposed design,
or a future possibility. The candidate now requires the agent to classify
material claims by evidence and lifecycle state, verify implemented claims
against inspected sources, distinguish accepted intent from implementation,
attribute proposals, and leave incomplete or conflicting evidence unresolved.
This is general guidance, not a Pub/Sub-specific rule. The original error
remains evidence that instruction text alone does not ensure correct
reasoning.

The installed Copilot CLI trial copy was updated to match the new candidate
revision, `907bdedcf5c4abeeb01ec4076d3f47e52ad21822`.

Fresh Copilot CLI session `9db8fad5-8d73-4f56-bffd-04742cc81dd6` tested the
new evidence categories against the trial ADR, accepted ADRs, implementation,
tests, and development guide. It distinguished accepted design intent from
implementation evidence, identified ADR-0005 as Proposed, and left unresolved
items as future/open. It also correctly said a dead-lettered message's
processing outcome is unknown: ADR-0002 describes commit followed by lost
acknowledgment, while the implementation test verifies that redelivery is
duplicate-safe but does not exercise dead-lettering. The response noted its
limited code/config search rather than treating that search alone as proof of
non-existence. This is a successful sample in Copilot CLI, not evidence for
VS Code Local or a guarantee of consistent reasoning.

## VS Code Copilot Local validation

A successful fresh VS Code Copilot Local trial was completed for
ADR-0005, Dead-Letter Remediation and Replay. The session discovered and
invoked the personal candidate and produced a Proposed ADR draft in the
disposable Robe Event Platform worktree. The result was not promoted,
accepted, or merged. A retained session identifier and complete desktop
transcript were not available in the catalog evidence, so this record does
not infer behavior beyond the observed trial.

The trial retained the distinction between accepted architectural direction,
implemented capabilities, tested behavior, and proposed functionality:

- **Accepted direction:** ADR-0002 establishes at-least-once delivery,
  independent push consumers, bounded retries, and a dead-letter topic
  approach. Its thresholds, ownership, visibility, replay, and operational
  procedures remain open.
- **Implemented capability:** the local Compose Pub/Sub bootstrap creates
  the topic and push subscriptions but does not configure a dead-letter
  policy. The item and audit consumers provide HTTP acknowledgment and
  idempotent persistence, but no remediation or replay implementation.
- **Tested behavior:** end-to-end tests verify retry after a database outage,
  duplicate-safe redelivery after a lost post-commit response, and independent
  consumer outcomes. They do not exercise Pub/Sub dead-letter forwarding or
  replay.
- **Proposed functionality:** ADR-0005 proposes human-controlled,
  consumer-scoped diagnosis and replay principles. It remains Proposed and
  was not implemented.

The trial also preserved unresolved architecture questions: dead-letter topic
and subscription ownership; maximum delivery attempts and backoff; alert and
retention thresholds; remediation and replay authorization; replay tooling;
handling permanently unprocessable events and missed forwarding; sensitive
payload controls; environment differences; and cloud integration validation.
The local Pub/Sub emulator does not establish production GCP or Cloud SQL
behavior.

This result verifies the candidate in VS Code Copilot Local for this single
trial. It is not proof of all future responses, and it does not establish
unrestricted write safety, interactive approval behavior, or discovery in
every future profile or VS Code/Copilot configuration.

The VS Code reference states that Local user agents use VS Code profile
storage, separate from `~/.copilot/agents/`; the candidate also has a Copilot
CLI location. The harness's planned deprecation makes future availability
uncertain. Keep the agent source canonical in this repository and preserve
the upstream attribution and adapted revision.

## Placement and next steps

Adopt the implementation for personal use while keeping repository instructions,
accepted decisions, and explicit authorization authoritative. The canonical
adapted source is
`~/Projects/robe-engineering/agents/adopted/portable-adr-generator.agent.md`;
the upstream MIT attribution is preserved alongside it. Controlled personal
installations are recorded at `~/.copilot/agents/portable-adr-generator.agent.md`
and `~/.copilot/agents/ADR-GENERATOR-LICENSE`.

Verified environments are Copilot CLI and VS Code Copilot Local. The evidence
records a Copilot CLI discovery and drafting trial and a successful VS Code
Copilot Local ADR-0005 trial. It does not claim verification of write safety
in other harnesses or of every repository convention.

For the Copilot harness in VS Code, the documented personal agent location is
`~/.copilot/agents/` on the machine running the agent
([VS Code custom-agent reference](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference)).
