# GURUJEE Phase 2: Platform Expansion & Production Hardening

**Date**: 2026-04-27  
**Status**: Planning Phase  
**Version**: 1.0 (Draft)  
**Target Release**: Q3 2026

---

## Overview

GURUJEE Phase 2 builds on the Phase 1 MVP (core chat, memory, automation, PWA) to deliver:

1. **Complete Device Automation** – Full SMS/calling automation with smart threading and context awareness
2. **Voice Cloning & Advanced TTS** – Persistent voice identity with fallback strategies
3. **Production Deployment** – Full Android APK, hardened security, performance optimization
4. **Multi-Model Workflows** – Advanced agent orchestration and parallel task execution
5. **Compliance & Observability** – Audit logging, metrics, and dashboard support

---

## Functional Requirements

### FR-001: Advanced SMS Automation

**Context**: Phase 1 implemented one-shot SMS sending (US3). Phase 2 expands to multi-turn conversations.

**User Stories**:

**US-001**: As a non-technical user, I want GURUJEE to handle SMS conversations automatically so that I can receive intelligent replies without active participation.

- Acceptance Criteria:
  - GURUJEE monitors incoming SMS from configured contacts
  - Extracts context from message history (prior 10 messages, last 24 hours)
  - Generates contextually aware replies using `memory` agent + AI model
  - Sends reply automatically with user-configurable delay (0–60 seconds)
  - User can view all SMS exchanges in chat UI with edit/override capability before sending

**US-002**: As a power user, I want to define SMS automation rules (allowlist, blocklist, patterns) so that I control which messages trigger automation.

- Acceptance Criteria:
  - Rules defined in `data/automation_rules.yaml`
  - Contact allowlist / blocklist patterns (exact name, regex, group)
  - Keyword triggers (e.g., "reminder", "schedule")
  - Time-based rules (e.g., "auto-reply 9–17:00 only")
  - Priority ranking (first matching rule wins)

### FR-002: Advanced SIP Calling Automation

**Context**: Phase 1 supports receive-only SIP calls with auto-answer. Phase 2 adds smart call handling.

**User Stories**:

**US-003**: As a user, I want GURUJEE to manage call transfers and voicemail intelligently so that important calls reach me and others are handled gracefully.

- Acceptance Criteria:
  - Incoming call detection via pjsua2
  - Caller ID lookup (contacts) and whitelist/priority routing
  - Smart transfer: if user not in call, transfer to voicemail with context-aware greeting
  - Voicemail transcription via Whisper STT → memory agent for recall
  - Callback notification in chat UI with transcript

### FR-003: Voice Cloning & Persistence

**Context**: Phase 1 supports voice sample recording (optional). Phase 2 uses it for cloned voice synthesis.

**User Stories**:

**US-004**: As a user, I want GURUJEE to remember my voice and use it for all outbound TTS so that calls and messages feel personal.

- Acceptance Criteria:
  - Voice sample (30 seconds, consent-gated) recorded via PWA Settings → voice_id stored in keystore
  - ElevenLabs cloning API integration: POST `/v1/voice_cloning` with audio sample
  - Cloned voice_id persisted in `data/soul_identity.yaml`
  - All TTS (calls, messages, reminders) uses cloned voice if available; falls back to base model
  - Voiceprint matching: on receive, compare incoming voice to stored sample (optional, gated)

### FR-004: Multi-Model Orchestration

**Context**: Phase 1 routes models by agent. Phase 2 supports parallel inference and sophisticated routing.

**User Stories**:

**US-005**: As a developer, I want to define model routing policies per agent so that I can tune cost/latency tradeoffs.

- Acceptance Criteria:
  - New config file: `config/agent_model_routing.yaml`
  - Route format: `agent: { default_model, fallback_models, budget_tier }`
  - Agent example:
    ```yaml
    orchestrator:
      default_model: "anthropic/claude-opus-4-6"
      fallback_models: ["anthropic/claude-sonnet-4-6", "openai/gpt-4o-mini"]
      budget_tier: "premium"
    ```
  - Runtime override: PWA Settings allows user to pin model per agent
  - Metrics: track usage per agent/model for cost optimization

### FR-005: Queue Management & Resilience

**Context**: Phase 1 accepts message queue (bounds undefined). Phase 2 formalizes constraints.

**Requirements**:

- **Queue capacity**: Max 100 pending AI requests; FIFO eviction on overflow
- **TTL**: Messages expire after 60 seconds (configurable per queue type)
- **Overflow behavior**: Log warning, drop oldest message, notify user if >50 backlog
- **Recovery**: On reconnect, resend max 10 most recent; discard older (configurable)
- **Dead letter**: Persist failed messages to `data/dlq.jsonl` for replay/audit

### FR-006: PWA Settings Panel (Phase 1 Gap Closure)

**Context**: Phase 1 spec included FR-017 (Settings view) but not explicitly tasked. Phase 2 implements.

**User Stories**:

**US-006**: As a user, I want a Settings panel in the PWA so that I can configure model, voice, and automation without CLI.

- Acceptance Criteria:
  - Settings icon in PWA header → slide-out panel
  - **Model tab**: Select default model, view routing policies, set budget tier
  - **Voice tab**: Record voice sample (consent), test playback, view cloned voice status
  - **Automation tab**: Manage SMS/call rules, allowlist/blocklist, timeouts
  - **Keys tab**: POLLINATIONS_API_KEY entry (encrypted, stored in keystore)
  - **Export/Import**: Backup/restore `soul_identity.yaml` and rules
  - **About tab**: Version, constitution summary, GitHub link

### FR-007: Audit Logging & Compliance

**Requirements**:

- **Audit trail**: All user actions (send chat, trigger automation, modify settings) logged to `data/audit.jsonl`
- **Log format**: `{ timestamp, user_id, action, resource, change_summary, outcome }`
- **Retention**: 90-day rolling window; older logs archived to `data/audit-archive/`
- **Secure**: Audit logs never leave device unless explicitly exported (compliance gate)
- **Metrics export**: PWA dashboard shows action frequency, error rates per feature

### FR-008: Performance Optimization for Target Hardware

**Requirements**:

- **ARM64 RAM ceiling**: Idle daemon ≤ 50 MB (measure on Termux; P1 gate for release)
- **Startup time**: Daemon ready (<1 second), chat UI interactive (<2 seconds from app tap)
- **Chat latency**: Message send → AI response < 3 seconds at p95 (measured on real device)
- **Memory profiling**: Periodic (daily) RSS sampling; alert if 2× baseline
- **Battery**: Voice activity < 10% drain during idle; monitor via system profiler

---

## Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Idle RAM (ARM64) | ≤ 50 MB | memory-profiler on Termux device |
| Daemon startup | < 1 second | system clock / debug logs |
| Chat latency (p95) | < 3 seconds | client JS timestamp delta |
| SMS delivery latency | < 10 seconds | Termux:API log capture |
| Voice quality (MOS) | ≥ 3.5 | user survey + ElevenLabs metrics |
| Uptime (monthly) | ≥ 99.0% | system watchdog + heartbeat metrics |
| Code coverage | ≥ 80% | pytest --cov |
| Security review | Pass | constitution P4 audit + threat model |

---

## User Stories Summary

| ID | Title | Phase | Status |
|----|-------|-------|--------|
| US-001 | Multi-turn SMS automation | 2 | New |
| US-002 | SMS automation rules | 2 | New |
| US-003 | Smart call transfer & voicemail | 2 | New |
| US-004 | Voice cloning & persistence | 2 | New |
| US-005 | Multi-model orchestration config | 2 | New |
| US-006 | PWA Settings panel | 2 | Deferred from Phase 1 |

---

## Out of Scope (Phase 2)

- Native mobile app distribution via Google Play Store (Phase 3)
- Cloud sync / multi-device (Phase 3+)
- Advanced NLP (entity extraction, sentiment, intent) (Phase 3+)
- Generative video responses (Phase 3+)
- Third-party integrations (Slack, Teams, Discord) (Phase 3+)

---

## Success Criteria

1. ✅ All user stories implemented and tested
2. ✅ ARM64 RAM measurement confirms ≤ 50 MB
3. ✅ Chat latency measured at < 3 seconds p95
4. ✅ Audit log covers all user actions
5. ✅ SMS/call automation functional with fallback handling
6. ✅ Voice cloning integrated with ElevenLabs API
7. ✅ PWA Settings panel accessible and functional
8. ✅ Constitution P1–P10 compliance verified
9. ✅ Code coverage ≥ 80%
10. ✅ Security review passed (P4 audit)

---

## Dependencies & Assumptions

**External Dependencies**:
- ElevenLabs API availability for voice cloning (fallback to TTS only)
- pjsua2 library maintenance for SIP (monitor for security updates)
- Termux:API stable for SMS integration

**Assumptions**:
- User has internet access for AI inference (offline mode out of scope)
- ARM64 device performance similar to Pixel 6+ (reference device)
- Voice cloning is optional; not required for baseline functionality

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Voice cloning latency > 5s | User experience degrade | Async background cloning; sync status in UI |
| SMS delivery on some Android versions fails | Automation broken | Test on 5 Android versions; fallback to Dialog UI |
| ARM64 RAM exceeds 50 MB ceiling | P1 violation; Phase 2 blocker | Profile early; cut features if needed (voice, cron) |
| ElevenLabs outage | Calls drop to ACE TTS | Health check; fast failover; cache cloned voice |
