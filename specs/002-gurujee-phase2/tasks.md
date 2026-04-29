# GURUJEE Phase 2: Task Breakdown

**Total Tasks**: 100 (T101–T200)  
**Phases**: 5 (2.1–2.5)  
**Estimated Duration**: 16 weeks  
**Status**: Planning

---

## Task Structure

**Format**: `T### [P] Description`
- `[P]` = Parallel-executable task (no blocking dependencies on other tasks within same phase)
- Task IDs: Grouped by phase (2.1: T101–T125, 2.2: T126–T140, etc.)

---

## PHASE 2.1 — SMS & Call Automation (Weeks 1–4, Tasks T101–T125)

### SMS Automation Core (T101–T110)

- **T101** — Create `config/automation_rules.yaml` schema and validator
  - Input: spec.md FR-001 rule examples
  - Output: `config/automation_rules.yaml.schema` (JSON Schema)
  - Acceptance: Schema validates all FR-001 examples; rejects invalid rules
  - Tests: `tests/config/test_automation_rules_schema.py`

- **T102 [P]** — Design automation rule data model (Pydantic)
  - Input: schema from T101
  - Output: `gurujee/models/automation.py` with classes: `SMSRule`, `CallRule`, `RuleCondition`, `RuleAction`
  - Acceptance: All rule examples from spec instantiate correctly
  - Tests: `tests/models/test_automation.py`

- **T103** — Implement rule loader & file watcher
  - Input: `config/automation_rules.yaml`
  - Output: `gurujee/config/rules_loader.py` with `RulesLoader` class
  - Acceptance: Detects file changes in <100ms; reloads without daemon restart
  - Tests: `tests/config/test_rules_loader.py`

- **T104 [P]** — Implement SMS message fetch from Termux:API
  - Input: Termux:API `/messages/list` (requires API permission)
  - Output: `gurujee/integrations/termux_sms.py:fetch_sms_messages(limit=50)`
  - Acceptance: Returns list of `SMSMessage(id, timestamp, sender, body, thread_id)` objects
  - Tests: `tests/integrations/test_termux_sms.py` (mocked Termux:API)

- **T105 [P]** — Implement SMS thread context extraction (10-message window)
  - Input: SMS history from T104
  - Output: `gurujee/automation/sms_context.py:extract_thread_context(sender, message_limit=10)`
  - Acceptance: Returns **last 10 messages** from sender (clarification Q5); formats as string for AI; excludes messages >24h old
  - Tests: `tests/automation/test_sms_context.py` (verify limit enforced, respects age filter)

- **T106** — Implement rule matching engine (all-match semantics)
  - Input: `SMSMessage`, loaded rules from T103
  - Output: `gurujee/automation/rules_engine.py:match_rules(message) -> List[Rule]`
  - Acceptance: **Returns ALL matching rules** (clarification Q4, not just first); correctly evaluates contact patterns, keywords, time ranges; detects conflicts (e.g., `discard: true` + `auto_reply: true`) and warns user
  - Tests: `tests/automation/test_rules_engine.py` (verify all-match behavior, conflict detection)

- **T107 [P]** — Implement AI reply generation (soul agent integration)
  - Input: SMS message, thread context, AI model
  - Output: `gurujee/automation/sms_responder.py:generate_reply(message, context) -> str`
  - Acceptance: Calls soul agent; returns reply ≤ 160 chars; handles AI failures gracefully
  - Tests: `tests/automation/test_sms_responder.py`

- **T108** — Implement SMS sending via Termux:API
  - Input: Recipient, reply text
  - Output: `gurujee/integrations/termux_sms.py:send_sms(number, text) -> bool`
  - Acceptance: Sends message; returns success/failure; logs to audit trail
  - Tests: `tests/integrations/test_termux_sms.py`

- **T109** — Integrate SMS automation into automation agent
  - Input: automation_agent.py, all T101–T108 modules
  - Output: Extended automation agent with SMS job loop (poll every 10 seconds)
  - Acceptance: Agent starts, polls SMS, matches rules, generates replies, sends; logs all actions
  - Tests: `tests/agents/test_automation_agent_sms.py` (integration)

- **T110** — Add SMS automation to PWA chat UI (display auto-replies)
  - Input: Audit trail (`sms_auto_reply` action)
  - Output: Chat UI tab showing "SMS replies sent today" with timestamps, contacts, text, rule matched
  - Acceptance: UI updates in real-time; user can view/edit/block automations
  - Tests: `e2e/test_pwa_sms_display.py`

### Call Automation Core (T111–T120)

- **T111** — Enhance pjsua2 SIP handler for call routing
  - Input: pjsua2 event loop (phase 1)
  - Output: `gurujee/integrations/sip_handler.py:handle_incoming_call(caller_id) -> action`
  - Acceptance: Detects caller priority (vip/normal/spam from contacts); returns action (answer/transfer/voicemail)
  - Tests: `tests/integrations/test_sip_handler.py` (mocked pjsua2)

- **T112 [P]** — Implement smart transfer logic
  - Input: Call event, user availability, voicemail settings
  - Output: `gurujee/automation/call_transfer.py:route_call(caller, user_available) -> action`
  - Acceptance: If user not available, transfers to voicemail; logs action
  - Tests: `tests/automation/test_call_transfer.py`

- **T113** — Implement voicemail recording & transcription
  - Input: Audio stream (pjsua2), Whisper model
  - Output: `gurujee/automation/voicemail.py:record_and_transcribe(call) -> str`
  - Acceptance: Records audio; transcribes via Whisper tiny.en; stores transcript
  - Tests: `tests/automation/test_voicemail.py`

- **T114 [P]** — Store voicemail in memory agent
  - Input: Voicemail transcript, caller info
  - Output: `memory.add_entry(type="voicemail", caller=..., transcript=..., timestamp=...)`
  - Acceptance: Memory agent stores and indexes voicemail for later recall
  - Tests: `tests/agents/test_memory_agent_voicemail.py`

- **T115** — Implement call automation rules (T111–T114 integration)
  - Input: Loaded rules from T103 (call type rules)
  - Output: automation agent extended with call loop (polling SIP events)
  - Acceptance: Agent detects incoming calls, matches rules, executes actions (answer/transfer/voicemail)
  - Tests: `tests/agents/test_automation_agent_calls.py` (integration)

- **T116 [P]** — Add call status to PWA UI
  - Input: Automation agent call logs
  - Output: PWA panel showing "Calls today: 5 answered, 2 transferred to voicemail"
  - Acceptance: Real-time call counter; user can view voicemail transcripts
  - Tests: `e2e/test_pwa_call_display.py`

- **T117 [P]** — Implement call & SMS fallback behavior
  - Input: Failed AI generation, timeout, API error
  - Output: `gurujee/automation/fallback.py` with strategy: call user / send manual notification
  - Acceptance: On automation failure, system notifies user via chat or callback; graceful degradation
  - Tests: `tests/automation/test_fallback.py`

- **T118 [P]** — Create automation_rules.yaml with example SMS/call rules
  - Input: Spec FR-001, FR-002
  - Output: `config/automation_rules.yaml` with 3–5 realistic examples
  - Acceptance: File validates against schema; examples match spec user stories
  - Tests: Manual review + T101 schema validation

- **T119** — Integration test: SMS automation end-to-end
  - Input: Mocked Termux:API, sample SMS, rules file
  - Output: Test suite in `tests/integration/test_sms_e2e.py`
  - Acceptance: Receive SMS → match rule → generate reply → send SMS; verifies audit log
  - Tests: Full flow with mocks

- **T120** — Integration test: Call automation end-to-end
  - Input: Mocked pjsua2, sample incoming call, rules file
  - Output: Test suite in `tests/integration/test_call_e2e.py`
  - Acceptance: Receive call → route → transfer to voicemail → transcribe; verifies memory
  - Tests: Full flow with mocks

---

## PHASE 2.2 — Voice Cloning & TTS (Weeks 5–7, Tasks T121–T150)

### Voice Sample Recording (T121–T125)

- **T121** — Design voice sample recording UI in PWA Settings
  - Input: spec.md FR-003 US-004
  - Output: Settings panel mockup (Figma or ASCII) showing:
    - Record button (15–30 second limit)
    - Playback button
    - Status indicator (pending/processing/ready/failed)
  - Acceptance: Design reviewed; accessibility (ARIA) confirmed
  - Tests: Manual design review

- **T122** — Implement voice sample recording endpoint (FastAPI)
  - Input: WebSocket audio stream from PWA
  - Output: `gurujee/api/voice.py:POST /voice/record` accepting audio blob
  - Acceptance: Stores audio to `data/voice_sample.wav` (AES-256 encrypted in keystore)
  - Tests: `tests/api/test_voice_endpoint.py`

- **T123 [P]** — Implement voice fingerprint hashing (optional Phase 2)
  - Input: Voice sample audio
  - Output: `gurujee/voice/fingerprint.py:compute_fingerprint(audio) -> str` (SHA-256)
  - Acceptance: Hash matches across same sample; differs for different speakers
  - Tests: `tests/voice/test_fingerprint.py`

- **T124** — Implement playback endpoint (test recorded sample)
  - Input: Stored voice sample
  - Output: `gurujee/api/voice.py:GET /voice/sample` serving audio blob
  - Acceptance: PWA can playback recorded sample for user verification
  - Tests: `tests/api/test_voice_endpoint.py`

- **T125** — Integrate voice recording into PWA Settings (T121–T124)
  - Input: Voice recording design, endpoints
  - Output: Settings "Voice" tab with record/playback/status flow
  - Acceptance: User can record sample, hear playback, see processing status
  - Tests: `e2e/test_pwa_voice_recording.py`

### Voice Cloning Integration (T126–T145)

- **T126** — Design ElevenLabs voice cloning API integration
  - Input: ElevenLabs API docs, spec.md FR-003
  - Output: Architecture doc: `docs/adr/voice-cloning-async.md`
  - Acceptance: Design addresses async processing, fallback, caching
  - Tests: Design review

- **T127** — Implement ElevenLabs client class
  - Input: API credentials from keystore, voice sample
  - Output: `gurujee/integrations/elevenlabs.py:ElevenLabsClient` with methods:
    - `clone_voice(sample_path) -> voice_id` (async)
    - `synthesize(text, voice_id) -> audio_stream` (streaming)
  - Acceptance: Authenticates correctly; handles rate limits; has fallback
  - Tests: `tests/integrations/test_elevenlabs.py` (mocked)

- **T128** — Implement async voice cloning job
  - Input: Voice sample, ElevenLabs client
  - Output: `gurujee/voice/cloning_job.py:CloneJob` with status tracking
  - Acceptance: Starts clone in background; stores status (pending/processing/ready/failed); persists voice_id
  - Tests: `tests/voice/test_cloning_job.py`

- **T129** — Integrate cloning job into daemon startup
  - Input: voice_sample.wav, daemon startup
  - Output: Daemon checks for voice sample; starts clone job if present & not done
  - Acceptance: Daemon starts clone job on first sample; status stored in soul_identity.yaml
  - Tests: `tests/agents/test_daemon_voice_init.py`

- **T130 [P]** — Implement cloning status polling endpoint
  - Input: Clone job ID
  - Output: `gurujee/api/voice.py:GET /voice/clone-status` returning `{ status: "processing", progress: 50 }`
  - Acceptance: PWA can poll status; updates UI in real-time
  - Tests: `tests/api/test_voice_endpoint.py`

- **T131** — Update soul_identity.yaml schema for voice_id & clone_status
  - Input: Voice cloning fields
  - Output: Extended `soul_identity.yaml` with fields: `voice_id`, `voice_sample_hash`, `voice_cloned_at`, `voice_clone_status`
  - Acceptance: Schema validates; soul agent reads voice_id on startup
  - Tests: `tests/models/test_soul_identity.py`

- **T132** — Implement TTS with fallback to cloned voice
  - Input: Text, soul agent model, voice_id (if available)
  - Output: `gurujee/tts/synthesizer.py:synthesize(text) -> audio_stream`
  - Acceptance: Uses cloned voice if voice_id present; falls back to default ElevenLabs voice; falls back to ACE TTS on API failure
  - Tests: `tests/tts/test_synthesizer.py`

- **T133** — Integrate TTS into SIP voice response
  - Input: Incoming SIP call, reply text
  - Output: SIP agent uses cloned voice for response audio
  - Acceptance: Calls using cloned voice (if available) or default; tested with pjsua2 simulation
  - Tests: `tests/integrations/test_sip_handler_voice.py`

- **T134** — Integrate TTS into reminder/notification playback
  - Input: Reminder alert (cron agent)
  - Output: Reminder alert uses cloned voice for notification audio
  - Acceptance: User hears reminder in their own voice (if cloned); fallback to default
  - Tests: `tests/agents/test_cron_agent_voice.py`

- **T135** — Implement voice quality check (MOS estimation)
  - Input: Cloned voice audio
  - Output: `gurujee/voice/quality.py:estimate_mos(audio) -> float` (0–5 scale)
  - Acceptance: MOS ≥ 3.5 for production release; warns user if lower
  - Tests: `tests/voice/test_quality.py` (using reference samples)

- **T136** — Add voice cloning success/failure notification to PWA
  - Input: Clone job completion event
  - Output: PWA notification: "Voice cloning complete! Ready to use" or "Cloning failed; falling back to default voice"
  - Acceptance: User receives timely notification
  - Tests: `e2e/test_pwa_voice_notification.py`

- **T137** — Integration test: Voice recording → cloning → TTS
  - Input: Voice sample, clone job, TTS synthesis
  - Output: Test suite in `tests/integration/test_voice_e2e.py`
  - Acceptance: End-to-end: record → clone → synthesize → output audio uses cloned voice
  - Tests: Full flow with mocked ElevenLabs

- **T138 [P]** — Performance test: Voice cloning latency
  - Input: Sample voice, ElevenLabs API (or mock with realistic delay)
  - Output: Test measuring clone time; assert < 60 seconds
  - Tests: `tests/performance/test_voice_cloning_latency.py`

- **T139 [P]** — Cache cloned voice for offline use (optional Phase 2)
  - Input: Cloned voice_id
  - Output: Daemon caches cloned voice locally (in encrypted data/); enables TTS without API on poor connection
  - Acceptance: TTS works even if ElevenLabs API temporarily unavailable (cached for <1 hour)
  - Tests: `tests/voice/test_voice_cache.py`

- **T140** — Handle voice cloning failures gracefully
  - Input: Clone job failure (network error, quota exceeded)
  - Output: Daemon logs failure; continues with default voice; user notified
  - Acceptance: System remains operational; user aware cloning failed
  - Tests: `tests/voice/test_cloning_failure.py`

---

## PHASE 2.3 — PWA Settings Panel (Weeks 8–9, Tasks T141–T160)

### Settings UI Implementation (T141–T155)

- **T141** — Design PWA Settings panel layout (Figma mockup)
  - Input: Spec FR-006 US-006
  - Output: Mockup with tabs: Model, Voice, Automation, Keys, Export/Import, About
  - Acceptance: Design reviewed; accessible (WCAG AA); mobile-responsive
  - Tests: Design review + accessibility audit

- **T142** — Implement Settings UI component shell (React/Vue)
  - Input: Layout design from T141
  - Output: `src/pwa/components/SettingsPanel.tsx` with tab routing
  - Acceptance: Tabs switchable; responsive on mobile
  - Tests: `tests/pwa/test_settings_panel.py` (snapshot)

- **T143** — Implement Model tab (select default model, view routing policies)
  - Input: `agent_model_routing.yaml`, available models list
  - Output: Settings > Model tab with dropdown for default model, info on routing
  - Acceptance: User can select model; routing info displayed; selection persisted
  - Tests: `tests/pwa/test_settings_model_tab.py`

- **T144** — Implement Voice tab (record, test, view cloning status)
  - Input: Voice recording endpoint (T122), clone status endpoint (T130)
  - Output: Settings > Voice tab with record button, playback, status indicator
  - Acceptance: User can record sample, hear playback, see clone status (from T125)
  - Tests: `tests/pwa/test_settings_voice_tab.py`

- **T145** — Implement Automation tab (manage SMS/call rules, allowlist/blocklist)
  - Input: `automation_rules.yaml` (T103), rules schema (T101)
  - Output: Settings > Automation tab with rule editor (UI builder or YAML editor)
  - Acceptance: User can add/edit/delete rules; UI prevents invalid rules
  - Tests: `tests/pwa/test_settings_automation_tab.py`

- **T146** — Implement Keys tab (POLLINATIONS_API_KEY entry, encrypted storage)
  - Input: API key input, keystore integration
  - Output: Settings > Keys tab with secure input field
  - Acceptance: Key stored in keystore (AES-256); input masked; user warned of importance
  - Tests: `tests/pwa/test_settings_keys_tab.py`

- **T147 [P]** — Implement Export Settings (backup soul_identity.yaml, rules)
  - Input: `soul_identity.yaml`, `automation_rules.yaml`
  - Output: Settings > Export button → downloads JSON backup
  - Acceptance: User can export and re-import settings
  - Tests: `tests/pwa/test_settings_export.py`

- **T148 [P]** — Implement Import Settings (restore from backup)
  - Input: Exported JSON
  - Output: Settings > Import button → parses and validates JSON; restores settings
  - Acceptance: User can restore settings from backup
  - Tests: `tests/pwa/test_settings_import.py`

- **T149** — Implement About tab (version, constitution summary, GitHub link)
  - Input: App version, constitution.md excerpt
  - Output: Settings > About tab with version info, principles summary, links
  - Acceptance: User can see app version and principles
  - Tests: `tests/pwa/test_settings_about_tab.py`

- **T150** — Implement Settings persistence (browser localStorage)
  - Input: Settings updates from tabs (T143–T148)
  - Output: Settings persisted in **browser localStorage** (clarification Q3); sensitive data (API keys) encrypted client-side before storage
  - Acceptance: User settings retained after PWA close/reopen; settings survive browser restart; lost if cache cleared (user responsibility)
  - Tests: `tests/pwa/test_settings_persistence.py` (verify localStorage read/write, survives restart)

### Settings API Backend (T151–T160)

- **T151** — Create Settings API endpoints
  - Input: FastAPI app
  - Output: `gurujee/api/settings.py` with endpoints:
    - `GET /settings` → current settings
    - `POST /settings/model` → update default model
    - `POST /settings/automation/rules` → update rules
    - `POST /settings/keys/{key_name}` → update API key (encrypted)
  - Acceptance: Endpoints validate input; return errors on invalid data
  - Tests: `tests/api/test_settings_endpoints.py`

- **T152** — Implement Settings validation (schema + business logic)
  - Input: Settings update requests
  - Output: `gurujee/settings/validator.py:validate_settings(data) -> (valid, errors)`
  - Acceptance: Validates model existence, rule format, key format; returns detailed errors
  - Tests: `tests/settings/test_validator.py`

- **T153** — Implement Settings storage (encrypted in keystore)
  - Input: Validated settings
  - Output: `gurujee/settings/store.py:SettingsStore` class for get/set/delete
  - Acceptance: Settings encrypted in keystore; can be read back correctly
  - Tests: `tests/settings/test_store.py`

- **T154** — Integrate Settings API with PWA (WebSocket updates)
  - Input: Settings API endpoints (T151), PWA Settings panel (T141–T150)
  - Output: PWA WebSocket listener for settings changes; real-time sync
  - Acceptance: PWA updates automatically when settings changed (e.g., rule added)
  - Tests: `tests/pwa/test_settings_websocket_sync.py`

- **T155** — Add Settings access logging to audit trail
  - Input: Settings API endpoints (T151)
  - Output: All settings changes logged to `audit.jsonl` with action=`settings_change`, resource=`settings`, change={field, old_value, new_value}
  - Acceptance: Audit trail shows all settings modifications
  - Tests: `tests/audit/test_settings_audit_logging.py`

---

## PHASE 2.4 — Multi-Model Orchestration (Weeks 10–12, Tasks T156–T185)

### Model Routing Config (T156–T170)

- **T156** — Create `config/agent_model_routing.yaml` schema
  - Input: spec.md FR-004, plan.md
  - Output: `config/agent_model_routing.yaml.schema` (JSON Schema)
  - Acceptance: Schema validates example routing from plan
  - Tests: `tests/config/test_agent_model_routing_schema.py`

- **T157 [P]** — Design agent model routing data model (Pydantic)
  - Input: Schema from T156
  - Output: `gurujee/models/model_routing.py` with classes: `AgentModelConfig`, `ModelFallback`
  - Acceptance: All examples from plan instantiate correctly
  - Tests: `tests/models/test_model_routing.py`

- **T158** — Implement model routing loader
  - Input: `config/agent_model_routing.yaml`
  - Output: `gurujee/config/model_routing_loader.py:ModelRoutingLoader` (similar to T103)
  - Acceptance: Loads routing config; supports hot-reload via file watcher
  - Tests: `tests/config/test_model_routing_loader.py`

- **T159** — Implement model selection logic per agent
  - Input: Agent ID, model routing config
  - Output: `gurujee/models/selector.py:select_model(agent_id) -> model_id`
  - Acceptance: Returns correct model for agent; supports user override from Settings
  - Tests: `tests/models/test_model_selector.py`

- **T160 [P]** — Create default `config/agent_model_routing.yaml`
  - Input: Spec FR-004, plan.md examples
  - Output: Configuration file with reasonable defaults for all agents
  - Acceptance: File validates against schema; agents can read and use routing
  - Tests: Manual review + T156 validation

### Runtime Model Override (T161–T170)

- **T161** — Add model override to Settings UI (Model tab extension)
  - Input: Settings panel from T143
  - Output: Settings > Model tab with per-agent model override option
  - Acceptance: User can override model for specific agent (e.g., orchestrator)
  - Tests: `tests/pwa/test_settings_model_override.py`

- **T162** — Implement model override persistence (keystore)
  - Input: User overrides from T161
  - Output: Overrides stored in keystore; loaded on daemon startup
  - Acceptance: Overrides persist across sessions
  - Tests: `tests/settings/test_model_override_store.py`

- **T163** — Integrate model override into agent initialization
  - Input: Model routing loader (T158), user overrides (T162)
  - Output: Agents use override model if set; fallback to default routing
  - Acceptance: Agents respect user model overrides
  - Tests: `tests/agents/test_agent_model_override.py`

- **T164** — Implement model fallback chain (failover logic)
  - Input: Model routing config (T158), model availability
  - Output: `gurujee/models/fallback.py:select_with_fallback(agent_id) -> model_id`
  - Acceptance: If default model fails, tries fallback models in order; logs failures
  - Tests: `tests/models/test_fallback.py`

- **T165** — Add cost tracking to model selection
  - Input: Model routing config (cost_per_1m_tokens from plan)
  - Output: Track cost per model; log to `data/metrics/cost.jsonl`
  - Acceptance: Cost data available for analysis; user can see per-session cost in Settings
  - Tests: `tests/models/test_cost_tracking.py`

- **T166** — Implement budget tier support (economy/standard/premium)
  - Input: Budget tier from model routing config
  - Output: `gurujee/models/budgeting.py` enforcing tier-based model selection
  - Acceptance: User can set budget tier; only models in tier are used
  - Tests: `tests/models/test_budgeting.py`

- **T167** — Create cost optimization dashboard (PWA)
  - Input: Cost metrics from T165
  - Output: PWA tab showing "Cost this month: $X.XX", breakdown by agent/model
  - Acceptance: User can see cost per session; understand which agents/models cost most
  - Tests: `tests/pwa/test_cost_dashboard.py`

- **T168 [P]** — Integration test: Model routing end-to-end
  - Input: Model routing config, agent initialization
  - Output: Test suite in `tests/integration/test_model_routing_e2e.py`
  - Acceptance: Agents use correct models per routing; fallback chain works
  - Tests: Full flow with mocked API calls

- **T169 [P]** — Performance test: Model selection overhead
  - Input: Model selector, many agents
  - Output: Test measuring selection latency per agent; assert < 1ms
  - Tests: `tests/performance/test_model_selection_latency.py`

- **T170** — Documentation: Model routing configuration guide
  - Input: Model routing config, use cases
  - Output: `docs/model-routing.md` with examples, best practices
  - Acceptance: Guide explains routing, overrides, budgeting; includes examples
  - Tests: Manual review

---

## PHASE 2.5 — Resilience & Observability (Weeks 13–16, Tasks T171–T200)

### Queue Management (T171–T180)

- **T171** — Formalize queue constraints
  - Input: Spec FR-005
  - Output: `gurujee/queue/config.py` with constants: `MAX_CAPACITY=100`, `MESSAGE_TTL_SECONDS=60`, `OVERFLOW_ACTION="fifo_drop"`
  - Acceptance: Constants documented; used by queue implementation
  - Tests: `tests/queue/test_config.py`

- **T172** — Implement bounded message queue with TTL (equal priority, FIFO)
  - Input: Queue constraints from T171
  - Output: `gurujee/queue/bounded_queue.py:BoundedQueue` class with:
    - `put(message, ttl=60)` → enqueues or drops if full
    - `get_all() -> List[message]` → returns messages not yet expired (oldest first, FIFO)
    - `cleanup()` → removes expired messages
  - Acceptance: Queue respects capacity and TTL; FIFO eviction works; **all messages have equal priority** (clarification Q1, no priority tiers); priority routing deferred to Phase 3
  - Tests: `tests/queue/test_bounded_queue.py` (verify FIFO order, equal priority)

- **T173** — Implement queue overflow handling
  - Input: Bounded queue (T172)
  - Output: When queue at capacity, drop oldest message; log warning; notify user if >50 backlog
  - Acceptance: System remains stable on long outages; user notified
  - Tests: `tests/queue/test_overflow_handling.py`

- **T174** — Implement dead-letter queue (DLQ)
  - Input: Failed messages (AI errors, timeouts)
  - Output: `gurujee/queue/dlq.py:DeadLetterQueue` persisting failed messages to `data/dlq.jsonl`
  - Acceptance: Failed messages logged with error; available for replay
  - Tests: `tests/queue/test_dlq.py`

- **T175 [P]** — Implement queue recovery on reconnect
  - Input: Queued messages, DLQ
  - Output: On reconnect, resend up to 10 most recent messages; notify user of dropped messages
  - Acceptance: Messages retried on reconnect; DLQ available for audit
  - Tests: `tests/queue/test_recovery.py`

- **T176** — Add queue metrics to observability
  - Input: Bounded queue operations
  - Output: Emit metrics: queue_size, queue_capacity, messages_dropped, messages_failed
  - Acceptance: Metrics available via `/metrics` endpoint
  - Tests: `tests/metrics/test_queue_metrics.py`

- **T177** — Integrate bounded queue into message bus
  - Input: MessageBus (from phase 1), bounded queue (T172)
  - Output: Replace simple asyncio.Queue with BoundedQueue in GatewayDaemon
  - Acceptance: Daemon uses bounded queue; old messages expired; overflow handled
  - Tests: `tests/daemon/test_gateway_bounded_queue.py` (integration)

- **T178** — Add queue status to PWA (optional Phase 2)
  - Input: Queue metrics (T176)
  - Output: PWA "Status" tab showing queue size, capacity, recent dropped messages
  - Acceptance: User can see queue health
  - Tests: `tests/pwa/test_queue_status.py`

- **T179 [P]** — Integration test: Queue overflow scenario
  - Input: Mocked long outage, bounded queue
  - Output: Test suite in `tests/integration/test_queue_overflow_e2e.py`
  - Acceptance: Queue fills, overflow occurs, oldest messages dropped, recovery works
  - Tests: Full flow simulation

- **T180** — Documentation: Queue management behavior
  - Input: Queue config, behavior
  - Output: `docs/queue-management.md` explaining capacity, TTL, overflow, recovery
  - Acceptance: Guide clear; users understand queue constraints
  - Tests: Manual review

### Audit Logging (T181–T190)

- **T181** — Design audit log schema
  - Input: Spec FR-007, potential use cases
  - Output: `docs/audit-schema.md` with JSON schema for audit events
  - Acceptance: Schema covers all user actions (chat, automation, settings, voice)
  - Tests: Design review

- **T182** — Implement audit logger
  - Input: Audit schema from T181
  - Output: `gurujee/audit/logger.py:AuditLogger` with `log(action, resource, change, outcome)`
  - Acceptance: Logs events to `data/audit.jsonl` with timestamp, action, resource, change, outcome
  - Tests: `tests/audit/test_audit_logger.py`

- **T183** — Add audit logging to all user-facing actions
  - Input: Audit logger (T182)
  - Output: Integrate logging into:
    - Chat send (soul agent)
    - SMS send (automation agent)
    - Call routing (automation agent)
    - Settings update (API)
    - Voice recording (API)
  - Acceptance: All actions logged with correct schema
  - Tests: `tests/audit/test_action_logging.py`

- **T184** — Implement audit log rotation & archival
  - Input: `data/audit.jsonl` growing large
  - Output: `gurujee/audit/archiver.py` archiving logs >90 days old to `data/audit-archive/`
  - Acceptance: Old logs archived; current log stays manageable
  - Tests: `tests/audit/test_archiver.py`

- **T185** — Implement audit log query API
  - Input: Audit logs
  - Output: `gurujee/api/audit.py` endpoints:
    - `GET /audit/logs?action=sms_auto_reply&limit=100` → filtered logs
    - `GET /audit/export?from=2026-05-01&to=2026-05-31` → export CSV
  - Acceptance: Users can query and export audit logs
  - Tests: `tests/api/test_audit_endpoints.py`

- **T186 [P]** — Create audit log viewer in PWA (optional Phase 2)
  - Input: Audit query API (T185)
  - Output: PWA "Audit" tab showing recent actions (last 100)
  - Acceptance: User can see audit trail
  - Tests: `tests/pwa/test_audit_viewer.py`

- **T187 [P]** — Implement audit log security (encryption at rest, redaction)
  - Input: Audit logs, sensitive data (phone numbers, API keys)
  - Output: Audit logs encrypted in keystore; sensitive fields redacted or masked
  - Acceptance: Audit logs secure; users can't accidentally expose PII
  - Tests: `tests/audit/test_security.py`

- **T188** — Integration test: Audit trail end-to-end
  - Input: User actions (chat, SMS, settings)
  - Output: Test suite in `tests/integration/test_audit_e2e.py`
  - Acceptance: All actions logged correctly; query and export work
  - Tests: Full flow

- **T189** — Documentation: Audit logging for compliance
  - Input: Audit schema, archival, query
  - Output: `docs/audit-compliance.md` explaining logging for compliance/privacy
  - Acceptance: Users understand audit logging and can export for compliance
  - Tests: Manual review

- **T190** — Compliance testing: GDPR/privacy audit
  - Input: Audit logs, sensitive data handling
  - Output: Report: "All PII in audit logs is redacted / encrypted; compliant with GDPR"
  - Acceptance: Security review confirms compliance
  - Tests: Manual security review

### Performance & Metrics (T191–T200)

- **T191** — Implement RAM profiling (daily cron job, 50MB hard blocker)
  - Input: memory-profiler, Termux ARM64 device (Phase 2.5 gate, CRITICAL)
  - Output: `gurujee/profiling/ram_profiler.py` running daily via cron agent; logs to `data/metrics/ram.jsonl`
  - Acceptance: Daily RAM measurements logged; **P1 ceiling (50 MB) is HARD BLOCKER** (clarification Q2): if exceeded, must cut features (voice, cron, etc.) before release, not proceed with bloat
  - Tests: `tests/profiling/test_ram_profiler.py` (assert baseline ≤ 50MB on ARM64)

- **T192** — Implement chat latency metrics (client-side)
  - Input: Chat UI (message send → AI response)
  - Output: Client JS timestamps; log to `data/metrics/chat.jsonl`
  - Acceptance: Latency sampled (10% of messages); logged for analysis
  - Tests: `tests/pwa/test_latency_metrics.py`

- **T193** — Create metrics aggregation (p50, p95, p99)
  - Input: Raw metrics (RAM, latency)
  - Output: `gurujee/metrics/aggregator.py` computing percentiles; emit to `/metrics`
  - Acceptance: Metrics endpoint returns aggregated stats
  - Tests: `tests/metrics/test_aggregator.py`

- **T194** — Implement alert thresholds (P1 breaches)
  - Input: Metrics (RAM, latency)
  - Output: Alert logic: if idle RAM > 55 MB (5 MB margin), notify user; if p95 latency > 5s, warn
  - Acceptance: Alerts triggered on threshold breach; user notified
  - Tests: `tests/metrics/test_alerting.py`

- **T195** — Create metrics dashboard (PWA)
  - Input: Metrics from `/metrics` endpoint
  - Output: PWA "Metrics" tab showing:
    - Idle RAM (daily trend)
    - Chat latency (p95, last 24 hours)
    - Model usage (cost per model)
    - Queue health (size, drops)
  - Acceptance: User can monitor system health
  - Tests: `tests/pwa/test_metrics_dashboard.py`

- **T196** — Implement battery drain tracking (optional Phase 2)
  - Input: System battery API (Termux or pjsua2)
  - Output: Voice activity time logged; correlation with battery drain analyzed
  - Acceptance: Metrics show voice impact on battery; target <10% drain during idle
  - Tests: `tests/profiling/test_battery_tracking.py` (simulation)

- **T197** — ARM64 device measurement campaign (Phase 2.5 gate)
  - Input: Profile script from Phase 1 (profile_ram.py)
  - Output: Run T069 measurement on real ARM64 Termux device (Pixel 6+, others); document in `specs/002-gurujee-phase2/data/benchmarks/arm64-ram-results.txt`
  - Acceptance: **GATE FOR PHASE 2 RELEASE**: Measurement must confirm ≤ 50 MB (P1 ceiling)
  - Tests: Real device measurement (manual)

- **T198** — Chat latency measurement on real device
  - Input: Chat UI, real Android device, network conditions
  - Output: Measure message send → AI response latency; p95 < 3 seconds target
  - Acceptance: **GATE FOR PHASE 2 RELEASE**: Measurement confirms < 3s p95
  - Tests: Real device measurement (manual)

- **T199** — Integration test: Metrics collection end-to-end
  - Input: Metrics collection pipeline
  - Output: Test suite in `tests/integration/test_metrics_e2e.py`
  - Acceptance: Metrics collected, aggregated, displayed in dashboard
  - Tests: Full flow with simulated load

- **T200** — Documentation: Performance & observability guide
  - Input: Metrics, thresholds, dashboard
  - Output: `docs/performance.md` explaining RAM/latency targets, how to read dashboard, how to debug
  - Acceptance: Guide clear; users understand performance targets
  - Tests: Manual review

---

## Summary

| Phase | Tasks | Duration | Focus |
|-------|-------|----------|-------|
| 2.1   | T101–T125 (25 tasks) | 4 weeks | SMS & call automation |
| 2.2   | T126–T150 (25 tasks) | 3 weeks | Voice cloning & TTS |
| 2.3   | T151–T160 (10 tasks) | 2 weeks | PWA Settings panel |
| 2.4   | T161–T185 (25 tasks) | 3 weeks | Multi-model orchestration |
| 2.5   | T186–T200 (15 tasks) | 4 weeks | Resilience, observability, P1 gate |
| **TOTAL** | **100 tasks** | **16 weeks** | **Production hardening** |

---

## Release Gates

### Before Phase 2 Release

- [ ] **ARM64 RAM measurement ≤ 50 MB** (T197 — P1 constitutional requirement)
- [ ] **Chat latency p95 < 3 seconds** (T198 — real device)
- [ ] **Code coverage ≥ 80%** (all test tasks)
- [ ] **Security review passed** (audit logging, encryption)
- [ ] **All 100 tasks completed**

### Beta Release (Pre-Production)

- [ ] 10+ external testers
- [ ] SMS/call automation on 3+ Android versions
- [ ] 2-week feedback cycle (bugs, UX improvements)
- [ ] Final production build

---

## Notes

- Phase 2 builds on Phase 1 MVP; assumes Phase 1 infrastructure stable
- All task descriptions include acceptance criteria and test files
- Integration tests use mocked external APIs (Termux, ElevenLabs, pjsua2)
- Real device measurements (ARM64) conducted during Phase 2.5 as release gate
- Phase 2 defers: cloud sync, Play Store distribution (Phase 3+)
