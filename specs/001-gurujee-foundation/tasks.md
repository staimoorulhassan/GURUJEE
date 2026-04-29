---
description: "Task list for GURUJEE Foundation — Phase 1 (v3: PWA + Automation + Launcher APK architecture)"
---

# Tasks: GURUJEE Foundation

**Input**: Design documents from `/specs/001-gurujee-foundation/`
**Branch**: `001-gurujee-foundation`
**Generated**: 2026-04-12
**Architecture**: Split-layer — Python daemon (asyncio) + FastAPI server + PWA static UI (ADR-003 v2)

**User Stories from spec.md**:
- **US1** — First-Time Setup and Onboarding (Priority: P1) 🎯 MVP Entry Gate
- **US2** — Conversational AI Companion with Persistent Memory (Priority: P1) 🎯 Core Value

**New architecture components (2026-04-12 decisions)**:
- **US3** — Device Control via Chat (Priority: P1) — OpenClaw-equivalent device control
- **US4** — FastAPI Server + PWA Chat UI (Priority: P1) — non-technical user interface
- **US5** — Background Daemon Auto-Start (Launcher APK) (Priority: P1) — zero-touch setup for non-technical users

**Tests**: Included per spec FR requirements and constitution P10 (70% coverage target).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository structure, package scaffolding, config files, and gitignore.
No user story work begins here.

- [X] T001 Create full directory tree per plan.md: `gurujee/`, `agents/`, `config/`, `data/`, `tests/`, `launcher/`, `gurujee/server/static/`, `gurujee/automation/actions/`
- [X] T002 Write `pyproject.toml` with package metadata, pytest config (asyncio_mode=auto, testpaths=tests, cov target 70%), and dependency list matching requirements.txt
- [X] T003 [P] Update `requirements.txt` — add `fastapi>=0.110`, `uvicorn>=0.29`, `httpx>=0.25`, `python-multipart>=0.0.9` alongside existing deps
- [X] T004 [P] Write `.gitignore` — exclude `data/`, `*.keystore`, `*.log`, `__pycache__/`, `*.pyc`, `.env`, `launcher/bin/`, `launcher/.buildozer/`
- [X] T005 [P] Write `config/models.yaml` — full provider catalogue per ADR-005: `builtin_providers` tier (pollinations as default zero-key provider with its 6 models, plus anthropic/openai/google/etc with `auth_env` fields), `custom_providers` tier (ollama, openrouter, litellm, deepseek, groq, mistral, etc with `base_url`), `agent_model_routing` map (all 6 agents → `pollinations/nova-fast`), `failover` config, `transcription_providers`, `image_providers`. Default: `pollinations/nova-fast` (`provider/model-id` format). All API keys referenced by `auth_env` keystore key name — never stored in this file.
- [X] T006 [P] Write `config/agents.yaml` — heartbeat interval: 30s, ping timeout: 5s, max restart count: 10, memory short_term_maxlen: 10, log rotation: 5MB×3
- [X] T007 [P] Write `config/voice.yaml` — provider: elevenlabs, model: turbo, streaming: true, sample_duration_seconds: 30
- [X] T008 [P] Write `config/automation.yaml` — shizuku_rish_path: `/data/user/0/moe.shizuku.privileged.api/rish`, action_timeout_seconds: 10, screenshot_path: `/data/data/com.termux/files/home/gurujee_screenshot.png`
- [X] T009 [P] Write `agents/soul_identity.yaml` — template: name GURUJEE, tagline, personality_traits, language_style, system_prompt_template with `{name}` `{user_name}` `{date}` `{traits_joined}` placeholders, voice_id: null
- [X] T010 Write `tests/conftest.py` — fixtures: `tmp_data_dir`, `mock_message_bus`, `mock_ai_client` (returns fixed stream), `mock_keystore`, `async_client` (httpx TestClient for FastAPI app), `mock_shizuku_executor`

**Checkpoint**: Repo structure and config files exist. `pytest --collect-only` runs with 0 errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure every user story depends on — message bus, BaseAgent, config
loader, keystore module, SQLite schema, AI client. MUST be 100% complete before any story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

MARK_DONEImplement `gurujee/config/loader.py` — `ConfigLoader` class: `load_yaml(path)` (PyYAML), `save_yaml(path, data)`, `load_ruamel(path)` (ruamel.yaml for soul_identity), `save_ruamel(path, data)`, `load_models()`, `load_agents()`, `get_user_config()`, `save_user_config(data)`, `init_user_config()` with defaults; all paths via `pathlib.Path`
MARK_DONE[P] Implement `gurujee/agents/base_agent.py` — `MessageType` enum (12 types from contracts/message-bus.md: CHAT_REQUEST, CHAT_RESPONSE, CHAT_STREAM_CHUNK, MEMORY_STORE, MEMORY_RETRIEVE, MEMORY_RESULT, HEARTBEAT_PING, HEARTBEAT_PONG, AGENT_STATUS, AGENT_RESTART, AUTOMATE_REQUEST, AUTOMATE_RESULT), `Message` dataclass (id UUID4, from_agent, to_agent, type, payload dict, timestamp, reply_to, ttl=10), `MessageBus` class with `asyncio.Queue` per agent and `send(msg)` / `subscribe(agent_name)` methods, `BaseAgent` ABC with `name`, `inbox: asyncio.Queue`, `bus: MessageBus`, abstract `run()` coroutine, `handle_message(msg)`, `start()`, `stop()` lifecycle methods
MARK_DONE[P] Implement `gurujee/keystore/keystore.py` — `Keystore` class per contracts/keystore-api.md: `__init__(path, data_dir)`, `create(pin)` derives 32-byte key via PBKDF2-HMAC-SHA256 (iterations=480_000, salt=device_fingerprint[:16] fallback to `.device_salt`), encrypts empty JSON blob with AES-256-GCM (nonce 12B ‖ ciphertext ‖ tag 16B), `unlock(pin)` with 3-attempt lockout + 30s exponential backoff, `lock()` zeroes key bytearray, `get(key)`, `set(key, value)`, `wipe()`, `is_locked` property; PIN never stored; raw binary on-disk format
MARK_DONEImplement `gurujee/memory/long_term.py` — `LongTermMemory` class: `init_db(path)` creates tables `memories`, `automation_log`, `notification_cache` with all columns per data-model.md, enables WAL mode, creates all indices; `store_memory(content, tags, category, importance, source)`, `retrieve_memories(query, limit=5)` using ADR-002 hybrid SQL; `log_automation(command_type, input_text, action_json, status, error_message, duration_ms)`, `prune_automation_log(max_entries=500)`; `cache_notifications(notifs)`, `get_notifications(limit=20)`, `prune_notification_cache(max_entries=100)`; `backup(backups_dir)` weekly copy with timestamp; `handle_corruption(path)` renames to `.corrupt.<timestamp>` and returns fresh path
MARK_DONE[P] Implement `gurujee/memory/short_term.py` — `ShortTermMemory` class: `deque(maxlen=10)` of `ConversationTurn` dataclasses (role, content, timestamp); `add(role, content)`, `to_messages()` → list of `{"role": ..., "content": ...}` dicts for OpenAI API; `serialize(path)` → YAML to `data/session_context.yaml`; `deserialize(path)` on startup; `summarize_to_long_term(long_term_memory)` called when context limit approached
MARK_DONEImplement `gurujee/ai/client.py` — `AIClient` class: `__init__(config_loader, keystore)`, `AsyncOpenAI(base_url="https://gen.pollinations.ai/v1", api_key="")`, `_active_model()` reads from `data/user_config.yaml`; `stream_chat(messages, on_chunk)` async generator using `client.chat.completions.create(stream=True)` with tenacity retry (3 attempts, 2s wait, on `openai.APIConnectionError`); network allowlist check before every call (only `gen.pollinations.ai` and `api.elevenlabs.io` permitted); `AUTOMATE` tool call support: parse `tool_calls` from stream chunks; queue pending requests on unreachable endpoint and auto-retry when connection restores
MARK_DONEWrite `tests/test_keystore.py` — test create+unlock roundtrip, wrong PIN lockout (3 attempts → 30s), forgot-PIN wipe, key derivation determinism, in-memory-only key after unlock, wipe removes file
MARK_DONE[P] Write `tests/test_ai_client.py` — mock `AsyncOpenAI` responses fixture; test streaming chunks delivered in order, retry on connection error (3 attempts), allowlist blocks unknown host, active model read from config, tool_calls parsed from stream

**Checkpoint**: Foundation complete. `pytest tests/test_keystore.py tests/test_ai_client.py` passes. `from gurujee.agents.base_agent import BaseAgent, MessageBus, Message, MessageType` imports cleanly.

---

## Phase 3: User Story 1 — First-Time Setup and Onboarding (Priority: P1) 🎯 MVP Entry Gate

**Goal**: User (technical: `install.sh`; non-technical: Launcher APK) completes full guided setup
and GURUJEE reaches "ready" state with all daemons running and `localhost:7171/health` responding.

**Independent Test**: Run `python -m gurujee.setup` on a clean `data/` directory. Verify
`data/setup_state.yaml` reaches `completed_at: <timestamp>` with all required steps marked
`completed: true`. Then run `python -m gurujee --headless` and verify `GET /health` → `{"status":"ready"}`.

### Implementation for User Story 1

- [X] T019 [US1] Implement `gurujee/setup/wizard.py` — `SetupWizard` class with `run()` entry point; loads/creates `data/setup_state.yaml` on start; skips already-completed steps; 8 steps as methods: `_step_packages()` (`pkg install -y python git termux-api` via subprocess), `_step_shizuku()` (activation instructions + `rish` binary verification), `_step_accessibility_apk()` (GitHub Releases URL + SHA-256 display + download + verify + `am start` sideload; skippable), `_step_permissions()` (`termux-setup-storage` + guided Android permission grants with re-check), `_step_keystore_pin()` (PIN prompt 4–8 digits, confirm, display "Forgot PIN" consequence, `Keystore.create(pin)`; cannot skip), `_step_ai_model()` (model list from `config/models.yaml`, writes to `data/user_config.yaml`), `_step_voice_sample()` (consent prompt → `termux-microphone-record` → ElevenLabs → store voice_id in keystore → discard audio; skippable), `_step_daemons()` (create `~/.termux/boot/start-gurujee.sh`, start daemon subprocess, poll `localhost:7171/health` max 60s)
- [X] T020 [US1] Implement `gurujee/__main__.py` — argparse: `--headless` (default, runs daemon + server), `--tui` (adds Textual), `--setup` (runs wizard only); PIN prompt on every launch after setup via `Keystore.unlock(pin)` before daemon start; calls `asyncio.run(GatewayDaemon().start())` for headless mode
- [X] T021 [US1] Update `install.sh` — idempotent bootstrap: `pkg update -y && pkg upgrade -y`, `pkg install -y python git termux-api`, clone/pull repo, `pip install -r requirements.txt`, check `data/setup_state.yaml` for completion, if not complete run `python -m gurujee.setup`, if complete run `python -m gurujee --headless`
- [X] T022 [US1] Write `tests/test_setup_wizard.py` — mock `subprocess`, mock ElevenLabs call, mock keystore; test: fresh start runs all 8 steps, interrupted setup resumes from last step, voice sample step skipped when declined, setup_state.yaml written correctly after each step, PIN step cannot be skipped

**Checkpoint (US1)**: `python -m gurujee.setup` completes on clean data dir. `data/setup_state.yaml` shows all required steps complete. `GET http://localhost:7171/health` → `{"status":"ready"}`.

---

## Phase 4: User Story 2 — Conversational AI Companion with Persistent Memory (Priority: P1)

**Goal**: User sends a message. GURUJEE responds with its defined personality, remembers facts
across sessions, queues messages when offline, and streams responses in real time.

**Independent Test**: `POST /chat {"message":"My son's name is Ali"}` → streaming response.
Stop daemon. Start daemon. `POST /chat {"message":"Do you remember my son's name?"}` → response
contains "Ali".

### Implementation for User Story 2

- [X] T023 [US2] Implement `gurujee/agents/soul_agent.py` — `SoulAgent(BaseAgent)`: loads `data/soul_identity.yaml` (initialises from `agents/soul_identity.yaml` template on first run); builds system prompt from `system_prompt_template` with `{name}`, `{user_name}`, `{date}`, `{traits_joined}` substitution; handles `CHAT_REQUEST`: injects system prompt + short-term context, calls `AIClient.stream_chat()`, publishes `CHAT_STREAM_CHUNK` per token and final `CHAT_RESPONSE`; detects "remember" intent and publishes `MEMORY_STORE`; on endpoint unreachable: publishes error chunk, queues request, auto-retries
- [X] T024 [US2] Implement `gurujee/agents/memory_agent.py` — `MemoryAgent(BaseAgent)`: initialises `ShortTermMemory` and `LongTermMemory` on start; loads `data/session_context.yaml` if exists; handles `MEMORY_STORE` (writes to SQLite, publishes confirmation); handles `MEMORY_RETRIEVE` (keyword/tag query, publishes `MEMORY_RESULT`); on every `CHAT_REQUEST` prepends relevant memories; on `CHAT_RESPONSE` appends to deque, calls `summarize_to_long_term()` if context limit near; serialises short-term on `stop()`; schedules weekly backup via asyncio task
- [X] T025 [US2] Implement `gurujee/agents/heartbeat_agent.py` — `HeartbeatAgent(BaseAgent)`: every 30s sends `HEARTBEAT_PING` to each always-on agent; awaits `HEARTBEAT_PONG` within 5s; on timeout publishes `AGENT_RESTART` to gateway; logs restart events to `data/heartbeat.log` via `RotatingFileHandler(5MB×3)`
- [X] T026 [US2] Implement `gurujee/agents/user_agent.py` — `UserAgent(BaseAgent)`: reads `user_name` and `user_profile` from `data/soul_identity.yaml` (ruamel.yaml); publishes user profile on startup for SoulAgent name injection; handles profile update messages from Settings
- [X] T027 [US2] Implement `gurujee/agents/cron_agent.py` — `CronAgent(BaseAgent)`: Phase 1 dormant; loads `data/cron_jobs.yaml` (empty list); exposes `add_job(job_dict)` and `list_jobs()` via MessageBus; logs startup as dormant; no jobs scheduled in Phase 1
- [X] T028 [US2] Implement `gurujee/daemon/gateway_daemon.py` — `GatewayDaemon`: `__init__` creates `MessageBus`, instantiates all 6 agents; `start()` coroutine: unlocks keystore, starts uvicorn server task, starts all agent tasks via `asyncio.create_task()`, runs message routing loop; `_route_message(msg)` delivers to correct agent inbox or broadcasts; `_on_agent_failure(name, exc)` triggers heartbeat restart; `stop()` gracefully cancels all tasks; exposes `agent_states` dict and `ready: bool` flag for `/health` and `/agents` endpoints
- [X] T029 [US2] Write `tests/test_soul_agent.py` — mock MessageBus + AIClient; test: system prompt injected with name/date/traits, CHAT_REQUEST triggers stream, "remember" intent triggers MEMORY_STORE, stream interrupted → [interrupted] suffix published, endpoint unreachable → error chunk + request queued
- [X] T030 [P] [US2] Write `tests/test_memory_agent.py` — test: explicit remember written to SQLite, cross-session recall (deserialise session_context.yaml), context summarisation triggered at limit, weekly backup scheduled (mock asyncio), corrupted DB handled gracefully
- [X] T031 [P] [US2] Write `tests/test_heartbeat_agent.py` — test: ping sent to all agents every 30s, AGENT_RESTART published on pong timeout (5s), restart logged to heartbeat.log

**Checkpoint (US2)**: Tell GURUJEE "My son's name is Ali". Stop daemon. Start daemon. Ask "Do you remember my son's name?" — answer must contain "Ali". `GET /agents` shows all 6 agents RUNNING.

---

## Phase 5: User Story 4 — PWA Chat Interface (Priority: P1)

**Goal**: Non-technical user opens a WhatsApp-style chat interface in a WebView or browser.
Messages stream token-by-token. Agent status visible in a subtle status bar. Works offline
after first load via service worker.

**Independent Test**: Open `http://localhost:7171` in Chrome. Type a message. See streaming
response in chat bubbles. Disable network. Reload — PWA loads from service worker cache.

### Implementation for User Story 4

- [X] T032 [US4] Implement `gurujee/server/app.py` — `create_app(gateway: GatewayDaemon) → FastAPI`: creates FastAPI instance, mounts `StaticFiles` at `/static` pointing to `gurujee/server/static/`, registers all routers (chat, agents, automate, notifications, health), registers WebSocket endpoint `/ws`, sets CORS to `127.0.0.1` only, configures `uvicorn.Config(app, host="127.0.0.1", port=7171, loop="asyncio", workers=1)` and starts `Server.serve()` as asyncio task from `GatewayDaemon`
- [X] T033 [US4] Implement `gurujee/server/routers/chat.py` — `POST /chat`: accepts `{"message": str}`, publishes `CHAT_REQUEST` to MessageBus, subscribes to `CHAT_STREAM_CHUNK` and `CHAT_RESPONSE` replies, streams via `StreamingResponse(media_type="text/event-stream")`; chunk format: `data: {"chunk": "...", "done": false}\n\n`; final: `data: {"chunk": "", "done": true}\n\n`; error: `data: {"error": "...", "done": true}\n\n`; **interrupted-stream**: on network drop, client disconnect, or LLM error mid-stream, publish `CHAT_RESPONSE` on the bus with `payload.metadata.interrupted = True`; MemoryAgent persists partial content to `data/memory.db` with `[interrupted]` suffix appended; PWA renders partial text with ⚠ interrupted indicator
- [X] T034 [US4] Implement `gurujee/server/routers/health.py` — `GET /health`: returns `{"status": "ready", "agents": {name: status}}` when GatewayDaemon is fully started; `{"status": "starting"}` during startup; used by Launcher APK to poll readiness
- [X] T035 [US4] Implement `gurujee/server/routers/agents.py` — `GET /agents`: returns snapshot of all `AgentState` entries from `GatewayDaemon.agent_states` as JSON list `[{"name": str, "status": str, "restart_count": int, "last_error": str|null}]`
- [X] T036 [US4] Implement `gurujee/server/websocket.py` — `WebSocket /ws`: on connect registers client in `GatewayDaemon.ws_clients` set; on agent status change or automation result broadcasts JSON event to all connected clients; handles `ping`/`pong` keep-alive; removes client on disconnect
- [X] T037 [US4] Write `gurujee/server/static/index.html` — PWA shell: `<meta name="viewport" content="width=device-width,initial-scale=1">`, dark background `#0a0a0a`, `<div id="status-bar">` (subtle top bar, 28px height), `<div id="chat-container">` (scrollable message list), `<div id="input-area">` (textarea + send button + voice button), `<link rel="manifest" href="manifest.json">`, service worker registration script, `<script src="app.js">`
- [X] T038 [US4] Write `gurujee/server/static/style.css` — WhatsApp-style dark theme: background `#0a0a0a`, user message bubble `#1a1a2e` right-aligned, assistant bubble `#0d3b2e` left-aligned, automation result bubble `#1e1e3a` centre-aligned, amber accent `#f0a500`, orange `#ff6b00`, `font-family: system-ui`, bubble border-radius 18px, max-width 75%, status bar `background: #111`, mobile-first responsive, no external CSS imports
- [X] T039 [US4] Write `gurujee/server/static/app.js` — chat logic: `sendMessage()` posts to `/chat` then reads SSE stream via `fetch` + `ReadableStream`; appends tokens to current assistant bubble in real time; shows blinking cursor `|` while streaming; removes cursor on `done: true`; shows `[interrupted]` suffix on error event; `connectWebSocket()` opens `/ws`, handles `agent_status` events to update status bar colour (green=all running, amber=degraded, red=critical); `loadHistory()` from localStorage on page load; no external JS libraries
- [X] T040 [US4] Write `gurujee/server/static/sw.js` — service worker: `CACHE_NAME = "gurujee-v1"`; on `install`: cache `["/", "/app.js", "/style.css", "/manifest.json"]`; on `fetch`: cache-first for static assets (match by URL), network-first for `/chat`, `/agents`, `/ws` paths (pass through to network, no cache); `skipWaiting()` on activate
- [X] T041 [US4] Write `gurujee/server/static/manifest.json` — `name: "GURUJEE"`, `short_name: "GURUJEE"`, `start_url: "/"`, `display: "standalone"`, `background_color: "#0a0a0a"`, `theme_color: "#f0a500"`, `icons: [{src:"icon-192.png", sizes:"192x192"}, {src:"icon-512.png", sizes:"512x512"}]`
- [X] T042 [US4] Write `tests/test_server_chat.py` — use `httpx.AsyncClient(app=app, base_url="http://test")`; test: POST /chat streams SSE chunks in `data: {...}` format, `done:true` terminates stream, error response format on agent unavailable, GET /health returns `{"status":"ready"}` after daemon start, GET /agents returns list with 6 entries, WebSocket /ws receives agent_status event on mock status change

**Checkpoint (US4)**: Open `http://localhost:7171` in browser. Send "Hello". See streaming chat bubbles. Refresh with network disabled — page loads from service worker. Status bar shows agents running.

---

## Phase 6: User Story 3 — Device Control via Chat (Priority: P1)

**Goal**: User says "open WhatsApp", "set volume to 50%", "turn WiFi off", "what are my
notifications". GURUJEE executes via Shizuku shell commands and replies with results.

**Independent Test**: With Shizuku active, `POST /automate {"command": "open WhatsApp"}` →
WhatsApp opens on device. Check `data/memory.db` `automation_log` has 1 row with `status: success`.
Shizuku deactivated → friendly error in response, not a crash.

### Implementation for User Story 3

- [X] T043 [US3] Implement `gurujee/automation/executor.py` — `ShizukuExecutor` class: `_rish_path` from `config/automation.yaml`; `execute(cmd: str, timeout: int) → tuple[str, str, int]` runs `rish -c "<cmd>"` via `asyncio.create_subprocess_shell`, captures stdout/stderr, enforces timeout (raises `AutomationTimeoutError`); `is_available() → bool` checks rish binary exists and Shizuku running; on unavailable raises `ShizukuUnavailableError` with user-friendly message and re-activation steps
- [X] T044 [P] [US3] Implement `gurujee/automation/actions/apps.py` — `open_app(executor, package_name: str)`: runs `am start -n <package>/.MainActivity` with fallback to `am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -f 0x10200000 <package>`; `list_running_apps(executor)`: `dumpsys activity | grep mResumedActivity`; `resolve_package(app_name: str) → str`: maps common names to packages (`whatsapp`, `chrome`, `camera`, `settings`, `clock`, `messages`, `youtube`) extensible via config
- [X] T045 [P] [US3] Implement `gurujee/automation/actions/device.py` — `set_volume(executor, level: int)`: `media volume --set <level> --stream 3`; `get_volume(executor)`: `media volume --get --stream 3`; `set_wifi(executor, enabled: bool)`: `svc wifi enable/disable`; `set_bluetooth(executor, enabled: bool)`: `svc bluetooth enable/disable`; `set_flashlight(executor, enabled: bool)`: camera flash toggle via `cmd`; `set_brightness(executor, level: int)`: `settings put system screen_brightness <level>`
- [X] T046 [P] [US3] Implement `gurujee/automation/actions/input.py` — `tap(executor, x: int, y: int)`: `input tap <x> <y>`; `swipe(executor, x1, y1, x2, y2, duration_ms=300)`: `input swipe`; `type_text(executor, text: str)`: `input text "<text>"` (escape special chars); `key_event(executor, keycode: int)`: `input keyevent <keycode>`; `press_back(executor)`: shortcut for keyevent 4
- [X] T047 [P] [US3] Implement `gurujee/automation/actions/notifications.py` — `list_notifications(executor)`: `termux-notification-list` via subprocess (Termux:API, not Shizuku), parse JSON; `dismiss_notification(executor, notif_id)`: `termux-notification-remove <id>`; cache results in `notification_cache` table via `LongTermMemory.cache_notifications()`
- [X] T048 [P] [US3] Implement `gurujee/automation/actions/system.py` — `take_screenshot(executor)`: `screencap -p <path>` via Shizuku, returns path; `get_running_apps(executor)`: `dumpsys activity | grep mFocusedApp`
- [X] T049 [US3] Implement `gurujee/automation/tool_router.py` — `ToolRouter` class: defines OpenAI tool schemas for 5 categories (open_app, device_setting, ui_input, set_reminder, read_notifications) as `tools` list for AI function-calling; `route(tool_call_json: dict) → Coroutine` maps `function.name` to correct action function + executor; raises `AutomationError` for unknown tool name
- [X] T050 [US3] Implement `gurujee/agents/automation_agent.py` — `AutomationAgent(BaseAgent)`: initialises `ShizukuExecutor` and `ToolRouter`; handles `AUTOMATE_REQUEST`: calls `ToolRouter.route(tool_call)`, records to `automation_log` (success/failed/timeout), publishes `AUTOMATE_RESULT` with outcome and duration_ms; on `ShizukuUnavailableError` publishes friendly error with re-activation instructions; prunes `automation_log` to 500 entries on startup
- [X] T051 [US3] Implement `gurujee/server/routers/automate.py` — `POST /automate`: accepts `{"command": str}`, publishes `AUTOMATE_REQUEST` to AutomationAgent via MessageBus, awaits `AUTOMATE_RESULT` reply (timeout 15s), returns `{"success": bool, "result": str, "command_type": str, "duration_ms": int}`
- [X] T052 [US3] Implement `gurujee/server/routers/notifications.py` — `GET /notifications`: reads latest 20 rows from `notification_cache`; `POST /notifications/refresh`: triggers `AUTOMATE_REQUEST` for notification fetch, returns fresh list
- [X] T053 [US3] Update `gurujee/ai/client.py` — integrate `ToolRouter.tools` list into every `chat.completions.create()` call as `tools=` parameter; when AI returns `tool_calls` in stream chunk, emit as `AUTOMATE_REQUEST` message instead of text; handle parallel tool calls (up to 4 per response per ADR-001)
- [X] T054 [US3] Update `gurujee/server/static/app.js` — handle `automate_result` WebSocket event: render automation result as system bubble with distinct colour `#1e1e3a`; on `shizuku_unavailable` error show banner with re-activation steps link; update status bar with automation state indicator
- [X] T055 [US3] Write `tests/test_automation_agent.py` — mock `ShizukuExecutor`; test: AUTOMATE_REQUEST dispatched to correct action, success logged to automation_log, timeout → status=timeout in log, Shizuku unavailable → friendly error published, automation_log pruned to 500 on startup
- [X] T056 [P] [US3] Write `tests/test_automation_actions.py` — mock executor; test each action: open_app resolves package + builds correct `am start` command, set_volume calls correct `media volume` command, tap/swipe produce correct `input` commands, list_notifications parses Termux:API JSON output
- [X] T057 [P] [US3] Write `tests/test_server_automate.py` — POST /automate with mock AutomationAgent; test: success response format, timeout response, Shizuku unavailable response, GET /notifications returns cached rows, POST /notifications/refresh triggers refresh

**Checkpoint (US3)**: Shizuku active → `POST /automate {"command": "open WhatsApp"}` → WhatsApp opens. `GET /notifications` → notification list. `automation_log` table has entries. Shizuku deactivated → friendly error in PWA, daemon stays running.

---

## Phase 7: User Story 5 — Background Daemon Auto-Start (Launcher APK) (Priority: P1)

**Goal**: Non-technical user taps GURUJEE.apk on a fresh Android device (no Termux pre-installed).
Sees progress screen. Within 3 minutes, sees PWA chat UI in WebView. Sends a message.

**Independent Test**: Install launcher APK on a fresh Android device. Tap GURUJEE icon. Within
3 minutes, see the chat UI. Send a message. Receive a streaming response.

### Implementation for User Story 5

- [X] T058 [US5] Implement `launcher/bootstrap.py` — `check_termux_installed() → bool`: `pm list packages | grep com.termux`; `install_termux()`: `pm install -r /sdcard/DCIM/termux.apk` (APK bundled in launcher assets, copied to sdcard on first run); `check_termux_api_installed() → bool`; `install_termux_api()`; `inject_bootstrap(script_path: str)`: uses `am start -n com.termux/.app.TermuxActivity --es com.termux.app.RUN_COMMAND_PATH "<script>" --ez com.termux.app.RUN_COMMAND_SESSION_ACTION 0` to inject and run bootstrap; `poll_daemon_ready(timeout_seconds=180) → bool`: GET `http://localhost:7171/health` every 3s until `status=="ready"` or timeout
- [X] T059 [US5] Implement `launcher/main.py` — Kivy `App` subclass `GurujeeApp`: `build()` returns `ScreenManager` with `ProgressScreen` and `WebViewScreen`; `ProgressScreen`: `ProgressBar` widget + `Label` for status messages ("Installing Termux…", "Starting GURUJEE…", "Connecting…"); `WebViewScreen`: uses `android.webview.WebView` via `jnius` (`autoclass("android.webkit.WebView")`) to load `http://localhost:7171` with `setJavaScriptEnabled(True)`, `setDomStorageEnabled(True)`; `GurujeeApp.on_start()` launches `bootstrap` in `threading.Thread`; on `poll_daemon_ready()` success calls `Clock.schedule_once(switch_to_webview, 0)`
- [X] T060 [US5] Write `launcher/buildozer.spec` — `package.name = gurujee`, `package.domain = ai.gurujee`, `version = 1.0.0`, `requirements = python3,kivy,requests,jnius,android`, `android.permissions = INTERNET,REQUEST_INSTALL_PACKAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE`, `android.api = 34`, `android.minapi = 29`, `source.include_exts = py,apk,sh`, `android.copy_libs = 1`

**Checkpoint (US5)**: `buildozer android debug` completes without error. APK installs on Android 10+ device. Fresh device (no Termux) → tap APK → progress screen → chat UI loads → message works.

---

## Phase 8: Developer TUI (Dev Tool Only — `python -m gurujee --tui`)

**Purpose**: Textual TUI for developers and admins. Runs in same process as daemon via
`app.run_worker()`. Not part of non-technical user flow.

- [X] T061 Implement `gurujee/tui/app.py` — `GurujeeApp(App)`: `--tui` mode only; runs `GatewayDaemon` as `app.run_worker()` coroutine; tab navigation: F1=Chat, F2=Agent Status, F3=Settings; handles CTRL+C graceful shutdown
- [X] T062 [P] Implement `gurujee/tui/theme.py` — CSS constants: `BACKGROUND="#0a0a0a"`, `AMBER="#f0a500"`, `ORANGE="#ff6b00"`, `PANEL_BG="#1a1a1a"`, `USER_BUBBLE="#1a1a2e"`, `ASSISTANT_BUBBLE="#0d3b2e"`
- [X] T063 [P] Implement `gurujee/tui/screens/chat_screen.py` — `ChatScreen(Screen)`: scrollable `RichLog` for history; `Input` widget; sends `CHAT_REQUEST` to bus on Enter; appends `CHAT_STREAM_CHUNK` tokens in-place with blinking cursor indicator; shows `[interrupted]` on stream error; commits full message to display on `CHAT_RESPONSE`
- [X] T064 [P] Implement `gurujee/tui/screens/agent_status_screen.py` — `AgentStatusScreen(Screen)`: `DataTable` refreshed every 2s from `GatewayDaemon.agent_states`; columns: Name, Status (colour-coded: green=RUNNING, yellow=STARTING, red=ERROR), Restarts, Last Restart
- [X] T065 [P] Implement `gurujee/tui/screens/settings_screen.py` — `SettingsScreen(Screen)`: AI model selector (`Select` widget reads `config/models.yaml`, writes `data/user_config.yaml`); soul identity editor (`TextArea` reads/writes `data/soul_identity.yaml` via ruamel.yaml); Phase 2 stubs: "Calls > Auto-Answer" and "SMS Auto-Reply" visible but disabled with "(Phase 2)" label

**Checkpoint (TUI)**: `python -m gurujee --tui` opens Textual app. Chat works (tokens stream). Agent Status shows all 6 agents. Settings saves changes to YAML. TUI crash does not kill daemon (agents continue).

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Security hardening, RAM profiling, logging, error handling, and final integration.

- [X] T066 Add `RotatingFileHandler(maxBytes=5*1024*1024, backupCount=3)` to `data/heartbeat.log`, `data/memory.log`, `data/automation.log`, `data/server.log`, `data/boot.log` in each respective module; grep all Python files for `print(` and replace with logger calls
- [X] T067 [P] Verify network allowlist enforcement in `gurujee/ai/client.py` — `_build_allowlist()` reads `base_url` from every provider in `config/models.yaml` (builtin + custom), extracts hostnames, adds four security-anchor hostnames from `config/security.yaml` (`api.elevenlabs.io`, `sip.suii.us`, `stun.l.google.com`, `api.deepgram.com`), deduplicates, returns as `frozenset`; rebuilds on every daemon restart; non-allowlisted host raises `AllowlistViolation`; logs full allowlist to `data/security.log` on build; logs blocked attempts to `data/security.log`
- [X] T068 [P] Add `GURUJEE_DATA_DIR` environment variable override to `gurujee/config/loader.py` — allows CI to point to a temp directory; all `pathlib.Path` data references route through `ConfigLoader.data_dir`
- [X] T069 Profile daemon + uvicorn idle RAM: run `python -m memory_profiler gurujee/__main__.py --headless`; if RSS > 50 MB, apply lazy import to heaviest dependency; document measured value in `specs/001-gurujee-foundation/plan.md` NFR budget row (P1 constitutional requirement — MUST NOT be skipped)
- [X] T070 [P] Verify Termux:Boot script created by `SetupWizard._step_daemons()` at `~/.termux/boot/start-gurujee.sh` has correct content: `#!/data/data/com.termux/files/usr/bin/bash`, `cd ~/gurujee`, `python -m gurujee --headless >> data/boot.log 2>&1 &`; add test to `test_setup_wizard.py`
- [X] T071 [P] Add global exception handler in `gurujee/server/app.py` — `@app.exception_handler(Exception)`: catch unhandled exceptions in request handlers, return `{"error": str(e), "done": true}` as SSE or JSON; log to `data/server.log`; never crash daemon on bad API request
- [X] T072 [P] Add Shizuku health flag to `GET /health` in `gurujee/server/routers/health.py` — if Shizuku unavailable, return `{"status": "ready", "warnings": ["shizuku_inactive"]}` (not an error — daemon usable without automation)
- [X] T073 Run full test suite `pytest --cov=gurujee --cov-report=term-missing` — confirm ≥70% coverage on all agent and server files; fix any failing tests; document final coverage percentage in `specs/001-gurujee-foundation/quickstart.md`
- [X] T074 Update `specs/001-gurujee-foundation/quickstart.md` — add split-layer developer setup: how to run `python -m gurujee --headless`, open PWA at `localhost:7171`, use `--tui`, run tests with coverage, build launcher APK with `buildozer android debug`

**Final Checkpoint**: `pytest` ≥70% passes. Idle daemon RSS ≤50 MB confirmed. `GET /health` → ready. `http://localhost:7171` shows PWA chat UI. "Open WhatsApp" automation works. `install.sh` completes on clean Termux. All logs rotating. Launcher APK installs and reaches chat screen.

- [X] T075 Create `config/security.yaml` — four security-anchor hosts (`api.elevenlabs.io`, `sip.suii.us`, `stun.l.google.com`, `api.deepgram.com`) with `purpose` and `required_for` fields; `unknown_host_policy: prompt_user`; `keystore` config (AES-256-GCM, PBKDF2, 260_000 iterations); `pin_policy` (min 4, max 8, 3 attempts, 30s lockout, ×2 multiplier). This file is version-controlled and contains NO secrets — only hostnames and policy settings. Referenced by `_build_allowlist()` in `gurujee/ai/client.py`.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup — T001–T010)
  └─→ Phase 2 (Foundational — T011–T018) ← CRITICAL GATE
        └─→ Phase 3 (US1: Setup Wizard) — entry gate for daemon
              └─→ Phase 4 (US2: Agents + Memory) — core intelligence
                    ├─→ Phase 6 (US3: Automation) — device control
                    └─→ Phase 5 (US4: FastAPI + PWA) — user interface
                          ├─→ Phase 7 (US5: Launcher APK) — zero-touch
                          └─→ Phase 8 (TUI) — dev tool (parallel with US3/US5)
  All complete → Phase 9 (Polish)
```

### Within Phase 2

- T011 (config loader) first — agents need it
- T012, T013, T015 parallel (independent files)
- T014 after T015 conceptually, but files are independent — can parallel
- T016 (AI client) after T011 (needs config loader)
- T017, T018 (tests) after T013, T016 respectively

### Within Phase 5 (US3)

- T032 (server/app.py) first
- T033–T036 (routers + WS) parallel after T032
- T037–T041 (static files) parallel — fully independent
- T042 (tests) after all routes implemented

### Within Phase 6 (US4)

- T043 (executor) first — all actions need it
- T044–T048 (actions) parallel after T043
- T049 (tool_router) after T044–T048 (needs action signatures)
- T050 (automation_agent) after T049
- T051, T052 (server routes) after T050
- T053 (ai/client update) after T049
- T054 (app.js update) after T051
- T055–T057 (tests) parallel after implementation

### Parallel Opportunities Summary

```bash
# Phase 1 — all parallel:
T003 T004 T005 T006 T007 T008 T009 (all independent config/setup files)

# Phase 2 — Group A parallel:
T012  # base_agent.py
T013  # keystore.py
T015  # short_term.py

# Phase 5 — static files parallel:
T037 T038 T039 T040 T041

# Phase 5 — routers parallel:
T033 T034 T035 T036

# Phase 6 — actions parallel:
T044 T045 T046 T047 T048

# Phase 6 — tests parallel:
T055 T056 T057
```

---

## Implementation Strategy

### MVP — Core chat via PWA (US1 + US2 + US3 only)

1. Phase 1: Setup (T001–T010)
2. Phase 2: Foundational (T011–T018) — **CRITICAL GATE**
3. Phase 3: US1 — Setup Wizard (T019–T022)
4. Phase 4: US2 — Agents + Memory (T023–T031)
5. Phase 5: US4 — FastAPI + PWA (T032–T042)
6. **STOP AND VALIDATE**: Open `localhost:7171`, send message, streaming works, stop/start daemon, memory recall works
7. Non-technical users can now use GURUJEE via PWA

### Incremental Addition

8. Phase 6: US3 — Automation (T043–T057) → "open WhatsApp" works
9. Phase 7: US5 — Background Daemon Auto-Start (T058–T060) → truly zero-touch
10. Phase 8: TUI (T061–T065) → developer tooling
11. Phase 9: Polish (T066–T075) → production-ready

### Parallel Team Strategy (3 developers after Phase 2)

| Developer | Tasks |
|-----------|-------|
| A | US1 (T019–T022) then US2 (T023–T031) |
| B | US3 server (T032–T036, T042) — routes + tests |
| C | US3 static (T037–T041) — PWA HTML/CSS/JS |

After US3 complete:
| Developer | Tasks |
|-----------|-------|
| A | US4 executor + actions (T043–T048) |
| B | US4 router + agent + routes (T049–T054) |
| C | US5 Launcher APK (T058–T060) |

---

## Task Count Summary

| Phase | Tasks | Notes |
|-------|-------|-------|
| Phase 1: Setup | T001–T010 (10) | All parallelizable |
| Phase 2: Foundational | T011–T018 (8) | Blocking gate |
| Phase 3: US1 Setup | T019–T022 (4) | Entry gate |
| Phase 4: US2 Memory/AI | T023–T031 (9) | Core value |
| Phase 5: US4 PWA/Server | T032–T042 (11) | User interface |
| Phase 6: US3 Automation | T043–T057 (15) | Device control |
| Phase 7: US5 Launcher | T058–T060 (3) | Zero-touch |
| Phase 8: TUI | T061–T065 (5) | Dev tool |
| Phase 9: Polish | T066–T075 (10) | Hardening |
| **Total** | **75 tasks** | |

**Parallelizable tasks**: 34 marked `[P]`
**MVP scope** (US1+US2+US3): T001–T042 (42 tasks)

---

## Notes

- `[P]` = task touches a different file than concurrent tasks — safe to run in parallel
- `[USn]` = maps to user story n for traceability and independent delivery
- All tasks are specific enough to implement without additional design context
- Constitution P1 RAM constraint: T069 (profiling) is mandatory — do NOT skip
- Security: FastAPI MUST bind `127.0.0.1` (never `0.0.0.0`) — enforced in T032 and verified in T069
- Commit after each task or logical group (P10 code quality)
- Stop at each phase checkpoint to validate independently before continuing
