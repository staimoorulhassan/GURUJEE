---
id: "008"
title: Foundation Tasks v2 Post-Clarification
stage: tasks
date: 2026-04-11
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: /sp.tasks
labels: ["tasks","android","termux","asyncio","textual","sqlite","keystore","pin","streaming","canonical-paths"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: history/adr/ADR-003-tui-daemon-single-process-architecture.md
  pr: null
files:
  - specs/001-gurujee-foundation/tasks.md
tests:
  - none
---

## Prompt

/sp.tasks

(Regenerated after /sp.clarify round 2 which added: FR-023 PIN prompt/lockout,
FR-015 streaming render contract, canonical config/data path split, 8-step setup wizard,
data/user_config.yaml, config/voice.yaml, data/soul_identity.yaml runtime path.)

## Response snapshot

Fully regenerated tasks.md for 001-gurujee-foundation with 49 tasks across 5 phases.
All tasks reflect post-clarification spec changes.

Key additions vs. prior generation (45 tasks):
- T007: Create config/voice.yaml (voice provider config, version-controlled)
- T011: keystore.py expanded with PIN lockout (3 attempts → 30s backoff), wipe() for forgot-PIN
- T015: __main__.py expanded with full PIN prompt flow (_prompt_pin, lockout display, forgot-PIN path)
- T016: conftest.py adds fake_user_config fixture
- T022: _step_keystore_pin() (new wizard step 5 — PIN setup + keystore initialization)
- T023: _step_ai_model() (writes data/user_config.yaml, previously implicit)
- T025: _step_daemons() expanded to copy agents/soul_identity.yaml → data/soul_identity.yaml
- T032: soul_agent.py updated to read data/soul_identity.yaml, emit CHAT_RESPONSE_COMPLETE with is_interrupted flag
- T035: user_agent.py updated to read data/soul_identity.yaml
- T038: chat_screen.py updated with full streaming render spec (blinking cursor, in-place append, [interrupted] suffix)
- T040: settings_screen.py updated to write data/user_config.yaml (not config/models.yaml)
- T048: Update data-model.md (add keystore_pin step, UserConfig entity, soul path)

Phase breakdown:
- Phase 1 Setup: T001–T009 (9 tasks — added config/voice.yaml T007)
- Phase 2 Foundational: T010–T016 (7 tasks — keystore lockout, loader user_config, main PIN prompt)
- Phase 3 US1: T017–T025 (9 tasks — 2 tests + 7 wizard impl including _step_keystore_pin and _step_ai_model)
- Phase 4 US2: T026–T041 (16 tasks — 4 tests + 12 impl with streaming render, data path updates)
- Phase 5 Polish: T042–T049 (8 tasks — added data-model.md update T048)

Parallel opportunities:
- Phase 1: T002–T009 all parallelizable after T001
- Phase 2: T011, T012, T014, T016 in parallel; T010 before T013/T015
- Phase 3 US1: T017 & T018 parallel; T019–T025 sequential (same wizard.py file)
- Phase 4 US2: T026–T029 parallel; T030, T031, T035, T036, T037 parallel;
  T038, T039, T040 parallel; T041 after screens
- Phase 5: T042, T043, T045, T046, T047, T048 parallel

MVP scope: Phase 1 + Phase 2 + Phase 3 (US1 setup wizard) = T001–T025 (25 tasks)

## Outcome

- ✅ Impact: 49 tasks covering full Phase 1 implementation with all post-clarification
  requirements: PIN UX (FR-023), streaming render (FR-015), canonical paths, 8-step wizard,
  data/user_config.yaml, config/voice.yaml, data/soul_identity.yaml runtime copy
- 🧪 Tests: n/a (task generation; test tasks are specified within tasks.md)
- 📁 Files: specs/001-gurujee-foundation/tasks.md
- 🔁 Next prompts: Begin implementation starting from T001 (project structure)
- 🧠 Reflection: The biggest structural change from v1 was adding _step_keystore_pin (T022)
  and _step_ai_model (T023) as explicit wizard tasks — previously implicit. The soul_identity
  path split (agents/ template vs data/ runtime) added 3 task updates across T025, T032, T035.
  The streaming render spec in T038 is the most complex UI task and deserves careful TDD.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Format validation PASS (all 49 tasks follow checkbox+ID+[P]+[USn]+description+path format); all 23 FRs from spec.md (FR-001 through FR-023) mapped to at least one task; phase structure correct
- Prompt variant (if applicable): N/A
- Next experiment: Begin T001 — create project package structure
