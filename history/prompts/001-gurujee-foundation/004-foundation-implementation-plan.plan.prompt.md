---
id: "004"
title: GURUJEE Foundation Implementation Plan
stage: plan
date: 2026-04-11
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: /sp.plan
labels: ["plan","android","termux","asyncio","textual","sqlite","keystore","agents"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: history/adr/ADR-001-skill-sandboxing-strategy.md
  pr: null
files:
  - specs/001-gurujee-foundation/plan.md
  - specs/001-gurujee-foundation/research.md
  - specs/001-gurujee-foundation/data-model.md
  - specs/001-gurujee-foundation/quickstart.md
  - specs/001-gurujee-foundation/contracts/message-bus.md
  - specs/001-gurujee-foundation/contracts/keystore-api.md
  - specs/001-gurujee-foundation/contracts/agent-base-interface.md
  - CLAUDE.md
tests:
  - none
---

## Prompt

Tech stack for Phase 1 — GURUJEE Foundation:
- Python 3.11+ inside Termux on Android ARM64
- AI: openai Python SDK 1.x, base_url=https://gen.pollinations.ai/v1, api_key=""
- TUI: Textual 0.47+ — Chat and Agent Status screens
- Color scheme: bg #0a0a0a, primary amber #f0a500, accent orange #ff6b00
- Guided setup wizard: Rich library
- Memory retrieval: hybrid recency-10 + keyword/tag SQLite (ADR-002)
- Keystore: cryptography AES-256-GCM, PBKDF2-HMAC-SHA256 device fingerprint salt
- Config: PyYAML + ruamel.yaml (soul_identity.yaml only)
- Database: sqlite3 stdlib, WAL mode, no ORM
- Logging: RotatingFileHandler 5MB × 3
- Daemon: asyncio in gateway_daemon.py, agents as Tasks, asyncio.Queue messaging
- Agent order: soul → memory → heartbeat → user_agent → cron dormant
- Termux:Boot auto-start
- Tests: pytest + responses, 70% coverage

## Response snapshot

Phase 0 (research.md): 10 decisions resolved — single-process architecture (R-007 saves
~25MB RAM), SQLite WAL single-writer (R-008), ruamel.yaml for soul_identity only (R-009),
Termux:Boot ~/.termux/boot/ confirmed (R-005), AsyncOpenAI custom base_url confirmed (R-006).

Phase 1 (design): 7 artifacts produced — plan.md, research.md, data-model.md (8 entities),
quickstart.md, contracts/message-bus.md (12 message types), contracts/keystore-api.md,
contracts/agent-base-interface.md. Constitution check: all P1–P10 PASS. Agent context
(CLAUDE.md) updated with tech stack.

Source structure: `gurujee/` package with agents/, daemon/, tui/, setup/, keystore/,
memory/, ai/, config/. Data in `data/` (gitignored). Config in `config/` and `agents/`.

## Outcome

- ✅ Impact: Full implementation plan for Phase 1; all design artifacts ready for /sp.tasks
- 🧪 Tests: pytest setup defined; conftest.py fixtures planned; 70% coverage target
- 📁 Files: 7 spec artifacts + CLAUDE.md updated
- 🔁 Next prompts: /sp.tasks to generate tasks.md
- 🧠 Reflection: Single-process TUI+daemon (R-007) is the most important design decision —
  it keeps idle RAM well within the 50MB P1 ceiling and simplifies the codebase significantly.
  The ruamel.yaml split (R-009) is a small but important detail for user experience.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Constitution Check P1–P10 all PASS
- Prompt variant (if applicable): N/A
- Next experiment: /sp.tasks 001-gurujee-foundation
