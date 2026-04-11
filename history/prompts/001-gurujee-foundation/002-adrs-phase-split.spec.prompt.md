---
id: "002"
title: ADRs and Phase Split Decision
stage: spec
date: 2026-04-11
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: /sp.adr skill-sandboxing-strategy + /sp.adr memory-retrieval-strategy + phase split
labels: ["adr","spec","phase-split","sandboxing","memory","architecture"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: history/adr/ADR-001-skill-sandboxing-strategy.md
  pr: null
files:
  - history/adr/ADR-001-skill-sandboxing-strategy.md
  - history/adr/ADR-002-memory-retrieval-strategy.md
  - specs/001-gurujee-foundation/spec.md
  - specs/001-gurujee-foundation/checklists/requirements.md
tests:
  - none
---

## Prompt

/sp.adr skill-sandboxing-strategy

Decision context: GURUJEE runs user-installed Skills as Python code on the user's phone.
Options: (1) subprocess isolation, (2) importlib with restricted builtins,
(3) multiprocessing with setrlimit. Recommend and record decision.

/sp.adr memory-retrieval-strategy

Decision context: Memory Agent retrieves relevant facts from SQLite for LLM injection.
No external embedding API, under 50MB RAM, under 100ms, SQLite only.
Options: (1) recency-only, (2) keyword/tag search, (3) TF-IDF, (4) hybrid recency + tag.
Recommend and record decision. Must not require sentence-transformers in v1.

Phase split: Rename 001-gurujee-core to 001-gurujee-foundation and trim spec to P1 only.
Phase 001 = foundation (setup, soul, memory, heartbeat, TUI, AI backend).
Phase 002 = comms (SIP, SMS, cron).
Phase 003 = automation (orchestrator, Shizuku, skills, plugins).

## Response snapshot

ADR-001 (Skill Sandboxing): Accepted — multiprocessing with setrlimit for third-party skills
(genuine crash isolation, keystore unreachable from child); restricted builtins for audited
built-in skills. subprocess IPC rejected (higher overhead, fragile protocol); importlib-only
rejected for third-party code (bypassable).

ADR-002 (Memory Retrieval): Accepted — Hybrid recency (last 10 turns in deque) + keyword/tag
search on SQLite (proper nouns + category taxonomy). Zero ML dependencies in v1. Forward-
compatible schema with nullable `embedding BLOB` column for future upgrade. TF-IDF rejected
(too slow without FTS5 for large stores); recency-only rejected (misses old facts).

Phase split: branch renamed 001-gurujee-core → 001-gurujee-foundation. spec.md rewritten for
P1 only: 2 user stories, 20 FRs, 8 SCs. Phases 2 and 3 defined for future /sp.specify runs.

## Outcome

- ✅ Impact: Two ADRs ratified; project split into 3 phases; Phase 1 spec finalized
- 🧪 Tests: n/a (architecture decisions)
- 📁 Files: history/adr/ADR-001, ADR-002; specs/001-gurujee-foundation/spec.md updated
- 🔁 Next prompts: /sp.plan for 001-gurujee-foundation
- 🧠 Reflection: Phase split was the right call — 34 FRs in one phase would produce an
  unmanageable plan. Phase 1 at 20 FRs is still large but tractable.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Spec quality checklist — all 12 items PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): /sp.plan 001-gurujee-foundation
