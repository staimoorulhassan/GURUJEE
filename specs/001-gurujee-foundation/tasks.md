---
description: "Task list for GURUJEE Foundation — Phase 1 (regenerated post-clarification round 2)"
---

# Tasks: GURUJEE Foundation

**Input**: Design documents from `/specs/001-gurujee-foundation/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: Included — 70% coverage target is explicitly stated in the tech stack (plan.md).
Tests follow TDD: write → confirm fail → implement.

**Organization**: Tasks grouped by user story for independent implementation and delivery.

**Changes from prior generation**: Added FR-023 PIN prompt/lockout (T011, T015, T022),
config/voice.yaml (T007), data/user_config.yaml (T010, T023), wizard _step_keystore_pin (T022),
wizard _step_ai_model (T023), full streaming render spec in chat_screen (T039),
updated all agent tasks to use data/soul_identity.yaml runtime path.

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Parallelizable (different files, no incomplete dependencies)
- **[Story]**: US1 = Setup & Onboarding, US2 = Conversational AI + Memory

## Path Conventions (from plan.md)

- Python package: `gurujee/` (single project at repo root)
- Config templates (versioned): `agents/`, `config/`
- Runtime data (gitignored): `data/`
- Tests: `tests/`

---

## Phase 1: Setup

**Purpose**: Initialize project structure, all config templates, and development tooling.
No user story dependencies — start immediately.

- [x] T001 Create full gurujee/ package directory tree: `gurujee/__init__.py`, `gurujee/agents/__init__.py`, `gurujee/daemon/__init__.py`, `gurujee/tui/__init__.py`, `gurujee/tui/screens/__init__.py`, `gurujee/setup/__init__.py`, `gurujee/keystore/__init__.py`, `gurujee/memory/__init__.py`, `gurujee/ai/__init__.py`, `gurujee/config/__init__.py`; also create empty `config/`, `agents/`, `tests/`, `data/` directories (data/ will be gitignored)
- [x] T002 Create `pyproject.toml` — package name `gurujee`, entry point `gurujee = "gurujee.__main__:main"`, pytest config: `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `python_requires = ">=3.11"`
- [x] T003 Create `requirements.txt` — pin all Phase 1 deps: `openai>=1.0.0`, `textual>=0.47.0`, `rich>=13.0.0`, `cryptography>=41.0.0`, `PyYAML>=6.0`, `ruamel.yaml>=0.18.0`, `tenacity>=8.2.0`, `elevenlabs>=1.0.0`, `faster-whisper>=1.0.0`, `pytest>=7.4.0`, `pytest-asyncio>=0.23.0`, `pytest-cov>=4.1.0`, `responses>=0.25.0`
- [x] T004 [P] Create `.gitignore` — exclude `data/`, `*.keystore`, `*.log`, `__pycache__/`, `.pytest_cache/`, `*.pyc`, `.coverage`, `htmlcov/`, `dist/`, `*.egg-info/`
- [x] T005 [P] Create `config/models.yaml` — `default: nova-fast`, `available: [nova-fast, gemini-fast, gemini-search, openai-fast, grok, mistral]`, `endpoint.base_url: "https://gen.pollinations.ai/v1"`, `endpoint.api_key: ""`
- [x] T006 [P] Create `config/agents.yaml` — heartbeat: `ping_interval_seconds: 30`, `response_timeout_seconds: 5`, `max_restart_attempts: 10`; memory: `short_term_max_turns: 10`, `long_term_max_results: 5`, `backup_interval_days: 7`; logging: `max_bytes: 5242880`, `backup_count: 3`
- [x] T007 [P] Create `config/voice.yaml` — voice provider config: `provider: elevenlabs`, `model: eleven_turbo_v2`, `streaming: true`, `sample_rate: 22050`, `voice_id: null` (populated at runtime from keystore); this file is version-controlled, never contains actual credentials
- [x] T008 [P] Create `agents/soul_identity.yaml` — default GURUJEE identity template (this is the SHIPPED template; runtime copy lives at `data/soul_identity.yaml`): name, tagline, personality_traits list, language_style, system_prompt_template with `{name}` `{date}` `{user_name}` `{traits_joined}` placeholders, `voice_id: null`, `user_name: null`, created_at, version: 1; use ruamel.yaml-compatible block style strings
- [x] T009 [P] Create `install.sh` — idempotent Termux bootstrap: `#!/data/data/com.termux/files/usr/bin/bash` shebang; `pkg update && pkg upgrade -y`, `pkg install -y python git`; `git clone / git pull` (detect existing install via `[ -d .git ]`); `pip install -r requirements.txt`; launch `python -m gurujee.setup`; `chmod +x install.sh` at top of script; all operations check exit codes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core modules that BOTH user stories depend on. No US task begins until this
phase is complete.

**⚠️ CRITICAL**: US1 and US2 implementation tasks are blocked until T010–T016 all pass.

- [x] T010 Implement `gurujee/config/loader.py` — `ConfigLoader` class: `load_yaml(path: Path) → dict` (PyYAML safe_load), `load_soul_identity(path: Path)` (ruamel.yaml round-trip, preserves comments), `save_soul_identity(data, path: Path)`, `load_setup_state(path: Path) → dict`, `save_setup_state(data, path: Path)`, `load_user_config(path: Path) → dict` (PyYAML, returns defaults if missing: `{active_model: "nova-fast", active_voice_id: null, tui_theme: "default"}`), `save_user_config(data, path: Path)`, `init_user_config(path: Path)` (writes defaults only if file does not exist); env var overrides: `GURUJEE_DATA_DIR`, `GURUJEE_CONFIG_DIR`, `GURUJEE_LOG_LEVEL`; type hints + docstrings on all methods
- [x] T011 [P] Implement `gurujee/keystore/keystore.py` — `Keystore(path: Path, pin: str)`: `unlock()` (PBKDF2-HMAC-SHA256, 480k iterations, salt from `android_id` via `settings get secure android_id` subprocess, fallback to `data/.device_salt`), `get(key) → str | None`, `set(key, value)`, `delete(key)`, `lock()` (zeros key bytearray), `is_locked() → bool`, `wipe()` (deletes `path` and `data/.device_salt` — used only by forgot-PIN flow); on-disk: 12-byte nonce + GCM ciphertext + 16-byte tag; atomic write via `os.replace`; PIN lockout: `_attempt_count: int`, `_lockout_until: float | None`; `unlock()` raises `KeystoreError("locked_out", lockout_seconds=N)` if `time.time() < _lockout_until`; after 3 wrong-PIN failures set `_lockout_until = time.time() + 30 * (2 ** (attempt_count - 3))`; `KeystoreError` with codes: `locked`, `invalid_pin`, `locked_out`, `corrupt`, `io_error`; type hints + docstrings
- [x] T012 [P] Implement `gurujee/agents/base_agent.py` — `MessageType` enum (CHAT_REQUEST, CHAT_CHUNK, CHAT_RESPONSE_COMPLETE, CHAT_ERROR, MEMORY_CONTEXT_REQUEST, MEMORY_CONTEXT_RESPONSE, MEMORY_STORE, MEMORY_STORED, HEARTBEAT_PING, HEARTBEAT_PONG, AGENT_STATUS_UPDATE, SETUP_COMPLETE, SHUTDOWN); `Message` dataclass with id (uuid4 str), from_agent, to_agent, type, payload, timestamp, reply_to, ttl=10; `MessageBus` class with `send(msg: Message)`, `register_agent(name: str, inbox: asyncio.Queue)`, `deregister_agent(name: str)`; `BaseAgent` ABC with `run()`, `handle_message(msg: Message)`, `send(to, type, payload)`, `broadcast(type, payload)`, `register_handler(type, fn)`; type hints + docstrings on all
- [x] T013 Implement `gurujee/daemon/gateway_daemon.py` — `GatewayDaemon`: `start()` coroutine; `_start_agents()` in order soul(P1)→memory(P2)→heartbeat(P3)→user_agent(P4)→cron(P5) each as `asyncio.create_task(agent.run())`; `_route_message(msg: Message)` delivers to target agent's inbox Queue; `_on_agent_failure(name: str)` triggers heartbeat restart logic; `shutdown(reason: str)` sends SHUTDOWN broadcast and awaits all tasks with 5s timeout; emits AGENT_STATUS_UPDATE to TUI on each state change; `get_agent_statuses() → dict[str, AgentStatus]` for setup wizard polling; type hints + docstrings
- [x] T014 [P] Implement `gurujee/ai/client.py` — `AIClient(models_config_path: Path, user_config_path: Path)`: loads `config/models.yaml`; reads `active_model` from `data/user_config.yaml` (falls back to `default` in models.yaml if not set); `async stream_chat(messages: list[dict], model: str | None = None) → AsyncGenerator[str, None]`; uses `AsyncOpenAI(base_url=..., api_key="")` with `stream=True`; wraps in `tenacity.AsyncRetrying(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)))`; on final failure emits CHAT_ERROR and adds message to `_pending_queue: deque`; `_retry_pending()` called on next successful connection; network allowlist check: raise `AllowlistViolation` for any host not in `{gen.pollinations.ai, api.elevenlabs.io}`; type hints + docstrings
- [x] T015 [P] Implement `gurujee/__main__.py` — `main()` entry point: parse `--headless` and `--reset` flags; detect first-run (check `data/setup_state.yaml` existence + `completed_at` field); if first-run or `--reset` → `SetupWizard().run()`; else: initialize `Keystore(data/gurujee.keystore, pin="")` (dummy — will be unlocked); call `_prompt_pin(keystore)` with Rich `Prompt.ask("Enter keystore PIN: ", password=True)`; `_prompt_pin` handles `KeystoreError("invalid_pin")` with attempt counter display, `KeystoreError("locked_out")` with countdown, "Forgot PIN?" prompt that calls `keystore.wipe()` + `SetupWizard().run()` after explicit confirmation; once unlocked: if `--headless` → `asyncio.run(GatewayDaemon(keystore).start())`, else → `GurujeeApp(keystore).run()`; configure root logger `RotatingFileHandler("data/boot.log", maxBytes=5_242_880, backupCount=3)`; set `GURUJEE_HEADLESS=1` when `--headless`; type hints + docstrings
- [x] T016 [P] Create `tests/conftest.py` — pytest fixtures: `mock_bus` (MockMessageBus with `sent_messages: list` capture), `temp_data_dir` (tmp_path with pre-created `data/`, `config/` dirs + copies of `config/models.yaml`, `config/agents.yaml`, `config/voice.yaml`), `fake_soul_yaml` (soul_identity.yaml at temp path from agents/ template), `fake_user_config` (data/user_config.yaml at temp path with `{active_model: "nova-fast"}`), `fake_openai_stream` (responses mock returning 3-chunk SSE for `/v1/chat/completions`), `fake_keystore` (Keystore backed by tmp_path with known test PIN "1234"); all fixtures function-scoped

**Checkpoint**: Phase 2 complete when `pytest tests/conftest.py -v` passes with no import errors.

---

## Phase 3: User Story 1 — Guided Setup and Onboarding (Priority: P1) 🎯 MVP

**Goal**: A new user can run `install.sh` on a fresh Android device and GURUJEE is fully
configured and running within 10 minutes, without external documentation.

**Independent Test**: Run `python -m gurujee.setup --reset` on fresh Termux. Interrupt after
step 3, relaunch — verify it resumes at step 4. Complete all 8 steps. Verify
`data/setup_state.yaml` has `completed_at` set, `~/.termux/boot/start-gurujee.sh` exists and
is executable, `data/gurujee.keystore` exists, `data/user_config.yaml` has `active_model` set,
`data/soul_identity.yaml` exists.

### Tests for US1 ⚠️ Write first — confirm they FAIL before T019

- [x] T017 [P] [US1] Write `tests/test_setup_wizard.py` — test wizard resumes from last completed step (inject partial `setup_state.yaml` with steps 1–3 complete; verify wizard starts at step 4); test `_step_keystore_pin()` writes keystore and marks step complete; test voice_sample step skipped when user inputs "n" at consent prompt and marks `skipped: true`; test `_step_accessibility_apk()` rejects APK with wrong SHA-256 and does NOT mark step complete; test `_step_daemons()` writes `~/.termux/boot/start-gurujee.sh` with correct content + executable bit; test full happy-path run writes `completed_at` to `setup_state.yaml`; test `_step_ai_model()` writes `active_model` to `data/user_config.yaml`
- [x] T018 [P] [US1] Write `tests/test_keystore.py` — test unlock→get→set→lock→unlock→get round-trip with PIN "1234"; test wrong PIN raises `KeystoreError("invalid_pin")`; test 3 wrong PINs raises `KeystoreError("locked_out")` on 4th attempt; test lockout duration is ≥ 30 seconds; test `lock()` prevents `get()` (raises `KeystoreError("locked")`); test `wipe()` deletes keystore file; test atomic write: partial write does not corrupt existing keystore; test `android_id` unavailable → falls back to `data/.device_salt`; test corrupt file raises `KeystoreError("corrupt")`

### Implementation for US1

- [x] T019 [US1] Implement `gurujee/setup/wizard.py` — `SetupWizard` class: `run()` entry; `_load_state() → dict` (loads `data/setup_state.yaml` or returns blank 8-step state); `_save_state(state)` (writes via ConfigLoader); `_step_runner(step_name, fn, required=True)` (skip if already `completed: true`; mark complete + set `completed_at` on success; handle `skipped: true` for optional steps); Rich `Progress` + `Console` for all output; `STEPS = ["packages", "shizuku", "accessibility_apk", "permissions", "keystore_pin", "ai_model", "voice_sample", "daemons"]`; type hints + docstrings
- [x] T020 [US1] Implement `SetupWizard._step_packages()` in `gurujee/setup/wizard.py` — `subprocess.run(["pkg", "update", "-y"])`, then `subprocess.run(["pkg", "install", "-y", "python", "git"])`, then `subprocess.run(["pip", "install", "-r", "requirements.txt"])`; display Rich progress bar per group; on non-zero exit: print error + `Prompt.ask("Retry? [y/n]")`; raise `SetupStepError("packages_failed")` on repeated failure; specific exception types only (no bare except)
- [x] T021 [US1] Implement `SetupWizard._step_accessibility_apk()` in `gurujee/setup/wizard.py` — display exact GitHub Releases URL and expected SHA-256 via Rich Panel; `urllib.request.urlretrieve(url, "/tmp/gurujee-accessibility.apk")`; compute sha256 of downloaded file; raise `SetupStepError("sha256_mismatch")` if mismatch and do not proceed; `subprocess.run(["pm", "install", "/tmp/gurujee-accessibility.apk"])`; save verified checksum to `steps.accessibility_apk.apk_sha256` in `setup_state.yaml`; `os.unlink("/tmp/gurujee-accessibility.apk")` after install
- [x] T022 [US1] Implement `SetupWizard._step_keystore_pin()` in `gurujee/setup/wizard.py` — display Rich Panel: "Choose a 4–8 digit PIN for your keystore. This PIN is NEVER stored — it is the only way to decrypt your credentials. **If you forget your PIN, your keystore must be wiped and all credentials re-entered.**"; `Prompt.ask("PIN (4–8 digits): ", password=True)` + `Prompt.ask("Confirm PIN: ", password=True)` with length validation; on mismatch: re-prompt (max 3 tries); instantiate `Keystore(data/gurujee.keystore, pin=pin)`; `keystore.unlock()` (creates new keystore if file absent); set empty initial entries via `keystore.set()`; `keystore.lock()`; save `pin_set: true` to `setup_state.yaml keystore_pin step`; never log or store the PIN string
- [x] T023 [US1] Implement `SetupWizard._step_ai_model()` in `gurujee/setup/wizard.py` — load `config/models.yaml` via ConfigLoader; display model list in a Rich Table with model names and descriptions; `Prompt.ask("Choose model (default: nova-fast): ")` with validation against available list; call `ConfigLoader.init_user_config(data/user_config.yaml)`; call `ConfigLoader.save_user_config({active_model: chosen_model, ...}, data/user_config.yaml)`; confirm selection to user; type hints + docstrings
- [x] T024 [US1] Implement `SetupWizard._step_voice_sample()` in `gurujee/setup/wizard.py` — display Rich Panel with 3-part consent: purpose ("Your voice will be cloned via ElevenLabs to power GURUJEE's call features in Phase 2"), retention ("The raw recording is deleted from your device immediately after upload"), deletion right ("You can remove your voice clone at any time via Settings"); `Confirm.ask("I consent and want to record now. Continue?")` — if "n": mark step `skipped: true` and return; `subprocess.run(["termux-microphone-record", "-l", "30", "-f", "/tmp/voice_sample.wav"])`; upload WAV to ElevenLabs instant clone API; unlock keystore with PIN re-prompt; `keystore.set("voice_id", returned_voice_id)`; `keystore.lock()`; `os.unlink("/tmp/voice_sample.wav")`; verify file deleted (raise if still exists) before marking step complete
- [x] T025 [US1] Implement `SetupWizard._step_daemons()` in `gurujee/setup/wizard.py` — copy `agents/soul_identity.yaml` → `data/soul_identity.yaml` using `shutil.copy2` (only if `data/soul_identity.yaml` does not already exist); initialise `data/user_config.yaml` defaults if not present via `ConfigLoader.init_user_config()`; instantiate `GatewayDaemon` and start in background thread; poll `daemon.get_agent_statuses()` for up to 10s until all 5 agents reach RUNNING; display Rich spinner during wait; write `~/.termux/boot/start-gurujee.sh`: `#!/data/data/com.termux/files/usr/bin/bash`, `sleep 5`, `cd <install_dir>`, `python -m gurujee --headless >> data/boot.log 2>&1 &`; `os.chmod(boot_script, 0o755)`; print confirmation with path

**Checkpoint**: US1 complete and independently testable.
Run: `python -m gurujee --reset && python -m gurujee.setup` — all 8 steps pass,
`data/setup_state.yaml` has `completed_at` set, `data/soul_identity.yaml` exists,
`data/user_config.yaml` has `active_model`, boot script exists and is executable.

---

## Phase 4: User Story 2 — Conversational AI Companion with Persistent Memory (Priority: P1)

**Goal**: User can chat with GURUJEE, which responds with personality and streaming tokens,
remembers facts across sessions, and retrieves them correctly in future conversations.

**Independent Test**: Start GURUJEE. Tell it: "My daughter's name is Fatima." Exit.
Restart (enter PIN). Ask: "What is my daughter's name?" — GURUJEE must answer "Fatima".
Interrupt a response mid-stream — verify `[interrupted]` suffix appears and fact is still
saved. Verify idle RAM < 50 MB via `ps aux | grep gurujee`.

### Tests for US2 ⚠️ Write first — confirm they FAIL before T031

- [x] T026 [P] [US2] Write `tests/test_soul_agent.py` — test system prompt contains `{name}`, `{date}`, `{user_name}` filled from `data/soul_identity.yaml`; test CHAT_REQUEST triggers MEMORY_CONTEXT_REQUEST (captured via mock_bus); test CHAT_CHUNK messages emitted per streaming token (mock AIClient returns 3 chunks); test CHAT_RESPONSE_COMPLETE emitted after final chunk with assembled `full_text`; test MEMORY_STORE emitted with full exchange after response complete; test CHAT_ERROR emitted when AIClient raises after retries exhausted
- [x] T027 [P] [US2] Write `tests/test_memory_agent.py` — test `LongTermMemory.insert()` writes row to SQLite; test `LongTermMemory.search("daughter")` returns record tagged "person"; test `ShortTermMemory` deque drops turn 1 when 11th turn added (maxlen=10); test MEMORY_CONTEXT_REQUEST → response contains `recent_turns` (≤10) and `long_term_facts` (≤5); test `explicit` source sets `importance=1.0`; test `backup_weekly()` creates `data/backups/memory_YYYYMMDD.db`; test corrupted DB → fresh empty DB created + AGENT_STATUS_UPDATE emitted
- [x] T028 [P] [US2] Write `tests/test_heartbeat_agent.py` — test HEARTBEAT_PING broadcast sent every 30s (mock asyncio.sleep); test agent missing PONG after 5s timeout → `_request_restart("agent_name")` called; test AGENT_STATUS_UPDATE(status=ERROR) emitted when restart requested; test restart_count increments in AgentState; test HEARTBEAT_PONG with "degraded" payload logged at WARNING but not treated as failure
- [x] T029 [P] [US2] Write `tests/test_ai_client.py` — test `stream_chat()` yields tokens as async generator (responses mock SSE); test ConnectError → retried 3× with exponential backoff; test all retries exhausted → CHAT_ERROR emitted + message added to `_pending_queue`; test `_retry_pending()` sends queued message on next successful call; test non-allowlisted host raises `AllowlistViolation`; test `active_model` read from `data/user_config.yaml` (not hardcoded); test model override arg takes precedence over user_config value

### Implementation for US2

- [x] T030 [US2] Implement `gurujee/memory/short_term.py` — `ConversationTurn` dataclass: role (str), content (str), timestamp (datetime); `ShortTermMemory`: `add_turn(role, content)` appends to `deque(maxlen=10)`; `get_recent(n=10) → list[dict]` returns `[{role, content}]`; `serialize(path: Path)` writes turns to YAML via PyYAML; `load(path: Path)` restores deque from YAML (tolerates missing file — returns empty deque); type hints + docstrings
- [x] T031 [US2] Implement `gurujee/memory/long_term.py` — `MemoryRecord` dataclass (id, content, tags, category, importance, created_at, source); `LongTermMemory(db_path: Path)`: `init_db()` creates `memories` table (schema per data-model.md), `PRAGMA journal_mode=WAL`, `CREATE INDEX idx_tags ON memories(tags)`; `insert(content, tags, category, importance=0.5, source="conversation") → MemoryRecord`; `search(query_text: str) → list[MemoryRecord]` (split query into keywords; SQL hybrid retrieval: `WHERE tags LIKE '%keyword%' ORDER BY importance*2 + 1.0/(julianday('now')-julianday(created_at)+1) DESC LIMIT 5`); `backup_weekly(backups_dir: Path)` — skip if backed up within 7 days, else `shutil.copy2`; `handle_corrupt(path: Path)` — rename to `.corrupt.<timestamp>`, create fresh DB; type hints + docstrings
- [x] T032 [US2] Implement `gurujee/agents/soul_agent.py` — `SoulAgent(name="soul")`: `run()` loop on inbox Queue; `_load_soul(path: Path)` via ConfigLoader reading `data/soul_identity.yaml`; `_build_system_prompt(user_name, date, recent_turns, long_term_facts) → str` (fills template placeholders); handles `CHAT_REQUEST`: sends `MEMORY_CONTEXT_REQUEST` → awaits `MEMORY_CONTEXT_RESPONSE` with 2s timeout → builds prompt → calls `AIClient.stream_chat()` → emits `CHAT_CHUNK` per token → on done emits `CHAT_RESPONSE_COMPLETE(full_text, is_interrupted=False)` + `MEMORY_STORE`; on `httpx.ConnectError` mid-stream: emits `CHAT_RESPONSE_COMPLETE(partial_text + " [interrupted]", is_interrupted=True)` + `MEMORY_STORE(partial_text, source="conversation")`; handles `SHUTDOWN`; type hints + docstrings
- [x] T033 [US2] Implement `gurujee/agents/memory_agent.py` — `MemoryAgent(name="memory")`: `run()` loop; initialises `LongTermMemory(data/memory.db)` + `ShortTermMemory()`; calls `long_term.init_db()` (creates or validates schema); loads `data/session_context.yaml` if exists; handles `MEMORY_CONTEXT_REQUEST` → extract keywords from `query_text` → `long_term.search()` → returns `MEMORY_CONTEXT_RESPONSE(recent_turns, long_term_facts)`; handles `MEMORY_STORE` → `long_term.insert()` + `short_term.add_turn()` → emits `MEMORY_STORED`; on `SHUTDOWN` → `short_term.serialize(data/session_context.yaml)`; `asyncio.create_task(_schedule_backup())` on startup; type hints + docstrings
- [x] T034 [US2] Implement `gurujee/agents/heartbeat_agent.py` — `HeartbeatAgent(name="heartbeat")`: `run()` coroutine; `_ping_loop()`: every 30s sends `HEARTBEAT_PING` broadcast with unique `ping_id`; `_pending_pings: dict[str, set[str]]` tracks agents without pong; `asyncio.wait_for(pong_event, timeout=5.0)` per agent; on timeout: `await self.send("gateway", MessageType.AGENT_STATUS_UPDATE, {name, status="ERROR", reason="pong_timeout"})`; handles `HEARTBEAT_PONG`: removes from `_pending_pings`; logs to `data/heartbeat.log` via `RotatingFileHandler(maxBytes=5_242_880, backupCount=3)`; type hints + docstrings
- [x] T035 [US2] Implement `gurujee/agents/user_agent.py` — `UserAgent(name="user_agent")`: `run()` loop; loads `user_name` from `data/soul_identity.yaml` top-level `user_name` field (add `user_name: null` to the template in `agents/soul_identity.yaml`); handles `USER_PROFILE_REQUEST` → returns `USER_PROFILE_RESPONSE(user_name=user_name)`; handles `SHUTDOWN`; type hints + docstrings
- [x] T036 [US2] Implement `gurujee/agents/cron_agent.py` — `CronAgent(name="cron")`: `run()` loop; loads `data/cron_jobs.yaml` (`jobs: []`); logs "cron: 0 active jobs (Phase 1 dormant)" at INFO on startup; `add_job(job: CronJob) → str` and `list_jobs() → list[CronJob]` callable from gateway; `CronJob` dataclass (id, description, cron_expr, action_type, action_payload, active, created_at, last_run, next_run — all fields from data-model.md); handles `SHUTDOWN`; type hints + docstrings
- [x] T037 [US2] Implement `gurujee/tui/theme.py` — module-level constants: `BG = "#0a0a0a"`, `PRIMARY_AMBER = "#f0a500"`, `ACCENT_ORANGE = "#ff6b00"`, `TEXT_PRIMARY = "#e0e0e0"`, `TEXT_DIM = "#666666"`; `GURUJEE_CSS: str` Textual global stylesheet applying BG to Screen, PRIMARY_AMBER to focused borders + buttons, ACCENT_ORANGE to active indicators, TEXT_DIM to disabled/stub labels; type hints + docstrings
- [x] T038 [US2] Implement `gurujee/tui/screens/chat_screen.py` — `ChatScreen(Screen)`: `RichLog(id="chat-log", auto_scroll=True, markup=True)` for history; `Input(placeholder="Message GURUJEE...", id="chat-input")` at bottom; `_streaming_message_id: str | None` tracks the in-progress bubble; `on_input_submitted(event)`: clear input, append user turn in TEXT_PRIMARY, send `CHAT_REQUEST` to gateway via `app.post_message()`; `on_chat_chunk(event)`: if first chunk → write opening bubble with amber blinking cursor `"[bold amber]●[/] "` + token; subsequent chunks → append token in-place via `log.markup`; `on_chat_error(event)`: append error row in red + `"(Will retry automatically)"` if `queued=True`; `on_chat_response_complete(event)`: remove cursor indicator, finalise amber color; if `event.is_interrupted` → append `" [interrupted]"` in TEXT_DIM after partial text; type hints + docstrings
- [x] T039 [US2] Implement `gurujee/tui/screens/agent_status_screen.py` — `AgentStatusScreen(Screen)`: `DataTable(id="agent-table")` with columns: Name, Status, Restarts, Last Error; `compose()` populates table with 5 agent names at STARTING; `on_agent_status_update(event)`: update matching row, flash row in PRIMARY_AMBER on state change; `action_back()` bound to Escape key; type hints + docstrings
- [x] T040 [US2] Implement `gurujee/tui/screens/settings_screen.py` — `SettingsScreen(Screen)`: section "Identity" → `Input` pre-filled with `soul.name` from `data/soul_identity.yaml`, on Submit: `ConfigLoader.save_soul_identity(updated, data/soul_identity.yaml)`; section "AI Model" → `Select` populated from `config/models.yaml available[]`, on change: `ConfigLoader.save_user_config({active_model: selected}, data/user_config.yaml)`; section "Calls" (Phase 2 stub) → `Label("Auto-Answer: Coming in Phase 2", classes="dim")`; section "SMS" (Phase 2 stub) → `Label("SMS Auto-Reply: Coming in Phase 2", classes="dim")`; type hints + docstrings
- [x] T041 [US2] Implement `gurujee/tui/app.py` — `GurujeeApp(App, keystore: Keystore)`: `CSS = GURUJEE_CSS` from theme.py; `SCREENS = {"chat": ChatScreen, "agents": AgentStatusScreen, "settings": SettingsScreen}`; `on_mount()`: push ChatScreen; `self.run_worker(self._start_daemon, thread=False)`; `_start_daemon()` coroutine: `GatewayDaemon(self._keystore)` → `daemon.start()`; `BINDINGS`: `"a" → agents screen`, `"s" → settings screen`, `"escape" → pop_screen`, `"ctrl+c" → quit`; `handle_exception(exc)`: log to `data/boot.log` + `self.notify(str(exc), severity="error")` — do NOT re-raise (Textual crash must not kill daemon); type hints + docstrings

**Checkpoint**: US2 complete and independently testable.
Run: `python -m gurujee` → chat opens, tell it a fact, exit, re-run, enter PIN, verify recall.
Run: `ps aux | grep gurujee` → verify RSS < 50 MB.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, compliance verification, and documentation finalization.
All US1 + US2 implementation MUST be complete before this phase.

- [x] T042 [P] Add `logging.getLogger(__name__)` + `RotatingFileHandler` to all production modules — `gurujee/agents/soul_agent.py`, `memory_agent.py`, `heartbeat_agent.py`, `user_agent.py`, `cron_agent.py`, `gurujee/daemon/gateway_daemon.py`; confirm zero `print()` in production code: `grep -rn "print(" gurujee/`
- [x] T043 [P] P10 compliance pass — `grep -rn "except Exception\|except:\|except BaseException" gurujee/` and replace with specific exception types; `grep -rn "os\.path\.join\|str(.*Path" gurujee/` and replace with `pathlib.Path`; `python -m mypy gurujee/ --ignore-missing-imports` and fix obvious type errors; `grep -rn "soul_identity" gurujee/` and confirm all references use `data/soul_identity.yaml` (not `agents/`)
- [x] T044 Run `pytest tests/ --cov=gurujee --cov-report=term-missing -v` — identify agent files below 70% coverage; add targeted unit tests for uncovered branches: corrupt DB, wrong PIN, locked_out keystore, endpoint outage, agent restart, [interrupted] stream path
- [x] T045 [P] Manual TUI render test — run `COLUMNS=80 python -m gurujee`; verify Chat screen, Agent Status screen, and Settings screen all render without overflow or truncation at 80 columns; document any layout fixes in `gurujee/tui/screens/`
- [x] T046 [P] Verify `install.sh` idempotency — run `bash install.sh` twice on a clean environment; confirm second run exits cleanly, no duplicate errors, no data overwritten
- [x] T047 [P] Create `data/.gitignore` — `*.db`, `*.keystore`, `*.log`, `*.yaml`, `*.db.corrupt.*`; but keep `backups/.gitkeep`; verify `git status` shows no `data/` files tracked
- [x] T048 [P] Update `specs/001-gurujee-foundation/data-model.md` — add `keystore_pin` step to SetupState schema (after `permissions`, before `ai_model`); update Soul entity path from `agents/soul_identity.yaml` to `data/soul_identity.yaml`; add `UserConfig` entry (`data/user_config.yaml`: active_model, active_voice_id, tui_theme)
- [x] T049 Update `specs/001-gurujee-foundation/quickstart.md` — reflect 8-step wizard, canonical config/data paths, PIN prompt at launch, `data/user_config.yaml`; verify all commands work against implemented codebase

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — all T002–T009 parallelizable after T001
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS both US1 and US2
- **US1 (Phase 3)**: Depends on Foundational; T017–T018 (tests) first
- **US2 (Phase 4)**: Depends on Foundational; T026–T029 (tests) first; can run IN PARALLEL with US1
- **Polish (Phase 5)**: Depends on both US1 AND US2 complete

### User Story Dependencies

- **US1**: No dependency on US2 — `SetupWizard` does not require any agent to be running
- **US2**: No dependency on US1 — agents start independently; `data/soul_identity.yaml` is
  initialized by wizard (US1) but US2 tests use `fake_soul_yaml` fixture from conftest.py
- **US1 and US2 can be implemented in parallel** by separate developers once Phase 2 completes

### Within Each User Story

- Tests (T017–T018, T026–T029) MUST be written and FAIL before implementation starts
- `memory/short_term.py` (T030) before `memory_agent.py` (T033)
- `memory/long_term.py` (T031) before `memory_agent.py` (T033)
- `soul_agent.py` (T032) after `ai/client.py` (T014) — already in Foundational
- All TUI screens (T037–T040) are independent of each other
- `app.py` (T041) after all three screens (T038–T040)
- wizard steps (T020–T025) run sequentially within `wizard.py` after base class (T019)

### Parallel Opportunities

```bash
# Phase 1 — after T001:
T002 & T003 & T004 & T005 & T006 & T007 & T008 & T009

# Phase 2 — after Phase 1:
T011 & T012 & T014 & T016   (independent files)
T010 first (loader.py needed by T013, T015)
T013 after T012 (gateway needs base_agent)
T015 after T010, T011 (main needs loader + keystore)

# Phase 3 US1 — tests parallel:
T017 & T018

# Phase 3 US1 — wizard impl:
T019 → T020 → T021 → T022 → T023 → T024 → T025  (sequential, same file)

# Phase 4 US2 — tests parallel:
T026 & T027 & T028 & T029

# Phase 4 US2 — impl parallel:
T030 & T031 & T035 & T036 & T037   (independent files)
T032 after T030 (soul agent uses short_term for context hints)
T033 after T030 & T031 (memory agent needs both)
T034 after T012 (heartbeat uses base_agent — already done)
T038 & T039 & T040   (independent TUI screens)
T041 after T038, T039, T040 (app.py assembles screens)

# Phase 5 — parallel:
T042 & T043 & T045 & T046 & T047 & T048
T044 after T042 (coverage after logging complete)
T049 after T044 (quickstart after coverage confirms paths)
```

---

## Implementation Strategy

### MVP First (US1 Setup Wizard — 18 tasks)

1. Complete Phase 1: Setup (T001–T009)
2. Complete Phase 2: Foundational (T010–T016) — CRITICAL GATE
3. Write US1 tests (T017–T018) — verify they FAIL
4. Complete Phase 3: US1 (T019–T025)
5. **STOP and VALIDATE**: all 8 wizard steps pass, boot script created, keystore created
6. **MVP shipped**: New user can configure GURUJEE in under 10 minutes ✓

### Incremental Delivery

1. **MVP** (US1 complete) → guided setup ships; users can install GURUJEE and set their PIN
2. **Phase 4** (US2 complete) → AI chat + memory ships; GURUJEE holds conversations with streaming
3. **Polish** → 70% coverage, P10 compliance, data model updated; ready for Phase 2 feature branch

### Parallel Team Strategy

With two developers after Foundational (Phase 2) completes:
- Developer A: Phase 3 (US1 — wizard, keystore PIN flow, wizard steps)
- Developer B: Phase 4 (US2 — agents, memory, streaming TUI)
- Both merge → Phase 5 (polish, coverage, docs, data model update)

---

## Notes

- `[P]` tasks = parallelizable (different files, no incomplete dependencies at that point)
- `[US1]` / `[US2]` maps each task to its user story for delivery traceability
- Tests MUST fail before implementation — do not skip the red phase
- Commit after each checkpoint or logical group
- For Termux testing: use `tmux` to keep GURUJEE running while verifying memory
- `data/` is gitignored; the wizard creates it on first run
- `agents/soul_identity.yaml` is the shipped template only; `data/soul_identity.yaml` is the runtime copy
- All `pathlib.Path` — no `os.path.join` anywhere (P10)
- PIN is NEVER logged, stored, or passed as a CLI argument
