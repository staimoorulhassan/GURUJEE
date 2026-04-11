---
id: "003"
title: Foundation Spec Clarifications Applied
stage: spec
date: 2026-04-11
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: /sp.clarify
labels: ["spec","clarification","memory","soul","setup","voice-clone","accessibility"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-gurujee-foundation/spec.md
  - specs/001-gurujee-foundation/checklists/requirements.md
tests:
  - none
---

## Prompt

Clarification answers for GURUJEE:

- AI fallback if Pollinations is unreachable: show error in TUI, queue the request and retry when connection restores
- Soul identity storage: JSON file at agents/soul_identity.json, editable by user in Settings
- Voice clone: user records 30-second sample in guided setup, cloned via ElevenLabs instant clone API
- Auto-answer opt-in: disabled by default, user enables in Settings > Calls > Auto-Answer
- Sub-agent max parallelism: 4 concurrent sub-agents, configurable in config/agents.yaml
- SMS auto-reply scope: only contacts in user's approved list (user configures in Settings > SMS)
- Memory database: SQLite at data/memory.db, auto-backs up weekly to data/backups/
- Automation accessibility: requires GURUJEE Accessibility Service APK companion to be installed (part of guided setup)
- Cron expressions: both natural language ("every morning at 8am") parsed by LLM AND raw cron syntax supported
- Plugin security: plugins run in restricted Python sandbox (importlib restrictions), user must approve each plugin

## Response snapshot

10 clarifications applied to spec. Phase 1 impacts:
- FR-005: soul path changed from data/soul.yaml → agents/soul_identity.json; editable via Settings
- FR-007/FR-008/Key Entities: memory DB path confirmed as data/memory.db
- FR-021 added: weekly auto-backup to data/backups/
- FR-001 updated: guided setup now includes Accessibility APK install + voice sample recording (optional step)
- FR-014 updated: AI retry is automatic when connection restores (no user re-send needed)
- FR-017 added: Settings panel with soul editing + Phase 2 placeholder settings
- US1 acceptance scenario 5 added: voice sample recording and voice ID storage
- US2 acceptance scenario 5 added: queued message auto-delivery on reconnect
- SC-009 added: queued message delivered within 5s of endpoint restore
- 2 new edge cases added: backup failure handling, voice sample skip path

Phase 2/3 forward references recorded in Clarifications section:
- auto-answer mechanism (Phase 2), SMS scope (Phase 2), cron dual syntax (Phase 2),
  sub-agent parallelism (Phase 3), plugin approval + sandbox (Phase 3).

## Outcome

- ✅ Impact: Spec updated with 10 clarifications; 22 FRs, 9 SCs, 7 edge cases, 8 assumptions
- 🧪 Tests: no code tests (spec artifact)
- 📁 Files: specs/001-gurujee-foundation/spec.md, checklists/requirements.md
- 🔁 Next prompts: /sp.plan for 001-gurujee-foundation
- 🧠 Reflection: Soul path changed from .yaml to .json — ensure future plan/tasks reference
  agents/soul_identity.json consistently.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Checklist — all items PASS (post-clarification)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): /sp.plan 001-gurujee-foundation
