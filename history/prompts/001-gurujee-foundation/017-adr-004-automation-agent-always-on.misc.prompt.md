---
id: "017"
title: ADR-004 AutomationAgent Always-On Lifecycle
stage: misc
date: 2026-04-12
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: /sp.adr automation-agent-always-on-lifecycle
labels: ["adr", "architecture", "agent-lifecycle", "constitution", "automation"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: history/adr/ADR-004-automation-agent-always-on-lifecycle.md
  pr: https://github.com/staimoorulhassan/GURUJEE/compare/001-gurujee-foundation
files:
 - history/adr/ADR-004-automation-agent-always-on-lifecycle.md (new)
 - .specify/memory/constitution.md (amended P7, version bump 1.1.0 → 1.1.1)
tests: []
---

## Prompt

/sp.adr automation-agent-always-on-lifecycle

Decision context: Constitution P7 classifies AutomationAgent as "on-demand"
(starts only when needed). The Phase 1 implementation runs it as always-on inside
the GatewayDaemon supervision loop, same as soul/memory/heartbeat.

Why it was implemented always-on:
The PWA architecture requires GURUJEE to respond to automation commands instantly
from the chat UI. If AutomationAgent had to cold-start on each request, the first
"open WhatsApp" command would have a 2-3 second delay while the agent initializes
its Shizuku connection. For a non-technical user, that feels broken.

Option A — Keep always-on (current implementation):
Pros: instant response, simpler supervision loop, Shizuku connection stays warm.
Cons: adds ~3-5MB idle RAM. Must verify P1 ceiling still holds.

Option B — On-demand with warm pool (lazy init, stays alive 5 min after last use):
Pros: saves RAM when automation is unused for long periods.
Cons: first command after idle has cold-start delay, more complex lifecycle code.

Option C — Revert to true on-demand per P7:
Pros: fully compliant with P7.
Cons: user-visible latency on every first automation command per session.

Decision: Option A — keep always-on, amend P7.
Rationale: The PWA-primary architecture (ADR-003) changed the UX contract.
Non-technical users expect instant response from a chat interface.
A 3-second delay on "open WhatsApp" violates the product promise even if it
satisfies the letter of P7. The RAM cost (~3-5MB) keeps us within the P1 ceiling.

P7 amendment required: Change AutomationAgent classification from
"on-demand" to "always-on" and add it to the supervised agent table.
Bump constitution to v1.0.1 (PATCH — clarification of existing principle).

Record as ADR-004. Update constitution.md to v1.0.1.

## Response snapshot

**Significance check**: Passed all three tests (impact on RAM budget + supervision loop,
three alternatives considered, cross-cutting scope across all feature phases).

**ADR-004 created**: `history/adr/ADR-004-automation-agent-always-on-lifecycle.md`
- Decision: AutomationAgent always-on under GatewayDaemon supervision
- Option A selected over Option B (warm pool) and Option C (true on-demand)
- Key rationale: ADR-003 PWA-primary UX contract; cold-start unacceptable for non-technical users
- RAM cost ~3–5MB idle; within P1 50MB ceiling

**Constitution amended** (1.1.0 → 1.1.1, PATCH):
- P7 always-on agents table: added `automation` row
- P7 on-demand agents table: removed `automation` row; `orchestrator` remains on-demand
- Added inline rationale note under the always-on table linking to ADR-004
- SYNC IMPACT REPORT updated with v1.1.1 changelog
- Previous 1.1.0 changelog preserved in comment block
- Version footer bumped: `**Version**: 1.1.1`

**Note on version**: User specified v1.0.1 but constitution was already at v1.1.0;
correct PATCH bump from v1.1.0 is v1.1.1 (semantic versioning).

## Outcome

- ✅ Impact: P7 constitution conflict (finding I2 from PHR-016) fully resolved
- 🧪 Tests: No test changes — ADR + constitution are documentation
- 📁 Files: ADR-004 created; constitution.md amended to v1.1.1
- 🔁 Next prompts: /sp.specify to add US3/US4/US5 and fix PWA framing in spec.md (findings I1, I3, U1)
- 🧠 Reflection: Version correction from v1.0.1 to v1.1.1 required — user was not tracking the 1.1.0 state; semantic versioning must always increment from current, not from an earlier base

## Evaluation notes (flywheel)

- Failure modes observed: version specified by user (v1.0.1) was lower than current (v1.1.0); corrected to v1.1.1
- Graders run and results (PASS/FAIL): ADR significance check PASS (all 3 criteria met); constitution amendment PASS (no placeholders, version coherent)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): /sp.specify for spec.md US3/US4/US5 gap (finding U1)
