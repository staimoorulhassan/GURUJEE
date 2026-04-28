# GURUJEE Phase 2: Technical Plan

**Date**: 2026-04-27  
**Status**: Draft  
**Target**: Q3 2026

---

## Architecture Overview

### Phases

**Phase 2.1 — SMS & Call Automation (Weeks 1–4)**
- Multi-turn SMS context handling
- Call transfer & voicemail (pjsua2 enhancement)
- Automation rules engine (`automation_rules.yaml`)
- Task: T101–T125

**Phase 2.2 — Voice Cloning & TTS (Weeks 5–7)**
- ElevenLabs voice cloning API integration
- Cloned voice persistence in keystore
- Voice sample recording in PWA Settings
- Task: T126–T140

**Phase 2.3 — PWA Settings Panel (Weeks 8–9)**
- Settings UI (model, voice, automation, keys, export)
- Settings state persistence
- Task: T141–T155

**Phase 2.4 — Multi-Model Orchestration (Weeks 10–12)**
- Agent model routing config (`agent_model_routing.yaml`)
- Runtime override via Settings
- Cost/latency optimization dashboard
- Task: T156–T170

**Phase 2.5 — Resilience & Observability (Weeks 13–16)**
- Queue management formalization (capacity, TTL, overflow)
- Audit logging (`audit.jsonl`)
- Performance metrics (RAM, latency, battery)
- ARM64 measurement gate
- Task: T171–T200

---

## Data Model

### New/Extended Entities

**automation_rules.yaml** (new file)

```yaml
rules:
  - id: rule-001
    type: "sms"
    trigger: "message"
    conditions:
      - contact: "+1-555-123-4567"  # exact phone
      - keyword_any: ["reminder", "schedule"]
      - time_range: "09:00-17:00"
    actions:
      - auto_reply: true
      - delay_seconds: 5
      - max_length: 160
      - fallback: "call_user"  # if AI fails, call user
    enabled: true

  - id: rule-002
    type: "call"
    trigger: "incoming"
    conditions:
      - caller_in_contacts: true
      - priority_tier: "vip"  # vip, normal, spam
    actions:
      - auto_answer: true
      - transfer_if_unavailable: true
      - voicemail_greeting: "ai_generated"
    enabled: true

  - id: rule-003
    type: "sms_blocklist"
    trigger: "message"
    conditions:
      - contact_regex: ".*spam.*"
      - keyword_any: ["unsubscribe"]
    actions:
      - discard: true
      - block_contact: false
    enabled: true
```

**agent_model_routing.yaml** (new file)

```yaml
agent_defaults:
  timeout_seconds: 30
  max_retries: 2

agents:
  soul:
    default_model: "anthropic/claude-opus-4-6"
    fallback_models: ["anthropic/claude-sonnet-4-6"]
    budget_tier: "premium"
    cost_per_1m_tokens: 15.0  # USD

  orchestrator:
    default_model: "anthropic/claude-sonnet-4-6"
    fallback_models: ["openai/gpt-4o-mini"]
    budget_tier: "standard"
    cost_per_1m_tokens: 3.0

  automation:
    default_model: "openai/gpt-4o-mini"
    fallback_models: ["google/gemini-1.5-flash"]
    budget_tier: "economy"
    cost_per_1m_tokens: 1.5

  # ... other agents
```

**soul_identity.yaml** (extended)

```yaml
name: GURUJEE
voice_id: null  # ElevenLabs cloned voice ID
voice_sample_hash: "sha256:abc123..."  # fingerprint of recorded sample
voice_cloned_at: "2026-05-10T14:32:00Z"
voice_clone_status: "ready"  # pending, processing, ready, failed
language_style: "friendly"
# ... other fields unchanged
```

**audit.jsonl** (new file)

Format: One JSON object per line

```json
{"timestamp": "2026-05-10T14:32:00.123Z", "action": "send_message", "resource": "chat", "user_id": "local", "change": {"to": "Alice", "text": "...", "model_used": "anthropic/claude-opus"}, "outcome": "success"}
{"timestamp": "2026-05-10T14:33:15.456Z", "action": "sms_auto_reply", "resource": "automation", "user_id": "local", "change": {"contact": "+1-555-123-4567", "reply_text": "...", "rule_id": "rule-001"}, "outcome": "success"}
```

### Data Storage Updates

| Entity | Storage | Access Pattern |
|--------|---------|-----------------|
| automation_rules | YAML file | Load at daemon start, watch for changes |
| agent_model_routing | YAML file | Load at daemon start, settable via PWA |
| audit trail | JSONL + archive | Append-only; archive every 90 days |
| voice_id | keystore (AES-256) | Retrieve on daemon start, use for all TTS |
| settings state | keystore | Encrypted; settable via PWA UI |

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        PWA Chat UI                           │
│                   (Settings Panel Tab)                       │
└────────────────────────┬────────────────────────────────────┘
                         │ WebSocket / REST
         ┌───────────────┴───────────────┐
         │                               │
    ┌────▼──────────────┐        ┌──────▼──────────┐
    │   FastAPI Server  │        │  Settings API   │
    │   (Port 7171)     │        │  Endpoints      │
    └────┬──────────────┘        └──────┬──────────┘
         │                              │
         │       ┌──────────────────────┴────────────────┐
         │       │                                       │
    ┌────▼─────────────────────────────────────────────▼──┐
    │              GatewayDaemon                           │
    │  ┌──────────────────────────────────────────────┐   │
    │  │ MessageBus (asyncio.Queue)                  │   │
    │  └──────────┬─────────────────────────────────┘   │
    │             │                                     │
    │  ┌──────────┴──────────┬────────────┬────────────┬┐ │
    │  │                    │            │            ││ │
    │ ┌▼──────────┐ ┌──────▼──┐ ┌──────▼──┐ ┌──────▼─┐│ │
    │ │soul agent │ │memory   │ │heartbeat│ │cron    ││ │
    │ └──────────┘ │agent    │ │agent    │ │agent   ││ │
    │              │         │ │         │ │        ││ │
    │              │         │ │         │ │        ││ │
    │              └─────────┘ └─────────┘ └────────┘│ │
    │                                                 │ │
    │  ┌─────────────────────────────────────────────┤ │
    │  │  automation agent (SMS/call handler)         │ │
    │  └─────────────────────────────────────────────┘ │
    │                                                   │
    │  ┌─────────────────────────────────────────────┐ │
    │  │ orchestrator agent (parallel tasks)         │ │
    │  └─────────────────────────────────────────────┘ │
    └───────────────────────────────────────────────────┘
         │                    │              │
         │                    │              │
    ┌────▼───────┐  ┌────────▼────┐  ┌─────▼──────────┐
    │ AI Provider │  │ Termux:API  │  │ SQLite DB      │
    │ (multi-model)  (SMS, calls)  │  (memory, audit) │
    └────────────┘  └─────────────┘  └────────────────┘
```

---

## Key Design Decisions

### D1: SMS Automation Threading

**Decision**: Implement smart thread detection (last message time + sender) rather than strict group threading.

**Rationale**:
- Termux:API provides message ID, timestamp, sender only (no thread ID)
- Smart threading replicates user expectation (same sender, <10 min gap = same conversation)
- Simpler than trying to infer threads from subject/body matching

**Tradeoff**: May mis-thread if same sender sends multiple unrelated messages in <10 min window. Mitigated by user ability to edit/block in UI.

### D2: Voice Cloning Async Background Job

**Decision**: Clone voice in background; don't block chat on first sample upload.

**Rationale**:
- ElevenLabs cloning is slow (30–60 seconds)
- User expects immediate Settings confirmation
- Cloning status polled by Settings UI; user notified when ready

**Tradeoff**: Slight delay before cloned voice is available. Mitigation: Show "Processing..." status; email notification when ready (future).

### D3: Audit Logging to Local JSONL

**Decision**: All audit logs stay on device (never cloud-synced by default).

**Rationale**:
- Constitution P4 requires secure secret handling; audit logs may contain PII
- Local-only preserves privacy; user must explicitly export for compliance/review
- JSONL format is human-readable, parseable, and compatible with downstream analytics

**Tradeoff**: Requires user to manage log retention (archive script provided). Mitigation: Automatic rolling window (90 days) per spec.

### D4: Queue Management — Max 100, FIFO Drop

**Decision**: Hard cap at 100 pending AI requests; drop oldest on overflow. All queued messages have equal priority (no priority tiers).

**Rationale**:
- Prevents unbounded memory growth on long outages
- 100 messages ≈ 5–10 min conversation at typical rate
- FIFO drop is predictable (oldest = least relevant context)
- Equal priority simplifies implementation; sufficient for MVP

**Tradeoff**: Long outages may lose some message context. Mitigation: Notify user, offer manual resend/retry. Priority routing deferred to Phase 3 if needed.

---

## Integration Points

### External APIs

| API | Phase 2 Usage | Fallback |
|-----|---------------|----------|
| ElevenLabs (voice cloning) | Clone voice from sample; use cloned ID for TTS | ACE TTS (on-device, no voice quality) |
| POLLINATIONS_API_KEY | Multi-turn model selection | Fallback to openai/gpt-4o-mini if unavailable |
| pjsua2 (SIP) | Incoming call detection, auto-answer, transfer | Disable call automation; voice-only fallback |
| Termux:API (SMS) | Send/receive SMS, log access | Disable SMS automation; manual sending only |

### Configuration Files

| File | Purpose | When Loaded | When Reloaded |
|------|---------|------------|---------------|
| automation_rules.yaml | SMS/call rules | Daemon startup | Watched (inotify) or Settings UI |
| agent_model_routing.yaml | Model selection per agent | Daemon startup | Settings UI override |
| security.yaml (P4) | Allowlist, security anchors | Daemon startup | Watched (inotify) |
| soul_identity.yaml | Voice ID, personality | Daemon startup | Settings UI update |

---

## Performance Targets & Measurement

### RAM Budget (P1 – ARM64)

| Component | Budget | Measurement Method |
|-----------|--------|-------------------|
| Daemon idle | ≤ 50 MB | memory-profiler, Termux device, 2–5 min idle |
| Chat UI active | ≤ 120 MB | Memory tab, DevTools |
| Voice activity | ≤ 200 MB | Peak during TTS/STT |

### Latency Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Chat message → AI response | < 3s p95 | Client JS Delta (send button → reply) |
| SMS trigger → auto-reply sent | < 10s p95 | Termux:API log timestamps |
| Incoming call → answer | < 1s p95 | pjsua2 event log |
| Settings save → applied | < 2s p95 | WebSocket ack timestamp |

### Measurement Plan

**Tools**:
- `memory-profiler` for RAM sampling (daily cron job)
- Client-side JS timestamp delta for chat latency
- Termux:API log parsing for SMS/call latency
- Custom Prometheus-compatible metrics endpoint (Phase 2.5)

**Sampling**:
- RAM: Every 10 minutes (logged to `data/metrics/ram.jsonl`)
- Chat latency: Per message (sampled 10%, logged to `data/metrics/chat.jsonl`)
- SMS latency: Per message (100%, logged to Termux:API integration)

---

## Deployment Strategy

### Android Version Testing

| Android Version | Device | Status | Notes |
|-----------------|--------|--------|-------|
| Android 13+ (ARM64) | Pixel 6+ | Primary | Target deployment |
| Android 12 | Generic ARM64 | Secondary | Fallback support |
| Android 11 | Generic ARM64 | Best-effort | May lose SMS permissions |
| Below 11 | N/A | Unsupported | Out of scope |

### Release Checklist

- [ ] All Phase 2.1–2.5 tasks completed
- [ ] ARM64 RAM measurement ≤ 50 MB (P1 gate)
- [ ] Chat latency < 3s p95 (measured on Pixel 6+)
- [ ] Code coverage ≥ 80%
- [ ] Constitution P1–P10 verified
- [ ] Security review passed
- [ ] Beta release to 10 testers
- [ ] Feedback integration (2-week cycle)
- [ ] Production release to GitHub

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Voice cloning slow | Background job; status UI; email notification |
| SMS delivery fails on some Android | Test all API levels; fallback to Dialog UI |
| RAM exceeds 50 MB | Profile early; cut features (voice, cron) if needed |
| ElevenLabs outage | Fast failover to ACE TTS; cached cloned voice |
| Audit log disk full | Auto-archive every 90 days; user warning at 80% |

---

## Clarifications

### Session 2026-04-28

- Q: Should queue messages have priority tiers or equal weight? → A: Equal priority; FIFO with no exceptions (simple, sufficient for MVP)
- Q: Is 50 MB ARM64 limit a hard blocker or target? → A: Hard blocker; cut features if exceeded (architectural commitment, P1 enforced)
- Q: Where should Settings state be persisted? → A: Browser localStorage (fast client-side, survives restart, user manages sensitive data encryption)
- Q: Automation rule evaluation: first match or all match? → A: All matching rules apply; accumulate actions in order (user responsible for conflict resolution)
- Q: Multi-turn SMS context window depth? → A: Last 10 messages (≈2–3 min conversation, balances context quality with token cost)

---

## Success Criteria for Phase 2 Completion

1. ✅ All FR-001–FR-008 requirements implemented
2. ✅ All 75 Phase 2 tasks (T101–T200) completed
3. ✅ ARM64 measurement confirms ≤ 50 MB idle
4. ✅ Chat latency < 3s p95 on real device
5. ✅ SMS/call automation tested on 3+ Android versions
6. ✅ Voice cloning integrated and working
7. ✅ PWA Settings panel complete and intuitive
8. ✅ Code coverage ≥ 80%
9. ✅ Constitution P1–P10 compliance verified
10. ✅ Beta feedback integration (≥3 rounds)

---

## Files to Create/Modify

**New Files**:
- `config/automation_rules.yaml`
- `config/agent_model_routing.yaml`
- `specs/002-gurujee-phase2/spec.md`
- `specs/002-gurujee-phase2/plan.md`
- `specs/002-gurujee-phase2/tasks.md`
- `data/audit.jsonl` (created on first action)
- `data/dlq.jsonl` (dead-letter queue, created on first failure)

**Modified Files**:
- `.specify/memory/constitution.md` (Phase 2 + Phase 3 forward references)
- `gurujee/daemon/gateway_daemon.py` (queue management)
- `gurujee/agents/automation_agent.py` (SMS/call rules engine)
- `gurujee/ai/client.py` (agent model routing)
- `src/pwа/index.html` (Settings panel)
- `tests/` (new test files for all Phase 2 features)

---

---

## Detailed Implementation Tasks (TDD Format)

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement these tasks sequentially. Each task follows TDD: write failing test → implement → pass → commit.

### Task Group 1: Infrastructure (Weeks 13–14 of Phase 2.5)

#### T171: Audit Logging System

**Files:**
- Create: `gurujee/audit/__init__.py`
- Create: `gurujee/audit/logger.py`
- Modify: `gurujee/memory/long_term.py` (add audit_log table)
- Create: `tests/test_audit_logger.py`

**Steps:**

- [ ] Write failing test: `test_audit_log_creation` — create entry, retrieve, assert fields
- [ ] Write failing test: `test_audit_log_retention_policy` — archive logs > 90 days
- [ ] Implement `AuditLogger` class: `log()`, `get_logs()`, `archive_old_logs()`, `export_logs()`
- [ ] Add audit_log table to memory.db schema
- [ ] Run tests: pytest tests/test_audit_logger.py -v
- [ ] Commit: "feat: add audit logging system with 90-day retention"

#### T172: Queue Management (Capacity, TTL, DLQ)

**Files:**
- Create: `gurujee/queue/__init__.py`
- Create: `gurujee/queue/manager.py`
- Create: `tests/test_queue_manager.py`

**Steps:**

- [ ] Write failing test: `test_queue_fifo_order` — add 3, get oldest
- [ ] Write failing test: `test_queue_overflow_eviction` — add 4 to cap-3, verify oldest dropped
- [ ] Write failing test: `test_queue_ttl_expiration` — wait > ttl, cleanup expires
- [ ] Write failing test: `test_dead_letter_queue` — move failed message to DLQ
- [ ] Implement `AIRequestQueue`: `add()`, `get()`, `size()`, `cleanup_expired()`, `move_to_dlq()`, `get_dlq()`
- [ ] Create SQLite tables: ai_request_queue, dead_letter_queue
- [ ] Run tests: pytest tests/test_queue_manager.py -v
- [ ] Commit: "feat: add queue management with capacity, TTL, dead letter queue"

#### T173: Model Routing Configuration

**Files:**
- Create: `config/agent_model_routing.yaml`
- Modify: `gurujee/ai/client.py` (add ModelRouter class)
- Create: `tests/test_model_routing.py`

**Steps:**

- [ ] Write failing test: `test_model_router_loads_config` — load YAML, check default models exist
- [ ] Write failing test: `test_model_router_fallback_chain` — get fallback list
- [ ] Write failing test: `test_model_router_budget_tier` — get budget tier per agent
- [ ] Create `agent_model_routing.yaml` with all 6 agents: soul, memory, user_agent, automation, cron, heartbeat
- [ ] Implement `ModelRouter` in ai/client.py: `get_default_model()`, `get_fallback_models()`, `get_budget_tier()`, `get_all_models()`
- [ ] Run tests: pytest tests/test_model_routing.py -v
- [ ] Commit: "feat: add per-agent model routing configuration"

---

### Task Group 2: SMS Automation (Weeks 1–4)

#### T101: SMS Message Retrieval & Context Building

**Files:**
- Create: `gurujee/communication/__init__.py`
- Create: `gurujee/communication/sms_handler.py`
- Create: `tests/test_communication_sms.py`

**Steps:**

- [ ] Write failing test: `test_sms_get_recent_messages` — retrieve last 10 SMS from contact
- [ ] Write failing test: `test_sms_build_context` — format 10-message history for AI prompt
- [ ] Write failing test: `test_sms_context_window_limit` — exclude messages beyond 10-message depth
- [ ] Implement `SMSHandler`: `get_recent_messages(limit=10)`, `build_context()`, `send_sms()`
- [ ] Support Termux:API path (/data/data/com.android.providers.telephony/databases/mmssms.db)
- [ ] **Context window:** Last 10 messages (≈2–3 min SMS conversation); optimizes token cost while maintaining conversational context
- [ ] Run tests: pytest tests/test_communication_sms.py -v
- [ ] Commit: "feat: add SMS retrieval and context building (10-message window)"

#### T102: SMS Automation Rules Engine

**Files:**
- Create: `config/sms_automation_rules.yaml`
- Modify: `gurujee/communication/sms_handler.py` (add rules methods)
- Modify: `tests/test_communication_sms.py` (add rules tests)

**Steps:**

- [ ] Write failing test: `test_sms_rules_allowlist_match` — exact/regex patterns
- [ ] Write failing test: `test_sms_rules_time_based` — active_hours evaluation
- [ ] Write failing test: `test_sms_rules_keyword_trigger` — keyword list matching
- [ ] Write failing test: `test_sms_rules_all_match_accumulate` — all matching rules' actions applied in order
- [ ] Create `sms_automation_rules.yaml` with 4 example rules (family, unknown, keywords, work hours)
- [ ] Implement in SMSHandler: `matches_rule()`, `evaluate_time_rule()`, `should_auto_reply()`, `collect_all_matching_rules()`
- [ ] **Rule Evaluation:** All matching rules are evaluated; actions from all matches are collected and applied in rule order
- [ ] **Conflict Resolution:** Contradictory actions (e.g., `discard: true` + `auto_reply: true`) from different rules result in user warning; user must refine rules
- [ ] Run tests: pytest tests/test_communication_sms.py -v
- [ ] Commit: "feat: add SMS automation rules (allowlist, keywords, time-based) with all-match semantics"

#### T103: SMS Preview & Delayed Sending

**Files:**
- Modify: `gurujee/communication/sms_handler.py` (add preview methods)
- Modify: `gurujee/server/routers/automate.py` (add SMS endpoints)
- Create: `tests/test_sms_preview.py`

**Steps:**

- [ ] Write failing test: `test_sms_preview_format` — format includes phone, message, delay
- [ ] Write failing test: `test_sms_send_with_delay` — enforce delay timing
- [ ] Implement in SMSHandler: `format_sms_preview()`, `send_sms_with_preview()`
- [ ] Add endpoints: POST `/api/sms/preview`, POST `/api/sms/confirm`
- [ ] Run tests: pytest tests/test_sms_preview.py -v
- [ ] Commit: "feat: add SMS preview and user-confirmable sending"

---

### Task Group 3: Call Automation (Weeks 1–4)

#### T104: Call Detection & Caller Routing

**Files:**
- Create: `gurujee/communication/call_handler.py`
- Create: `tests/test_communication_call.py`

**Steps:**

- [ ] Write failing test: `test_call_handler_lookup_contact` — find contact by phone
- [ ] Write failing test: `test_call_handler_priority_routing` — direct vs voicemail route
- [ ] Write failing test: `test_call_handler_voicemail_greeting` — generate context-aware greeting
- [ ] Implement `CallHandler`: `lookup_contact()`, `determine_route()`, `generate_voicemail_greeting()`, `record_call_log()`
- [ ] Run tests: pytest tests/test_communication_call.py -v
- [ ] Commit: "feat: add call detection and priority-based routing"

#### T105: Voicemail Transcription & Memory

**Files:**
- Modify: `gurujee/communication/call_handler.py` (add voicemail methods)
- Modify: `gurujee/memory/long_term.py` (add voicemail table)
- Create: `tests/test_voicemail.py`

**Steps:**

- [ ] Write failing test: `test_voicemail_transcription` — STT audio to text
- [ ] Write failing test: `test_voicemail_storage` — store in memory.db
- [ ] Implement in CallHandler: `transcribe_voicemail()` (uses faster-whisper), `store_voicemail()`, `get_voicemail_notifications()`
- [ ] Add voicemail table: id, phone_number, contact_name, transcript, audio_path, created_at
- [ ] Run tests: pytest tests/test_voicemail.py -v
- [ ] Commit: "feat: add voicemail transcription and memory storage"

---

### Task Group 4: Voice Cloning (Weeks 5–7)

#### T126: Voice Sample Collection (PWA + Keystore)

**Files:**
- Modify: `gurujee/server/static/index.html` (add settings icon)
- Modify: `gurujee/keystore/keystore.py` (add voice_id storage)
- Create: `tests/test_voice_sample.py`

**Steps:**

- [ ] Write failing test: `test_voice_sample_recording` — MediaRecorder blob capture
- [ ] Write failing test: `test_voice_sample_keystore_encryption` — store encrypted
- [ ] Add voice recording UI to PWA Settings tab (HTML5 MediaRecorder)
- [ ] Extend keystore to handle voice_id (AES-256-GCM)
- [ ] Run tests: pytest tests/test_voice_sample.py -v
- [ ] Commit: "feat: add voice sample recording with keystore encryption"

#### T127: ElevenLabs Voice Cloning Integration

**Files:**
- Create: `gurujee/voice/__init__.py`
- Create: `gurujee/voice/cloning.py`
- Create: `tests/test_voice_cloning.py`

**Steps:**

- [ ] Add to requirements.txt: `elevenlabs>=0.2.0`
- [ ] Write failing test: `test_elevenlabs_clone_voice` — POST audio, get voice_id
- [ ] Write failing test: `test_cloning_error_handling` — API failure recovery
- [ ] Implement `ElevenLabsCloner`: `clone_voice()` with retry logic (tenacity)
- [ ] Run tests: pytest tests/test_voice_cloning.py -v
- [ ] Commit: "feat: add ElevenLabs voice cloning integration"

#### T128: Persistent Voice Identity

**Files:**
- Create: `gurujee/voice/persistence.py`
- Modify: `gurujee/memory/long_term.py` (add voice_identity table)
- Create: `tests/test_voice_persistence.py`

**Steps:**

- [ ] Write failing test: `test_voice_identity_persistence` — save/load from keystore
- [ ] Write failing test: `test_voice_identity_fallback` — use default if unavailable
- [ ] Implement `VoiceIdentity`: `save()`, `load()`, `get_tts_voice()`
- [ ] Add voice_identity table: id, voice_id, cloned_at, model_version, fallback_voice
- [ ] Run tests: pytest tests/test_voice_persistence.py -v
- [ ] Commit: "feat: add persistent voice identity with fallback"

#### T129: TTS with Cloned Voice Integration

**Files:**
- Modify: `gurujee/ai/client.py` (extend TTS methods)
- Modify: `gurujee/agents/soul_agent.py` (use voice_id)
- Modify: `gurujee/agents/automation_agent.py` (use voice_id for SMS replies)
- Create: `tests/test_tts_voice_integration.py`

**Steps:**

- [ ] Write failing test: `test_tts_with_cloned_voice` — TTS uses voice_id parameter
- [ ] Write failing test: `test_tts_fallback_on_missing_voice` — default voice if voice_id unavailable
- [ ] Extend `AIClient.tts_stream()` to accept voice_id parameter
- [ ] Update soul_agent and automation_agent to retrieve voice_id and pass to TTS
- [ ] Run tests: pytest tests/test_tts_voice_integration.py -v
- [ ] Commit: "feat: integrate cloned voice into TTS streams with fallback"

---

### Data Persistence Strategy – Settings

Settings state (Model, Voice, Automation, Keys, About) are persisted in **browser localStorage**. This provides:
- Fast client-side read/write
- Survives browser restart
- No backend round-trip on settings access
- Trade-off: Lost if browser cache cleared; user responsibility to manage sensitive data (API keys, voice samples encrypted client-side)

Settings are loaded on PWA startup from localStorage and synced to daemon via WebSocket on change.

---

### Task Group 5: PWA Settings Panel (Weeks 8–9)

#### T141: Settings Panel UI Structure

**Files:**
- Create: `gurujee/server/static/settings.html`
- Create: `gurujee/server/static/settings.js`
- Create: `gurujee/server/static/settings.css`
- Modify: `gurujee/server/static/index.html` (add settings icon)
- Create: `tests/test_settings_ui.py`

**Steps:**

- [ ] Write failing test: `test_settings_panel_opens` — mock DOM, check modal visible
- [ ] Add ⚙️ settings icon to PWA header (index.html)
- [ ] Create settings.html with 5 tabs: Model, Voice, Automation, Keys, About
- [ ] Implement tab switching in settings.js
- [ ] Style with dark theme (settings.css) matching index.css
- [ ] Run tests: pytest tests/test_settings_ui.py -v
- [ ] Commit: "feat: add PWA settings panel with 5 tabs"

#### T142: Model Settings Tab

**Files:**
- Modify: `gurujee/server/static/settings.html`
- Modify: `gurujee/server/static/settings.js`
- Create: `gurujee/server/routers/settings.py` (add model endpoints)
- Create: `tests/test_settings_models.py`

**Steps:**

- [ ] Write failing test: `test_settings_get_available_models` — GET /api/settings/models
- [ ] Write failing test: `test_settings_set_default_model` — POST /api/settings/models
- [ ] Add HTML: dropdown list of models from agent_model_routing.yaml
- [ ] Display routing policy (default + fallbacks, budget tier)
- [ ] Implement endpoints: GET /api/settings/models, POST /api/settings/models
- [ ] Persist user choice to user_config.yaml
- [ ] Run tests: pytest tests/test_settings_models.py -v
- [ ] Commit: "feat: add model selection settings with routing policy"

#### T143: Voice Settings Tab

**Files:**
- Modify: `gurujee/server/static/settings.html`
- Modify: `gurujee/server/static/settings.js`
- Extend: `gurujee/server/routers/settings.py` (add voice endpoints)
- Create: `tests/test_settings_voice.py`

**Steps:**

- [ ] Write failing test: `test_voice_record_and_save` — record, save, retrieve
- [ ] Write failing test: `test_voice_cloning_status_polling` — check status (pending/processing/ready)
- [ ] Add HTML: Record/Stop/Play/Save buttons, status display
- [ ] Implement endpoints: POST /api/settings/voice/record, GET /api/settings/voice/status
- [ ] Trigger async cloning background job on save
- [ ] Run tests: pytest tests/test_settings_voice.py -v
- [ ] Commit: "feat: add voice recording and cloning status in settings"

#### T144: Automation Rules Tab

**Files:**
- Modify: `gurujee/server/static/settings.html`
- Modify: `gurujee/server/static/settings.js`
- Extend: `gurujee/server/routers/settings.py` (add rules endpoints)
- Create: `tests/test_settings_rules.py`

**Steps:**

- [ ] Write failing test: `test_rules_get_current` — GET /api/settings/automation/rules
- [ ] Write failing test: `test_rules_create` — POST /api/settings/automation/rules
- [ ] Write failing test: `test_rules_edit` — PUT /api/settings/automation/rules/{id}
- [ ] Write failing test: `test_rules_delete` — DELETE /api/settings/automation/rules/{id}
- [ ] Add HTML: rule list, create/edit form
- [ ] Implement CRUD endpoints for sms_automation_rules.yaml
- [ ] Validate rules before save
- [ ] Run tests: pytest tests/test_settings_rules.py -v
- [ ] Commit: "feat: add automation rules editor in settings"

#### T145: Keys & Export/Import

**Files:**
- Modify: `gurujee/server/static/settings.html`
- Modify: `gurujee/server/static/settings.js`
- Extend: `gurujee/server/routers/settings.py` (add export/import endpoints)
- Create: `tests/test_settings_export.py`

**Steps:**

- [ ] Write failing test: `test_settings_export_encrypted` — export configs as encrypted zip
- [ ] Write failing test: `test_settings_import_encrypted` — restore from encrypted zip
- [ ] Add HTML: API key input (masked), Export/Import buttons
- [ ] Implement POST /api/settings/keys (store POLLINATIONS_API_KEY)
- [ ] Implement POST /api/settings/export → returns .zip with soul_identity.yaml + rules.yaml (AES-256-GCM encrypted)
- [ ] Implement POST /api/settings/import → validates, restores from .zip
- [ ] Run tests: pytest tests/test_settings_export.py -v
- [ ] Commit: "feat: add keys and encrypted backup/restore"

---

### Task Group 6: Performance & Monitoring (Weeks 13–16)

#### T174: RAM Profiling & Alerting

**Files:**
- Create: `gurujee/profiling/__init__.py`
- Create: `gurujee/profiling/monitor.py`
- Create: `tests/test_profiling_monitor.py`

**Steps:**

- [ ] Write failing test: `test_memory_sampling` — sample RSS, log to metrics file
- [ ] Write failing test: `test_memory_threshold_alert` — alert if RSS > 2× baseline
- [ ] Implement `MemoryMonitor`: `sample_rss()`, `check_threshold()`, `get_baseline()`
- [ ] Setup daily cron task in cron_agent to sample RAM
- [ ] Verify on Termux ARM64: idle daemon ≤ 50 MB
- [ ] Log to data/metrics/ram.jsonl
- [ ] Run tests: pytest tests/test_profiling_monitor.py -v
- [ ] Commit: "feat: add RAM profiling with daily sampling and 2x alerts"

#### T175: Startup Time Measurement

**Files:**
- Modify: `gurujee/daemon/gateway_daemon.py` (add phase logging)
- Create: `tests/test_startup_timing.py`

**Steps:**

- [ ] Write failing test: `test_startup_phases_logged` — check boot logs for phase timestamps
- [ ] Add timing points in GatewayDaemon: [boot] start → config load → DB init → agents spawn → server ready
- [ ] Log each phase with elapsed time: [boot] Config loaded (245ms)
- [ ] Target: daemon ready < 1s, chat UI interactive < 2s
- [ ] Run tests: pytest tests/test_startup_timing.py -v
- [ ] Commit: "feat: add startup phase timing and measurement"

#### T176: Chat Latency Measurement (p95)

**Files:**
- Modify: `gurujee/server/routers/chat.py` (add latency tracking)
- Modify: `gurujee/server/static/app.js` (add client-side timestamps)
- Create: `tests/test_chat_latency.py`

**Steps:**

- [ ] Write failing test: `test_chat_latency_logging` — log send→response time
- [ ] Modify client to add timestamp to SSE messages (client_sent_ms)
- [ ] Server adds Server-Timing header on response start
- [ ] Calculate latency = response_received_ms - client_sent_ms
- [ ] Log all latencies to data/metrics/chat.jsonl
- [ ] Compute p95 percentile from sampled logs
- [ ] Target: p95 < 3 seconds
- [ ] Run tests: pytest tests/test_chat_latency.py -v
- [ ] Commit: "feat: add chat latency measurement and p95 tracking"

---

## Next Actions

1. **Create tasks.md** (Phase 2 detailed task breakdown) — now automated via this plan
2. **Prioritize ARM64 measurement** as Phase 2.5 gate (blocker for release)
3. **Plan ElevenLabs API spike** (2-day investigation for voice cloning integration)
4. **Define audit log schema** in detail (fields, retention, export format) — done above
5. **Design Settings panel UX** (mockups, user flows, accessibility)
