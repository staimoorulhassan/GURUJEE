---
id: "005"
title: ADR Single Process Architecture
stage: plan
date: 2026-04-11
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: /sp.adr tui-daemon-single-process-architecture
labels: ["adr","architecture","process-model","tui","daemon","p1","termux"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: history/adr/ADR-003-tui-daemon-single-process-architecture.md
  pr: null
files:
  - history/adr/ADR-003-tui-daemon-single-process-architecture.md
tests:
  - none
---

## Prompt

/sp.adr tui-daemon-single-process-architecture

Decision: GURUJEE TUI + daemon run as a single Python process. Textual App IS the process.
All agents are asyncio Tasks via app.run_worker(). --headless flag removes Textual for
Termux:Boot. Option A chosen over Option B (split process via Unix socket) because P1
50MB idle ceiling is a hard constraint; second Python interpreter costs ~25MB on ARM64.

## Response snapshot

ADR-003 created and accepted. Significance test: PASS (cross-cutting, P1-constrained,
will be revisited if web UI is added). Two alternatives considered:
- Option B (split process/Unix socket): rejected on P1 RAM grounds + IPC complexity
- Option C (multiprocessing per agent): rejected immediately (~75MB for 5 agents alone)

Revisit trigger documented: if Phase 3+ adds web UI, swap MessageBus internals to socket
delivery without structural agent changes. --headless mode already proves daemon-without-TUI
is viable.

ADR scan of plan.md: R-008 (SQLite WAL) already in ADR-002; R-009 (YAML split) below
significance threshold; R-004/R-006 are constitution-mandated; no new ADRs warranted.

## Outcome

- ✅ Impact: ADR-003 ratified; process architecture locked before implementation
- 🧪 Tests: n/a (architecture decision)
- 📁 Files: history/adr/ADR-003-tui-daemon-single-process-architecture.md
- 🔁 Next prompts: /sp.tasks for 001-gurujee-foundation
- 🧠 Reflection: The revisit trigger is important to document now. The MessageBus
  abstraction is the key design decision that makes the single→split migration localised.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Significance test PASS; all 4 checklist criteria met
- Prompt variant (if applicable): N/A
- Next experiment: /sp.tasks 001-gurujee-foundation
