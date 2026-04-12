---
id: "001"
title: GURUJEE Communications Layer Spec
stage: spec
date: 2026-04-12
surface: agent
model: claude-sonnet-4-6
feature: 002-gurujee-comms
branch: 002-gurujee-comms
user: Taimoor
command: /sp.specify
labels: ["spec", "sip", "sms", "cron", "pjsua2", "elevenlabs", "phase2"]
links:
  spec: specs/002-gurujee-comms/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/002-gurujee-comms/spec.md (new)
tests: []
---

## Prompt

/sp.specify

New feature: 002-gurujee-comms
Branch: 002-gurujee-comms

Build the communications layer for GURUJEE:

US1 — SIP Calling:
GURUJEE answers incoming calls automatically using AI voice.
When a call comes in, it answers after 2 rings, transcribes the caller with 
Whisper, sends to Pollinations nova-fast, streams TTS response via ElevenLabs 
back into the call in real time. User can enable/disable auto-answer in settings.
Outgoing calls: user says "call Ali" in chat, GURUJEE dials the number.
Voice cloning: user can have GURUJEE answer in their own cloned voice.

US2 — SMS Auto-Reply:
GURUJEE reads incoming SMS via Termux:API polling every 30 seconds.
If sender is on the approved auto-reply list, AI generates a contextual reply
and sends it via termux-sms-send. User approves the auto-reply list in settings.

US3 — Scheduled Tasks (Cron Agent activation):
Cron agent was started dormant in Phase 1. Phase 2 activates it.
User says "remind me every morning at 8am to drink water" — AI parses this into
a cron expression, stores in data/cron_schedules.yaml, cron agent executes it.
Supports: reminders (TTS notification), auto-SMS, auto-call, run automation command.

SIP config: domain sip.suii.us — credentials from keystore only, never hardcoded.
SIP library: pjsua2 Python bindings compiled in Termux.

## Response snapshot

Created `specs/002-gurujee-comms/spec.md` with:

**3 user stories (all P1/P2):**
- US1: AI answers incoming SIP calls — 6 ACs (auto-answer, AI TTS loop, outgoing call,
  ElevenLabs fallback, STT failure handling)
- US2: AI auto-replies to approved SMS senders — 4 ACs (polling, reply, non-approved,
  add-to-list command)
- US3: Scheduled tasks via natural language — 5 ACs (parse to cron, TTS reminder,
  list jobs, SMS cron, corrupted schedule handling)

**15 Functional Requirements (FR-101–FR-115):**
- SIP: registration + retry (FR-101), auto-answer (FR-102), STT→AI→TTS loop (FR-103),
  outgoing calls (FR-104), ElevenLabs streaming + ACE fallback (FR-105), keystore-only
  credentials (FR-106)
- SMS: 30s polling (FR-107), auto-reply (FR-108), non-approved notification (FR-109),
  list management via chat (FR-110)
- Cron: job execution (FR-111), NL→cron parse (FR-112), CRUD via chat (FR-113)
- Health: SIP status in /health (FR-114), all events to automation.log (FR-115)

**7 Key Entities:** SIPSession, SMSMessage, CronJob, SIPConfig

**7 Success Criteria (SC-101–SC-107):**
- Call answered <5s (SC-101), TTS round-trip <5s (SC-102), SMS reply <90s (SC-103),
  cron parse accuracy 100% (SC-104), reminder fires within 60s (SC-105),
  idle RAM <80MB with SIP+SMS (SC-106), graceful pjsua2 absence (SC-107)

**Clarifications recorded:** pjsua2 compile assumption, Termux:API dependency,
ElevenLabs voice ID from Phase 1 keystore, one active call at a time.

## Outcome

- ✅ Impact: Phase 2 spec created — 3 user stories, 15 FRs, 7 SCs, 4 entities
- 🧪 Tests: No tests yet — awaiting /sp.plan and /sp.tasks
- 📁 Files: specs/002-gurujee-comms/spec.md
- 🔁 Next prompts: /sp.plan for 002-gurujee-comms (architecture: pjsua2 integration, SMS agent, cron activation, PWA settings extension)
- 🧠 Reflection: auto-call via cron deferred from Phase 2 to Phase 3 per clarification; SC-106 extends RAM ceiling to 80MB to account for pjsua2 library overhead (vs Phase 1's 50MB daemon)

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): spec template compliance PASS; all FRs testable PASS; no NEEDS CLARIFICATION placeholders remaining PASS
- Prompt variant (if applicable): combined with Phase 1 wrap-up in same session
- Next experiment (smallest change to try): /sp.plan for 002-gurujee-comms to design pjsua2 integration architecture
