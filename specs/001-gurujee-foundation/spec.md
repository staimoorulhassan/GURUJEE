# Feature Specification: GURUJEE Foundation

**Feature Branch**: `001-gurujee-foundation`
**Created**: 2026-04-11
**Status**: Implemented
**Phase**: 1 — Foundation (all US1–US5 stories delivered)
**Input**: User description: "Build GURUJEE Phase 1 — guided setup, soul agent, memory agent,
heartbeat/gateway daemon, PWA chat UI (localhost:7171), device automation via Shizuku,
Launcher APK, and Pollinations AI backend"

**What Phase 1 actually delivered** (see ADR-003 for architecture pivot):
- Guided setup wizard (8 steps, resume-on-interrupt)
- Soul, memory, heartbeat, user_agent, cron, automation agents (all always-on)
- GatewayDaemon supervising 6 agents
- FastAPI server on localhost:7171 with PWA static chat UI
- WebSocket /ws for real-time streaming; SSE /chat endpoint
- ShizukuExecutor + ToolRouter for device automation (NL → tool call → rish)
- Kivy Launcher APK (ProgressScreen + WebViewScreen)
- Textual TUI as developer/admin tool (--tui flag only)

**Subsequent phases**:
- `002-gurujee-comms` — SIP calling, SMS auto-reply, cron agent activation (Phase 1 scaffold → live)
- `003-gurujee-advanced` — sub-agent orchestrator, skills system, plugins system

---

## Clarifications

### Session 2026-04-11

- Q: AI fallback if Pollinations is unreachable → A: Show error in TUI, queue the request and retry automatically when connection restores.
- Q: Soul identity storage location and editability → A: YAML file at `agents/soul_identity.yaml`; editable by the user via Settings panel.
- Q: Voice clone setup flow → A: User records a 30-second voice sample during guided setup; sample is sent to ElevenLabs instant clone API. Voice ID is stored in keystore. (Actual clone call is Phase 2 TTS; sample capture is Phase 1 setup step.)
- Q: Auto-answer opt-in mechanism → A: Disabled by default; user enables via Settings > Calls > Auto-Answer. (Phase 2 feature; Settings panel scaffold is Phase 1.)
- Q: Sub-agent max parallelism → A: 4 concurrent sub-agents; configurable in `config/agents.yaml`. (Phase 3 feature.)
- Q: SMS auto-reply scope → A: Auto-reply only to contacts in user's approved list, configured in Settings > SMS. (Phase 2 feature.)
- Q: Memory database path and backup → A: SQLite at `data/memory.db`; auto-backup weekly to `data/backups/`.
- Q: Config file format → A: All config/state files use YAML. `agents/soul_identity.yaml` and `data/setup_state.yaml` (renamed from .json to comply with P10).
- Q: Device automation accessibility mechanism → A: Requires GURUJEE Accessibility Service APK companion; installed as part of guided setup in Phase 1 (used in Phase 3).
- Q: Cron expression input format → A: Both natural language ("every morning at 8am", parsed by LLM) and raw cron syntax supported. (Phase 2 feature.)
- Q: Plugin security model → A: Plugins run in restricted Python sandbox (importlib restrictions); user must explicitly approve each plugin before installation. (Phase 3 feature; aligns with ADR-001 built-in-skill sandbox tier.)
- Q: AI model config path conflict (FR-013 vs plan.md) → A: `config/models.yaml` holds the version-controlled model catalogue; `data/user_config.yaml` holds all user runtime preferences (active_model, active_voice_id, tui_theme). Clean separation: `config/` is committed, `data/` is gitignored.
- Q: Streaming response render behavior in TUI Chat screen → A: Tokens stream into the Textual Chat screen as they arrive. Message bubble appears immediately with a blinking cursor indicator. Tokens append in-place (no flicker, no full redraw). On completion, cursor disappears and the full message is written to `data/memory.db`. On network interruption mid-stream, partial text is shown with an `[interrupted]` suffix and the partial content is still logged to `data/memory.db`.
- Q: Keystore PIN UX flow → A: Guided setup prompts the user to set a 4–8 digit PIN (first run only). PIN is never stored — it is the PBKDF2-HMAC-SHA256 input for key derivation combined with the device salt. On every subsequent launch, the TUI prompts for the PIN before the daemon starts. Three consecutive wrong attempts trigger a 30-second lockout with exponential backoff. A "Forgot PIN?" option must display the consequence (keystore wipe + re-run guided setup) explicitly before allowing the user to proceed.
- Q: Canonical config/data paths → A: `config/models.yaml` (model catalogue, version-controlled), `config/agents.yaml` (agent startup config, version-controlled), `config/voice.yaml` (voice provider config, version-controlled), `data/user_config.yaml` (user runtime preferences, gitignored), `data/setup_state.yaml` (setup progress, gitignored), `data/soul_identity.yaml` (soul personality state, gitignored — initialized from `agents/soul_identity.yaml` template on first run), `data/memory.db` (SQLite, gitignored), `data/gurujee.keystore` (encrypted secrets, gitignored). No other config paths are permitted (P10).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — First-Time Setup and Onboarding (Priority: P1)

A user downloads `install.sh` on their Android phone, opens Termux, runs the script, and
GURUJEE guides them through every setup step: dependency installation, Shizuku activation,
GURUJEE Accessibility Service APK installation, permission grants, AI model configuration,
voice sample recording for future voice cloning, SIP credential entry (stored in keystore),
and daemon startup. By the end, GURUJEE greets them by name and is fully operational —
without any manual configuration outside the guided wizard.

**Why this priority**: Nothing else works without a successful first-run setup. This is the
entry gate for all other stories.

**Independent Test**: Run `install.sh` on a stock, non-rooted Android device with a fresh
Termux install. Verify GURUJEE reaches the "Setup complete — I'm ready" state and responds
to a chat message.

**Acceptance Scenarios**:

1. **Given** a fresh Android device with Termux installed, **When** the user runs `install.sh`,
   **Then** all dependencies install, Shizuku is activated, the Accessibility Service APK is
   installed, all permissions are granted, all daemons start, and GURUJEE sends a greeting
   message — with no manual steps skipped.

2. **Given** the guided setup is interrupted halfway (e.g., phone rebooted), **When** the user
   re-opens GURUJEE, **Then** setup resumes from exactly where it left off, without repeating
   completed steps.

3. **Given** a permission (e.g., microphone) is denied during setup, **When** the user retries,
   **Then** GURUJEE explains why the permission is needed, guides the user to the correct
   Android settings screen, and re-checks the permission automatically.

4. **Given** setup is complete, **When** the user opens GURUJEE after a reboot, **Then** all
   daemons restart automatically and GURUJEE is ready without re-running setup.

5. **Given** the voice sample recording step in setup, **When** GURUJEE reaches that step,
   **Then** it first displays a consent prompt stating what the recording is for, how long it
   will be retained, and that the user can delete it at any time. Recording only begins after
   the user explicitly confirms. The 30-second sample is then sent to ElevenLabs, the returned
   voice ID is stored in the keystore, and the raw audio is discarded from the device.

---

### User Story 2 — Conversational AI Companion with Persistent Memory (Priority: P1)

A user chats with GURUJEE in the terminal. GURUJEE responds in its own voice and personality,
remembers what the user told it in previous sessions, and proactively references past context.
After a week away, GURUJEE still remembers the user's name, preferences, and prior conversations.

**Why this priority**: Core value proposition — without memory and personality, GURUJEE is
just another chatbot.

**Independent Test**: Tell GURUJEE a personal fact ("My son's name is Ali"), end the session,
start a new session, and ask "Do you remember my son's name?" — GURUJEE must answer correctly.

**Acceptance Scenarios**:

1. **Given** the user sends a message, **When** GURUJEE responds, **Then** the response
   reflects GURUJEE's defined personality (wise, concise, proactive) and addresses the user
   by name if known.

2. **Given** the user shared a personal fact in a previous session, **When** the user starts
   a new session days later, **Then** GURUJEE references that fact without being prompted.

3. **Given** the user asks GURUJEE to remember something explicitly ("Remember that I'm
   allergic to peanuts"), **When** the user asks about it in a future session, **Then**
   GURUJEE recalls it accurately and in context.

4. **Given** a conversation is in progress, **When** GURUJEE's context window approaches its
   limit, **Then** GURUJEE summarises and compresses older context without losing key memories.

5. **Given** the AI endpoint is unreachable mid-conversation, **When** the user sends a
   message, **Then** GURUJEE displays a clear error in the TUI, queues the message, and
   delivers it automatically when connectivity is restored — without the user re-sending.

---

### User Story 3 — Device Control via Chat (Priority: P1)

A non-technical user types "open WhatsApp" or "turn off WiFi" in the PWA chat interface.
GURUJEE parses the natural language command, converts it to a structured tool call via the
AI backend, and executes it on the phone using Shizuku (`rish`). The user never types a
shell command or sees a terminal.

**Why this priority**: Device automation is the differentiator between GURUJEE and a
regular chatbot. Without it, the "AI companion that can act" promise is undelivered.

**Independent Test**: With Shizuku active, type "open the camera app" in the chat UI.
Verify the camera app launches within 3 seconds.

**Acceptance Scenarios**:

1. **Given** the user types "open WhatsApp" in the chat, **When** GURUJEE processes the
   request, **Then** WhatsApp opens on the device within 3 seconds and GURUJEE confirms
   in the chat that it opened the app.

2. **Given** the user types "set volume to 50%", **When** GURUJEE processes the request,
   **Then** the media volume is set to 50% and GURUJEE confirms in the chat.

3. **Given** Shizuku is inactive, **When** the user sends an automation command,
   **Then** GURUJEE returns a friendly error in the chat ("I can't control your device
   right now — Shizuku is not active. Open the Shizuku app and tap 'Start'") and does
   not crash.

4. **Given** the automation command has ambiguous app name ("open messages"),
   **When** GURUJEE cannot uniquely resolve it, **Then** it asks the user to clarify
   ("Did you mean SMS Messages or Google Messages?").

---

### User Story 4 — PWA Chat Interface (Priority: P1)

A non-technical user taps the GURUJEE app icon, the PWA chat UI loads in the in-app
WebView, and they can chat with GURUJEE exactly like using WhatsApp — no terminal,
no commands, no configuration. The interface works offline after the first load.

**Why this priority**: This is the primary user-facing interface per constitution P5/P6
and ADR-003. Without it, GURUJEE is inaccessible to non-technical users.

**Independent Test**: Open the PWA in a browser at `localhost:7171`. Send a message.
Verify it streams token-by-token. Disable network; reload — PWA must load from cache.

**Acceptance Scenarios**:

1. **Given** the daemon is running, **When** the user opens `localhost:7171`,
   **Then** the chat UI loads within 2 seconds and shows the conversation history.

2. **Given** a user sends a message, **When** the AI responds, **Then** tokens appear
   in the chat bubble one by one (SSE streaming) with no full-page reload.

3. **Given** network is disabled after the first load, **When** the user opens the PWA,
   **Then** it loads from the service worker cache and shows a "You're offline — messages
   will send when reconnected" banner.

4. **Given** the user is on the agent status view, **When** an agent crashes and restarts,
   **Then** the status bar updates in real time (WebSocket /ws) without a page refresh.

---

### User Story 5 — Background Daemon Auto-Start (Priority: P1)

A user turns on their phone. Without opening anything, GURUJEE's daemon starts
automatically via Termux:Boot. When they tap the GURUJEE APK icon, the Launcher shows a
loading screen while the daemon reaches ready state, then loads the PWA chat UI directly.
The user never opens a terminal.

**Why this priority**: Reliability and always-on availability are core promises.
A system that requires manual startup every boot is not an AI companion.

**Independent Test**: Reboot the device with Termux:Boot installed and configured.
After boot, wait 60 seconds. Tap the GURUJEE APK. The PWA must load within 5 seconds
without any terminal interaction.

**Acceptance Scenarios**:

1. **Given** the device reboots, **When** Termux:Boot fires, **Then** `gateway_daemon.py`
   starts in headless mode, all 6 agents initialize, and the server is ready on
   `localhost:7171` within 60 seconds.

2. **Given** the daemon is starting, **When** the user opens the Launcher APK,
   **Then** a progress screen shows a meaningful status message (not a blank screen)
   and transitions to the PWA WebView when `GET /health` returns `{"status": "ready"}`.

3. **Given** the daemon fails to start within 3 minutes, **When** the Launcher times out,
   **Then** a retry button is shown with a diagnostic message (not a crash or blank screen).

4. **Given** the boot script fails (e.g., Python not installed), **When** Termux:Boot
   fires, **Then** the failure is logged to `data/boot.log` and the APK shows a helpful
   error on next open.

---

### Edge Cases

- What happens if the AI endpoint (`gen.pollinations.ai`) is unreachable? GURUJEE queues
  the message, shows an error in the TUI chat panel, and retries automatically when the
  connection restores. The daemon does not crash.
- What happens if the phone runs out of storage during dependency installation? Setup detects
  the disk space issue before failing and guides the user to free space.
- What happens if Shizuku is deactivated after initial setup (e.g., after phone reboot)?
  GURUJEE detects this and warns the user; device automation commands are not present until
  Phase 3, but the warning is surfaced immediately.
- What happens if the AI endpoint returns a malformed response or times out mid-conversation?
  GURUJEE surfaces a graceful error to the user and remains stable; the daemon does not crash.
- What happens if the SQLite memory database (`data/memory.db`) is corrupted? GURUJEE starts
  with a fresh database and notifies the user, rather than crashing on launch. The corrupted
  file is renamed to `data/memory.db.corrupt.<timestamp>` for manual recovery.
- What happens if the weekly backup fails (e.g., `data/backups/` is not writable)? GURUJEE
  logs the failure to `data/memory.log` and continues operating; backup failure is never
  a blocking error.
- What happens if the user denies the voice cloning consent prompt? Setup marks the
  `voice_sample` step as skipped in `data/setup_state.yaml` and continues. Voice cloning
  will not be available in Phase 2 until the user records a sample via Settings.
- What happens if an AI response stream is interrupted mid-delivery (e.g., network drop)?
  The partial text already rendered in the Chat screen gains an `[interrupted]` suffix.
  The partial content is written to `data/memory.db`. The pending request is queued and
  retried automatically when connectivity restores (per FR-014).
- What happens if the user enters the wrong keystore PIN three times? GURUJEE locks for
  30 seconds (exponential backoff on further failures). The "Forgot PIN?" option is displayed,
  which — after explicit user confirmation of the consequence — wipes `data/gurujee.keystore`
  and re-launches guided setup to re-enter all credentials.

---

## Requirements *(mandatory)*

### Functional Requirements

**Onboarding & Setup**

- **FR-001**: On first launch, GURUJEE MUST run a guided terminal setup that executes all of
  these steps in order:
  1. Install required packages.
  2. Activate Shizuku.
  3. Install the GURUJEE Accessibility Service APK — downloaded exclusively from the official
     GURUJEE GitHub Releases page. The guided setup MUST display the exact URL and SHA-256
     checksum before installation begins. No APK MAY be sideloaded from any other source.
  4. Grant Android permissions in one batch.
  5. Set keystore PIN: the user chooses a 4–8 digit PIN. The PIN is never stored; it is the
     PBKDF2-HMAC-SHA256 input for keystore key derivation. The setup MUST display the
     "Forgot PIN" consequence (keystore wipe + re-run setup) at this step.
  6. Configure AI model (selection written to `data/user_config.yaml`).
  7. Voice sample recording (optional — skippable): GURUJEE MUST display a consent prompt
     stating what the recording is for, how long it will be retained, and that the user can
     delete it at any time. Recording MUST NOT begin until the user explicitly confirms.
     The 30-second sample is sent to ElevenLabs; the returned voice ID is stored in the
     keystore; the raw audio is discarded from the device immediately.
  8. Start all daemons.
  All steps execute entirely within the Termux terminal.
- **FR-002**: Setup state MUST be persisted to `data/setup_state.yaml` so that an interrupted
  setup resumes from its last completed step on next launch.
- **FR-003**: After a device reboot, all always-on daemons (soul, memory, heartbeat,
  user_agent, cron, automation) MUST restart automatically without user intervention.
  Termux:Boot launches `gateway_daemon.py` in headless mode; the daemon is ready before
  the Launcher APK loads the PWA WebView. In Phase 1, the cron daemon starts dormant with
  an empty job schedule; it exposes `add_job()` and `list_jobs()` interfaces but no jobs
  are registered until Phase 2.

**Soul & Identity**

- **FR-004**: GURUJEE MUST maintain a defined personality (wise, concise, proactive) encoded
  in a system prompt that the Soul Agent injects into every AI conversation.
- **FR-005**: GURUJEE's identity and personality configuration MUST persist across reboots in
  `data/soul_identity.yaml` (initialized from the shipped template `agents/soul_identity.yaml`
  on first run). The user MUST be able to edit this file through the Settings panel in the TUI
  without manually editing the file.

**Memory**

- **FR-006**: Short-term conversation context (current session, last 10 turns) MUST be held
  in RAM and injected automatically into every AI request.
- **FR-007**: Long-term memories MUST be stored in `data/memory.db` (SQLite) and retrieved by
  keyword/tag matching for each conversation turn (see ADR-002).
- **FR-008**: When the user explicitly asks GURUJEE to remember something, it MUST be written
  to `data/memory.db` immediately and confirmed to the user in the chat panel.
- **FR-009**: When context approaches the AI model's context limit, GURUJEE MUST summarise and
  compress older context without discarding explicitly-saved long-term memories.
- **FR-021**: `data/memory.db` MUST be automatically backed up weekly to `data/backups/`
  with a timestamped filename. Backup failures MUST be logged but MUST NOT block normal
  operation.

**Gateway Daemon & Heartbeat**

- **FR-010**: A gateway daemon MUST manage all always-on agents as long-lived asyncio tasks
  and route messages between them via an internal message bus (asyncio Queue).
- **FR-011**: The heartbeat agent MUST monitor all always-on agents, automatically restart
  any that have stopped or errored within 10 seconds, and log restart events to
  `data/heartbeat.log`.

**AI Backend**

- **FR-012**: All AI inference MUST route through the provider catalogue defined in
  `config/models.yaml` (ADR-005). The default zero-key provider is `pollinations`
  (`base_url: https://gen.pollinations.ai/v1`, OpenAI-compatible). Any provider entry
  in the catalogue is permitted. Model references MUST use the `provider/model-id` format
  (e.g. `pollinations/nova-fast`). No endpoint URL MUST be hardcoded in logic.
- **FR-013**: The available AI models MUST be defined in the version-controlled
  `config/models.yaml`. The user's active model selection MUST be stored in
  `data/user_config.yaml` under the `active_model` key; the default is
  `pollinations/nova-fast` (`provider/model-id` format per P2 v1.2.0).
  No model ID MUST be hardcoded in logic.
- **FR-014**: When the AI endpoint is unreachable, GURUJEE MUST display a clear error
  message in the TUI chat panel, queue the pending request, and automatically resend it
  when connectivity to the endpoint is restored — without requiring user action.

**Device Automation via Chat (Phase 1)**

- **FR-024**: GURUJEE MUST accept natural-language automation commands from the PWA chat
  interface and execute them on the device via Shizuku shell commands (`rish`). The AI MUST
  convert the natural-language input to a structured tool call (OpenAI function-calling
  format), which `ToolRouter` dispatches to the correct action handler.
- **FR-025**: The following automation actions MUST be supported in Phase 1:
  open app by name (`am start`), set volume level, toggle WiFi/Bluetooth/flashlight,
  one-shot SMS sending via Termux:API (user explicitly requests "send SMS to X saying Y"),
  set alarm, read latest notifications, take screenshot. Automated SMS auto-reply and
  polling are Phase 2 (002-gurujee-comms); only user-initiated one-shot SMS is Phase 1.
- **FR-026**: When Shizuku (`rish`) is unavailable, GURUJEE MUST return a graceful error
  to the user in the chat UI and surface `"warnings": ["shizuku_inactive"]` in GET `/health`.
  Automation commands MUST NOT crash the daemon if Shizuku is not active.

**PWA Chat UI — Primary User Interface (Phase 1)**

> The primary user-facing interface is the **PWA chat UI**, not the Textual TUI.
> The Textual TUI is a **developer/admin tool** launched with `python -m gurujee --tui`.
> Non-technical users never see a terminal (see ADR-003, constitution P5/P6).

- **FR-015**: The FastAPI server MUST serve a PWA chat UI from `localhost:7171` that
  provides a WhatsApp-style conversation interface. AI responses MUST stream token-by-token
  via the `/chat` SSE endpoint as they arrive. A typing indicator MUST appear while
  streaming is in progress. On network interruption mid-stream, the partial response MUST
  be shown with an `[interrupted]` suffix, and the partial content MUST be logged to
  `data/memory.db`. On streaming completion the full message is written to `data/memory.db`.
  The PWA MUST work fully offline after first load via a service worker cache.
- **FR-016**: The PWA MUST provide an agent status bar showing each always-on agent's name
  and current state (green = running / amber = degraded / red = stopped) updated in real
  time via the WebSocket `/ws` endpoint.
- **FR-017**: The PWA MUST provide a Settings view exposing AI model selection
  (reads/writes `data/user_config.yaml`), soul identity editing (reads/writes
  `data/soul_identity.yaml`), and placeholders for Phase 2 settings (Calls > Auto-Answer,
  SMS) that are visible but inactive until Phase 2.
- **FR-018**: The PWA MUST be responsive (interaction-to-render under 100 ms) at all times,
  including while an AI endpoint call is in-flight. The Textual developer TUI MUST also
  be responsive (keystroke-to-render under 100 ms) when running in `--tui` mode.

**Security & Credentials**

- **FR-019**: All secrets (ElevenLabs voice ID, SIP credentials when added in Phase 2) MUST
  be stored exclusively in an AES-256-GCM encrypted keystore at `data/gurujee.keystore`.
- **FR-020**: Credentials MUST never appear in source code, configuration files, or logs.
- **FR-022**: The network allowlist MUST be built dynamically at daemon startup by reading
  all `base_url` fields from `config/models.yaml` (all active providers) plus the four
  security-anchor hosts from `config/security.yaml` (`api.elevenlabs.io`, `sip.suii.us`,
  `stun.l.google.com`, `api.deepgram.com`). Any outbound connection to a host not in this
  derived list MUST raise `AllowlistViolation` and be blocked unless the user explicitly
  approves it via the PWA settings UI. User-added custom providers are automatically added
  to the allowlist on save.
- **FR-023**: On every GURUJEE launch after initial setup, the TUI MUST prompt the user for
  their keystore PIN before the daemon starts. Three consecutive wrong attempts MUST trigger a
  30-second lockout with exponential backoff on subsequent failures. The PIN prompt MUST
  display a "Forgot PIN?" option that clearly states the consequence (keystore wipe + guided
  setup must be re-run to re-enter all credentials) before allowing the wipe to proceed.

---

### Key Entities

- **Soul**: Named AI identity; personality and system prompt template persisted in
  `data/soul_identity.yaml` (gitignored; initialized from shipped template
  `agents/soul_identity.yaml` on first run). Loaded by the Soul Agent on daemon startup.
  Editable via the TUI Settings panel.
- **Memory Record**: SQLite row in `data/memory.db` with id, content, tags
  (comma-separated), importance score, and created_at timestamp. Retrieval via keyword/tag
  matching (ADR-002). Database auto-backs up weekly to `data/backups/`.
- **Agent**: Long-lived asyncio task identified by name, with state (running/stopped/error)
  and an asyncio Queue inbox. Agents communicate only via the message bus.
- **GatewayDaemon**: Supervisor that starts, monitors, and restarts all always-on agents.
  Entry point for the GURUJEE process.
- **Keystore**: AES-256-GCM encrypted blob at `data/gurujee.keystore`; key derived from
  device fingerprint + user PIN (4–8 digits, set during guided setup, never stored).
  Decrypted in memory only for the duration of use; zeroed on lock. Three wrong PIN
  attempts trigger a 30-second lockout with exponential backoff. Forgot-PIN path: wipe
  keystore + re-run guided setup. Stores: ElevenLabs voice ID (Phase 1), SIP credentials
  (Phase 2).
- **CronDaemon**: Always-on dormant agent in Phase 1. Starts with the gateway on every boot,
  holds an empty job schedule, and exposes `add_job()` / `list_jobs()` interfaces. Phase 2
  registers the first jobs without any daemon wiring.
- **SetupState**: YAML document at `data/setup_state.yaml` tracking completion of each
  guided-setup step for resumption after interruption. Fields:
  `packages: bool`, `shizuku: bool`, `accessibility_apk: bool`, `permissions: bool`,
  `keystore_pin_set: bool`, `ai_model: bool`, `voice_sample: bool` (optional, skippable),
  `daemons: bool`. Setup is not considered complete until `keystore_pin_set` is `true`.
- **AutomationAgent**: Always-on Phase 1 agent supervised by GatewayDaemon. Receives
  natural-language automation intents from the message bus, calls the AI backend to
  convert them to structured tool calls, and dispatches to `ToolRouter` for Shizuku
  execution. Exposes the `/automate` REST endpoint.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user completes the entire guided setup on a fresh Android device in
  under 10 minutes, with no external documentation required.
- **SC-002**: GURUJEE correctly recalls any personal fact that the user explicitly asked it
  to remember, in 100% of test cases across sessions.
- **SC-003**: GURUJEE's first response to a chat message is delivered within 5 seconds on a
  3G connection to the AI endpoint.
- **SC-004**: The TUI remains responsive (keystroke-to-render under 100 ms) while an AI
  inference call is simultaneously in-flight.
- **SC-005**: GURUJEE's idle RAM footprint (all always-on daemons running, no active call)
  stays under 50 MB on a device with 3 GB RAM.
- **SC-006**: After a device reboot, all daemons are running and GURUJEE responds to chat
  within 60 seconds of the user opening Termux.
- **SC-007**: A daemon that crashes is detected and restarted by the heartbeat agent within
  10 seconds, with no user intervention required.
- **SC-008**: An interrupted guided setup resumes from its last completed step in 100% of
  test cases (no step is repeated unnecessarily).
- **SC-009**: A queued message (sent while AI endpoint was unreachable) is delivered
  automatically within 5 seconds of the endpoint becoming reachable again.

---

## Assumptions

- The user's Android device has at least 3 GB RAM and 1 GB free storage.
- Termux is installed from F-Droid (not Play Store) to allow background process execution.
- The AI endpoint (`gen.pollinations.ai`) does not require authentication for Phase 1; if
  this changes, it constitutes a P2 violation requiring a constitution amendment.
- Shizuku activation and device automation (AutomationAgent + ShizukuExecutor) are both
  Phase 1 scope. Automation was originally planned for Phase 3 but was moved forward
  during Phase 1 implementation (see ADR-003 and ADR-004); all 66 foundation tasks include
  automation work.
- The GURUJEE Accessibility Service APK is installed during Phase 1 setup and used by
  AutomationAgent for accessibility-based UI actions (supplementary to Shizuku shell).
- Voice sample recording in the guided setup is optional and skippable; voice cloning
  (ElevenLabs instant clone API call) happens in Phase 2 TTS. Phase 1 only captures the
  raw sample and stores the resulting voice ID.
- Memory retrieval uses keyword/tag search with no embedding model in v1, per ADR-002.
- Termux:API companion app IS required for Phase 1 one-shot SMS sending (FR-025).
  Automated SMS auto-reply and polling are Phase 2 (002-gurujee-comms).
- The Settings panel in Phase 1 exposes soul identity editing (`data/soul_identity.yaml`)
  and AI model selection (written to `data/user_config.yaml`); Calls and SMS settings are
  visible but inactive scaffolding for Phase 2.
- Canonical config/data paths: `config/models.yaml`, `config/agents.yaml`, and
  `config/voice.yaml` are version-controlled; `data/user_config.yaml`, `data/soul_identity.yaml`,
  `data/setup_state.yaml`, `data/memory.db`, and `data/gurujee.keystore` are gitignored runtime
  files. No other config paths are permitted (P10).
