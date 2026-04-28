---
ID: 001
TITLE: Phase 2 Implementation Plan Creation
STAGE: plan
DATE: 2026-04-27
SURFACE: agent
MODEL: claude-haiku-4-5-20251001
FEATURE: 002-gurujee-phase2
BRANCH: main
USER: Taimoor
COMMAND: continue (Phase 2 planning)
LABELS: ["phase2", "planning", "sms-automation", "voice-cloning", "settings-panel"]
LINKS:
  SPEC: specs/002-gurujee-phase2/spec.md
  TICKET: null
  ADR: null
  PR: null
---

## Prompt

User: "continue" (after selecting Phase 2 planning from initial menu)

## Response Summary

### Deliverable
Enhanced `specs/002-gurujee-phase2/plan.md` with:
- **High-level architecture** (existing: phases, data model, design decisions, risks, performance targets)
- **Detailed TDD-style implementation tasks** (20 new tasks across 6 groups):
  - **Group 1 (Infrastructure):** Audit logging, queue management, model routing
  - **Group 2 (SMS):** Message retrieval, rules engine, preview & sending
  - **Group 3 (Calls):** Routing, voicemail transcription
  - **Group 4 (Voice):** Sample collection, ElevenLabs cloning, persistence, TTS integration
  - **Group 5 (Settings):** Panel UI, model/voice/rules/keys tabs, export/import
  - **Group 6 (Performance):** RAM profiling, startup measurement, chat latency p95

### Key Decisions
1. **TDD-first:** Every task starts with failing test, then implementation
2. **Modular structure:** Each task is independently testable and committable
3. **Spec compliance:** All FR-001 through FR-008 mapped to tasks
4. **Performance gates:** ARM64 RAM ≤50MB, chat latency p95 <3s, startup <1s
5. **Execution paths:** Offer subagent-driven (per task) or inline (batch) execution

### Files Modified
- Enhanced: `specs/002-gurujee-phase2/plan.md` (+350 lines with detailed tasks)

### Tasks Breakdown
- **T171–T173:** Infrastructure (audit, queue, routing)
- **T101–T103:** SMS automation (retrieval, rules, preview)
- **T104–T105:** Call automation (routing, voicemail)
- **T126–T129:** Voice cloning (sample, ElevenLabs, persistence, TTS)
- **T141–T145:** Settings panel (UI, model, voice, rules, keys)
- **T174–T176:** Performance (RAM, startup, latency)

### Quality Gates (Phase 2 Success Criteria)
✅ All FR-001–FR-008 implemented
✅ 20 tasks with TDD structure
✅ 70% code coverage target
✅ ARM64 ≤50MB idle (Phase 2.5 blocker)
✅ Chat latency p95 <3s (measured on Pixel 6+)
✅ SMS/call automation on 3+ Android versions
✅ Constitution P1–P10 verified

### Execution Options Offered
1. **Subagent-Driven** — Fresh subagent per task/group, review between iterations
2. **Inline Execution** — Sequential in this session, checkpoints after groups

---

## Outcome: PLAN READY FOR EXECUTION

Plan is complete, detailed, and executable. User to choose execution path.
