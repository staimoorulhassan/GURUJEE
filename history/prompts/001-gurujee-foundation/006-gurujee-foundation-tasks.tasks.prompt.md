---
id: "006"
title: GURUJEE Foundation Tasks Generated
stage: tasks
date: 2026-04-11
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: /sp.tasks
labels: ["tasks","android","termux","asyncio","textual","sqlite","keystore","agents","tui","pytest"]
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

## Response snapshot

Generated tasks.md for 001-gurujee-foundation with 45 tasks across 5 phases, organized by user story
(US1: Guided Setup P1, US2: Conversational AI + Memory P1). All tasks follow strict checklist format
with Task IDs, parallelizability markers [P], and story labels [US1]/[US2].

Phase breakdown:
- Phase 1 Setup (T001–T008): 8 tasks — package dirs, pyproject.toml, requirements.txt, .gitignore,
  config/models.yaml, config/agents.yaml, agents/soul_identity.yaml, install.sh. All parallelizable
  after T001 (project init).
- Phase 2 Foundational (T009–T015): 7 blocking prereqs — config/loader.py (PyYAML+ruamel), 
  keystore/keystore.py (AES-256-GCM+PBKDF2), agents/base_agent.py (BaseAgent ABC+MessageBus+MessageType
  enum), daemon/gateway_daemon.py (GatewayDaemon+ordered startup soul→memory→heartbeat→user_agent→cron),
  ai/client.py (AsyncOpenAI+tenacity+allowlist+queue), __main__.py (TUI/headless/setup dispatch),
  tests/conftest.py (fixtures). Blocks both US1 and US2.
- Phase 3 US1 (T016–T022): 7 tasks — 2 test tasks (test_setup_wizard.py, test_keystore.py) then
  setup/wizard.py with all 7 FR-001 steps including Termux:Boot script creation, accessibility APK
  SHA-256 verification, and voice-clone consent prompt.
- Phase 4 US2 (T023–T038): 16 tasks — 4 test tasks (test_soul_agent, test_memory_agent,
  test_heartbeat_agent, test_ai_client), then memory/short_term.py (ConversationTurn deque(10)),
  memory/long_term.py (SQLite WAL CRUD), all 5 agent files (soul, memory, heartbeat, user_agent, cron),
  tui/theme.py, 3 TUI screens (chat, agent_status, settings), tui/app.py (Textual + run_worker).
- Phase 5 Polish (T039–T045): 7 tasks — RotatingFileHandler logging integration, P10 compliance pass
  (no bare-except, no string paths, pathlib.Path everywhere), 70% coverage run, TUI 80-col layout test,
  install.sh idempotency validation, data/.gitignore creation, quickstart.md update.

Parallel opportunities: T002–T008 all parallelizable; T016–T022 test tasks [P] before impl; 
T023–T026 test tasks [P] all parallelizable before their respective impl tasks.

MVP scope: Phase 1 + Phase 2 + Phase 3 (US1: working guided setup) = T001–T022 (22 tasks).

## Outcome

- ✅ Impact: 45 tasks created covering full Phase 1 implementation — project init, foundational
  infrastructure, setup wizard (US1), conversational AI + 5-agent daemon + TUI (US2), and polish.
  All tasks are immediately executable with precise file paths.
- 🧪 Tests: n/a (task generation; test tasks are specified within tasks.md)
- 📁 Files: specs/001-gurujee-foundation/tasks.md
- 🔁 Next prompts: Begin implementation following tasks.md in order; optionally run /sp.implement
  starting from T001 (project init)
- 🧠 Reflection: Organizing phases by user story (not by layer) was the right call — it gives each
  phase an independently testable outcome. Phase 2 Foundational correctly captures the 7 blocking
  prereqs that both US1 and US2 depend on, preventing wasted rework. The test-first ordering within
  each US phase ensures RED-GREEN discipline even though tests weren't explicitly requested.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Format validation PASS (all 45 tasks follow checkbox+ID+[P]+[USn]+description+path format); dependency graph PASS (no circular deps); coverage PASS (all 22 FRs from spec.md mapped to at least one task)
- Prompt variant (if applicable): N/A
- Next experiment: Begin T001 — create project package structure per plan.md
