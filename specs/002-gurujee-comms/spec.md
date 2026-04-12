# Feature Specification: GURUJEE Communications Layer

**Feature Branch**: `002-gurujee-comms`
**Created**: 2026-04-12
**Status**: Draft
**Phase**: 2 — Communications (SIP calling, SMS auto-reply, cron activation)
**Input**: User description: "Build the communications layer for GURUJEE: SIP auto-answer with
AI voice, SMS auto-reply, and cron agent activation (Phase 1 scaffold → live)"
**Depends on**: `001-gurujee-foundation` (daemon, agents, keystore, PWA, allowlist)

**Subsequent phases**:
- `003-gurujee-advanced` — sub-agent orchestrator, skills system, plugins system

---

## Clarifications

### Session 2026-04-12

- SIP library: `pjsua2` Python bindings compiled in Termux (no root; Shizuku not required for SIP)
- SIP domain: `sip.suii.us` — credentials (username, password, caller_id) from keystore only; never hardcoded
- Voice clone: Phase 1 captured the raw sample and stored the ElevenLabs voice ID in keystore; Phase 2 uses that voice ID for TTS in calls
- Auto-answer opt-in: disabled by default; user enables via Settings > Calls > Auto-Answer in PWA
- SMS polling: Termux:API (`termux-sms-list`) every 30 seconds; no background SMS broadcast (non-root constraint)
- SMS auto-reply list: user configures approved sender numbers in Settings > SMS > Auto-Reply List (stored in keystore, not plaintext)
- Cron expressions: stored in `data/cron_schedules.yaml`; Phase 1 CronAgent already loads this file on startup — Phase 2 adds the API to populate it from chat commands and from the PWA settings
- Cron execution scope in Phase 2: reminders (TTS notification via ElevenLabs to speaker), auto-SMS, run automation command. Auto-call deferred to Phase 3.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — AI Answers Incoming SIP Calls (Priority: P1)

A contact calls the user's SIP number. GURUJEE detects the incoming call via pjsua2,
answers after 2 rings, greets the caller by name (if in contacts), transcribes the
caller's speech with Whisper tiny.en, sends the transcript to Pollinations nova-fast,
and streams the AI response as ElevenLabs TTS audio back into the call in real time.
The caller hears a natural, voice-cloned AI response with no noticeable silence.

The user can enable/disable auto-answer in Settings > Calls > Auto-Answer.
When disabled, incoming calls ring without being answered by GURUJEE.

**Why this priority**: SIP calling is the signature feature of Phase 2 — the reason the
SIP credentials were captured in Phase 1 setup. It differentiates GURUJEE from SMS-only
assistants.

**Independent Test**: Configure SIP credentials. Call the SIP number from another phone.
Verify GURUJEE answers after 2 rings, greets, transcribes "What's the weather today?",
and responds with a voiced AI answer within 5 seconds of call connect.

**Acceptance Scenarios**:

1. **Given** auto-answer is enabled and a call comes in, **When** 2 rings complete,
   **Then** pjsua2 accepts the call, plays a greeting, and enters listen mode.

2. **Given** the caller speaks, **When** Whisper finishes transcription,
   **Then** the transcript is sent to Pollinations and the AI response streams as
   ElevenLabs TTS audio back into the call within 3 seconds of speech end.

3. **Given** auto-answer is disabled, **When** a call comes in,
   **Then** GURUJEE does NOT answer; the call rings until the caller hangs up or
   voicemail picks up.

4. **Given** the user says "call Ali" in the PWA chat, **When** GURUJEE looks up "Ali"
   in the user's contact list, **Then** it dials Ali's SIP/PSTN number and confirms
   "Calling Ali..." in the chat.

5. **Given** ElevenLabs is unreachable, **When** TTS is required during a call,
   **Then** GURUJEE falls back to ACE TTS (on-device) and logs the ElevenLabs error.

6. **Given** Whisper STT fails mid-call, **When** the caller speaks and no transcript
   arrives within 8 seconds, **Then** GURUJEE says "Sorry, I didn't catch that" and
   re-enters listen mode without dropping the call.

---

### User Story 2 — AI Auto-Replies to Approved SMS Senders (Priority: P2)

GURUJEE polls `termux-sms-list` every 30 seconds. When a new SMS arrives from a
number on the user's approved auto-reply list, GURUJEE reads it, generates a
contextual AI reply (using conversation history if available), and sends it via
`termux-sms-send`. The user sees all auto-replies in the PWA chat view as a
conversation thread per contact.

When a message arrives from a non-approved sender, GURUJEE notifies the user in the
PWA chat but does NOT auto-reply.

**Why this priority**: SMS auto-reply is the second communications capability that
makes GURUJEE a passive AI companion — the user's phone handles messages even when
they're unavailable.

**Independent Test**: Add a test number to the approved list. Send an SMS to the device.
Within 60 seconds, an AI reply must be sent from the device. Confirm in `termux-sms-list`.

**Acceptance Scenarios**:

1. **Given** a new SMS arrives from an approved number, **When** the 30s poll detects it,
   **Then** GURUJEE generates an AI reply and sends it via `termux-sms-send` within 90
   seconds of the SMS arriving.

2. **Given** a new SMS arrives from a non-approved number, **When** GURUJEE detects it,
   **Then** it shows the message in the PWA chat as a notification but does NOT send
   a reply.

3. **Given** `termux-sms-send` fails (e.g., no SIM), **When** the send attempt fails,
   **Then** GURUJEE logs the error and shows a failure notification in the PWA chat;
   the daemon does not crash.

4. **Given** the user says "add +1234567890 to my auto-reply list" in chat,
   **When** GURUJEE processes the command, **Then** the number is added to the
   approved list in the keystore and confirmed in the chat.

---

### User Story 3 — Scheduled Tasks via Natural Language (Priority: P2)

The user says "remind me every morning at 8am to drink water" in the PWA chat.
GURUJEE parses the intent with the AI, converts it to a cron expression
(`0 8 * * *`), stores it in `data/cron_schedules.yaml`, and the CronAgent executes
it — sending a TTS notification to the device speaker at 8am each day.

The user can list, pause, and delete scheduled tasks from the PWA chat or Settings.

**Why this priority**: The CronAgent was already scaffolded in Phase 1; Phase 2 makes
it live. Cron tasks are a natural language superpower — users don't need to know cron
syntax.

**Independent Test**: Say "remind me in 2 minutes to test the cron agent". Verify the
reminder fires via TTS at the correct time and a record appears in `data/cron_schedules.yaml`.

**Acceptance Scenarios**:

1. **Given** the user says "remind me daily at 7pm to take medication", **When** the AI
   parses this, **Then** a cron entry (`0 19 * * *`) is written to `data/cron_schedules.yaml`
   and GURUJEE confirms "I'll remind you every day at 7pm to take your medication."

2. **Given** a cron job fires, **When** the scheduled time arrives, **Then** GURUJEE
   plays a TTS reminder via the device speaker (ElevenLabs, falling back to ACE TTS).

3. **Given** the user says "what reminders do I have?", **When** GURUJEE processes this,
   **Then** it lists all active cron jobs from `data/cron_schedules.yaml` in a readable
   summary in the chat.

4. **Given** a cron job fires for auto-SMS, **When** the time arrives, **Then** GURUJEE
   sends the configured SMS via `termux-sms-send` and logs the action.

5. **Given** the cron schedule file is corrupted or missing, **When** CronAgent starts,
   **Then** it starts with an empty schedule, logs the error, and notifies the user in
   the PWA chat — it does NOT crash.

---

### Edge Cases

- What happens if the SIP server is unreachable at daemon startup? pjsua2 registration
  fails silently; GURUJEE logs the error and retries registration every 60 seconds.
  SIP status is shown as "unregistered" in the health endpoint.
- What happens if a call comes in while GURUJEE is already on a call? Second call is
  rejected (busy signal); the caller is logged. No parallel call handling in Phase 2.
- What happens if ElevenLabs rate-limits mid-call? Fall back to ACE TTS immediately
  for the current utterance; log the rate limit event; retry ElevenLabs on the next turn.
- What happens if `termux-sms-list` returns malformed JSON? SMS polling catches the parse
  error, logs it, and skips that poll cycle — does not crash the SMS polling loop.
- What happens if the user removes a number from the auto-reply list while a reply is
  being generated? The in-flight reply completes; future messages from that number are
  not auto-replied.
- What happens if a cron job fails (e.g., SMS send fails)? The error is logged to
  `data/automation.log`; the CronAgent continues running; the next scheduled run proceeds.
- What happens if pjsua2 is not installed (e.g., fresh Termux)? Guided setup Phase 2
  extension installs it; if still absent at runtime, SIP features are disabled with a
  clear warning in GET /health and in the PWA status bar.

---

## Requirements *(mandatory)*

### Functional Requirements

**SIP Calling**

- **FR-101**: GURUJEE MUST register with the SIP server defined in the keystore
  (`sip.suii.us`) using pjsua2 on daemon startup. Registration MUST retry every 60
  seconds on failure; retry is silent (no user notification unless 5+ consecutive failures).
- **FR-102**: When auto-answer is enabled AND an incoming SIP call arrives, GURUJEE MUST
  answer after 2 rings, play a greeting, and begin listening. Auto-answer is disabled by
  default; user enables via PWA Settings > Calls > Auto-Answer.
- **FR-103**: During a call, GURUJEE MUST transcribe the caller's speech using Whisper
  tiny.en (local, streaming), send the transcript to Pollinations, and stream the AI
  response as ElevenLabs TTS audio (user's cloned voice if available) back into the call.
  Round-trip latency from speech-end to first TTS audio MUST be under 5 seconds on WiFi.
- **FR-104**: When the user says an outgoing call command in chat (e.g., "call Ali"),
  GURUJEE MUST look up the name in the contacts list, dial via pjsua2, and confirm the
  call attempt in the chat UI.
- **FR-105**: ElevenLabs TTS MUST be called in streaming mode (P8 / P1 compliance);
  buffered mode is prohibited. ACE TTS MUST be available as fallback when ElevenLabs
  is unreachable or rate-limited.
- **FR-106**: SIP credentials (domain, username, password, caller_id) MUST be read from
  the AES-256-GCM keystore only; MUST NOT appear in config files, source code, or logs.

**SMS Auto-Reply**

- **FR-107**: GURUJEE MUST poll `termux-sms-list` every 30 seconds for new messages.
  SMS polling MUST NOT block the event loop; it MUST run as an async task in the daemon.
- **FR-108**: When a new SMS arrives from an approved sender, GURUJEE MUST generate an AI
  reply using Pollinations and send it via `termux-sms-send`. The auto-reply list MUST be
  stored in the keystore; MUST NOT be stored in plaintext config files.
- **FR-109**: Messages from non-approved senders MUST be shown in the PWA chat as
  notifications but MUST NOT receive an auto-reply.
- **FR-110**: The user MUST be able to add/remove numbers from the auto-reply list by
  typing a command in the PWA chat (e.g., "add +1234567890 to auto-reply").

**Cron Agent Activation**

- **FR-111**: The CronAgent (Phase 1 scaffold) MUST be activated to execute scheduled
  jobs from `data/cron_schedules.yaml`. Supported action types in Phase 2:
  `tts_reminder` (play TTS via ElevenLabs/ACE), `send_sms`, `run_automation_command`.
- **FR-112**: When the user expresses a scheduling intent in chat, GURUJEE MUST use the
  AI to parse the intent into a cron expression and write it to `data/cron_schedules.yaml`,
  confirming the scheduled job in chat.
- **FR-113**: The user MUST be able to list, pause, and delete cron jobs by typing
  commands in the PWA chat. The cron schedule MUST survive daemon restarts.

**Health & Observability**

- **FR-114**: GET `/health` MUST include SIP registration status:
  `{"sip": "registered" | "unregistered" | "disabled"}`.
- **FR-115**: All SIP call events (answer, end, reject, error), SMS send/receive events,
  and cron job executions MUST be logged to `data/automation.log` (existing rotating handler).

---

### Key Entities

- **SIPSession**: Active pjsua2 call. Attributes: `call_id`, `caller_uri`, `state`
  (RINGING/ACTIVE/ENDED), `start_time`, `transcript` (accumulated), `direction`
  (INBOUND/OUTBOUND). At most one active session at a time in Phase 2.
- **SMSMessage**: Inbound message from Termux:API poll. Attributes: `sender` (E.164),
  `body`, `received_at`, `auto_replied: bool`, `reply_text: Optional[str]`.
- **CronJob**: Schedule entry in `data/cron_schedules.yaml`. Fields: `id` (uuid),
  `description` (user-facing label), `cron_expression` (standard 5-field), `action_type`
  (`tts_reminder` | `send_sms` | `run_automation_command`), `action_payload` (dict),
  `enabled: bool`, `last_run: Optional[datetime]`, `created_at: datetime`.
- **SIPConfig**: Read from keystore at startup. Fields: `domain`, `username`, `password`,
  `caller_id`, `stun_server` (`stun.l.google.com`). Never persisted outside the keystore.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-101**: An incoming SIP call is answered automatically within 5 seconds of
  the first ring when auto-answer is enabled.
- **SC-102**: Round-trip latency from caller speech-end to first TTS audio byte is
  under 5 seconds on a WiFi connection.
- **SC-103**: SMS auto-reply is sent within 90 seconds of the inbound SMS arriving
  on the device (30s poll + AI generation + send).
- **SC-104**: A natural-language scheduling command is correctly converted to a cron
  expression and stored in `data/cron_schedules.yaml` in 100% of test cases.
- **SC-105**: A cron reminder fires within 60 seconds of its scheduled time.
- **SC-106**: All Phase 2 agents remain within the P1 RAM ceiling:
  idle daemon with SIP registered and SMS polling active < 80 MB RSS
  (extended ceiling vs. Phase 1 50 MB, justified by pjsua2 library overhead;
  must be profiled before merge).
- **SC-107**: When pjsua2 is not installed, GURUJEE starts normally and displays
  a clear "SIP unavailable — pjsua2 not installed" warning in GET /health and the
  PWA status bar; no crash.

---

## Assumptions

- pjsua2 Python bindings compile successfully in Termux on ARM64. If they don't, SIP
  features must be feature-flagged and the daemon must start without them.
- `termux-sms-list` and `termux-sms-send` require Termux:API companion app to be
  installed. Phase 2 setup step adds Termux:API installation if not present.
- ElevenLabs voice ID was captured and stored in the keystore during Phase 1 setup.
  If absent, TTS falls back to ACE TTS for all Phase 2 features.
- The cron daemon started dormant in Phase 1 — Phase 2 assumes it is always-on and
  already wired into GatewayDaemon supervision. No new daemon wiring is needed.
- Phase 2 handles one active SIP call at a time. Parallel call handling is Phase 3.
- SMS auto-reply only processes new messages (received after daemon start). Historical
  messages are shown as read-only in the PWA chat thread but never auto-replied.
