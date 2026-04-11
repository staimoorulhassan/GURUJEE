---
id: "001"
title: GURUJEE Core Platform Spec
stage: spec
date: 2026-04-11
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-core
branch: 001-gurujee-core
user: Taimoor
command: /sp.specify
labels: ["spec","android","termux","ai-agent","autonomous","mobile"]
links:
  spec: specs/001-gurujee-core/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-gurujee-core/spec.md
  - specs/001-gurujee-core/checklists/requirements.md
  - history/prompts/001-gurujee-core/001-gurujee-core-spec.spec.prompt.md
tests:
  - none
---

## Prompt

Build GURUJEE — an autonomous AI agent Android application deployed via Termux on a non-rooted phone.

GURUJEE is a persistent AI companion that:

1. Has a named identity, personality, and self-narrative (Soul Agent).
2. Remembers everything across sessions (Memory Agent).
3. Can make and receive phone calls autonomously via SIP.
4. Can send and receive SMS automatically via Termux:API.
5. Runs scheduled tasks (Cron Agent).
6. Orchestrates complex multi-step tasks (Sub-Agent Orchestrator).
7. Automates the Android device via Shizuku (no root).
8. Has a modular Skills system (plug-and-play Python modules).
9. Has a modular Plugins system (extend core with new agents/panels/integrations).
10. Provides a minimal Textual TUI in Termux.
11. On first launch, guided setup from scratch.
12. Keeps all credentials encrypted locally.

## Response snapshot

Spec v1 written to `specs/001-gurujee-core/spec.md`. Branch `001-gurujee-core` created.

8 user stories (P1–P3), 34 functional requirements (FR-001–FR-034), 10 success criteria
(SC-001–SC-010), 6 edge cases, 8 key entities, and 7 explicit assumptions documented.
No NEEDS CLARIFICATION markers — all gaps resolved with informed defaults and documented
in the Assumptions section. Quality checklist at `specs/001-gurujee-core/checklists/requirements.md`
— all items pass.

## Outcome

- ✅ Impact: Full spec for GURUJEE core platform written; ready for `/sp.plan`
- 🧪 Tests: Independent test defined for each of the 8 user stories
- 📁 Files: specs/001-gurujee-core/spec.md, checklists/requirements.md
- 🔁 Next prompts: `/sp.clarify` (optional refinement) or `/sp.plan` (start architecture)
- 🧠 Reflection: Feature scope is very large (8 stories, 34 FRs). Consider asking user if
  they want to split into multiple features (e.g., Core + Calling + Automation) for phased
  delivery, or keep as one large feature and phase via task priorities.

## Evaluation notes (flywheel)

- Failure modes observed: create-new-feature.ps1 errored on positional arg (multi-word
  description needs quoting); branch and spec file were created before the error, so
  the workflow continued via agent-native file write.
- Graders run and results (PASS/FAIL): Quality checklist — all 12 items PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Scope split — ask user if calling/SMS/automation
  should be separate features to reduce plan/tasks scope.
