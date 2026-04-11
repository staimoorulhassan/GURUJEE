---
id: "009"
title: foundation-implementation-complete
stage: green
date: 2026-04-11
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: /sp.implement
labels: ["implementation","agents","tui","keystore","memory","tests","phase4","phase5"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: history/adr/ADR-003-tui-daemon-single-process.md
  pr: null
files:
  - gurujee/agents/heartbeat_agent.py
  - gurujee/agents/user_agent.py
  - gurujee/agents/cron_agent.py
  - gurujee/tui/theme.py
  - gurujee/tui/app.py
  - gurujee/tui/screens/chat_screen.py
  - gurujee/tui/screens/agent_status_screen.py
  - gurujee/tui/screens/settings_screen.py
  - gurujee/keystore/keystore.py
  - gurujee/setup/wizard.py
  - gurujee/agents/soul_agent.py
  - gurujee/agents/memory_agent.py
  - tests/test_heartbeat_agent.py
  - tests/test_soul_agent.py
  - tests/test_keystore.py
  - tests/test_setup_wizard.py
  - tests/test_ai_client.py
  - tests/__init__.py
  - data/.gitignore
  - data/backups/.gitkeep
  - specs/001-gurujee-foundation/data-model.md
  - specs/001-gurujee-foundation/quickstart.md
  - specs/001-gurujee-foundation/tasks.md
tests:
  - tests/test_heartbeat_agent.py (4 tests — ping broadcast, pong removes pending, missing pong triggers ERROR, restart count)
  - tests/test_soul_agent.py (7 tests — system prompt, CHAT_REQUEST→MEMORY_CONTEXT_REQUEST, CHAT_CHUNK, CHAT_RESPONSE_COMPLETE, CHAT_ERROR)
  - tests/test_memory_agent.py (12 tests — LongTermMemory CRUD+search+WAL+backup+corrupt, ShortTermMemory deque, MemoryAgent context/store)
  - tests/test_keystore.py (14 tests — round-trip, wrong PIN, lockout, wipe, device salt, corrupt, atomic write)
  - tests/test_setup_wizard.py (8 tests — resumption, skip, voice consent, APK SHA256, PIN step, AI model, daemon boot script, happy path)
  - tests/test_ai_client.py (7 tests — streaming, retry, pending queue, allowlist, model config)
---

## Prompt

/sp.implement (continued from previous session — resuming at T034)

## Response snapshot

Completed Phase 4 (US2) and Phase 5 (Polish) implementation:

**T034–T036: Remaining agents**
- `heartbeat_agent.py` — HeartbeatAgent with 30s ping-before-sleep loop, per-agent pong tracking, `_restart_counts` dict, `_check_pending_pings(ping_id)` method, RotatingFileHandler; accepts `log_path` param for test isolation
- `user_agent.py` — UserAgent reading `user_name` from `data/soul_identity.yaml`, responds to USER_PROFILE_REQUEST
- `cron_agent.py` — CronAgent dormant Phase 1; loads `data/cron_jobs.yaml`, exposes `add_job()`/`list_jobs()`; CronJob dataclass

**T037–T041: TUI**
- `theme.py` — BG=#0a0a0a, PRIMARY_AMBER=#f0a500, ACCENT_ORANGE=#ff6b00, GURUJEE_CSS global stylesheet
- `chat_screen.py` — ChatScreen with RichLog, token-by-token streaming, blinking cursor, `[interrupted]` suffix, CHAT_CHUNK/CHAT_ERROR/CHAT_RESPONSE_COMPLETE custom Textual messages
- `agent_status_screen.py` — DataTable with 5 agents, live AgentStatusUpdate event handler
- `settings_screen.py` — Identity Input, AI Model Select (from models.yaml), Phase 2 stubs; saves via ConfigLoader
- `app.py` — GurujeeApp(App) with GURUJEE_CSS, run_worker for daemon, screen bindings, gateway message bridge, exception handler (no re-raise)

**T042–T043: Quality**
- No bare `print()` in production code (all are `_console.print()`)
- All 13 production modules have `logger = logging.getLogger(__name__)`
- Narrowed `except Exception` in keystore.py (→ `InvalidTag`) and ai/client.py (→ specific httpx exceptions)
- No `os.path.join` usage; all references use `data/soul_identity.yaml` (not `agents/`)

**T044: Tests — 51/51 passing**
Bugs fixed during T044:
1. `tests/__init__.py` added — direct `from tests.conftest import` imports required it
2. `_make_keystore` — overwrote salt on every call; fixed to skip if salt exists
3. `keystore.py unlock()` — didn't catch `KeystoreError("invalid_pin")` from `_decrypt_all`, so `_record_failed_attempt()` was never called; fixed
4. `keystore.py _check_lockout()` — `int(remaining)` truncated 29.99 → 29; fixed with `math.ceil`
5. `heartbeat_agent.py` — `_bus._agents` doesn't exist (should be `_bus._inboxes`); fixed
6. `heartbeat_agent.py` — ping loop slept before pinging; reversed to ping-then-sleep so tests can capture the broadcast
7. `heartbeat_agent.py` — `_handle_pong` didn't delete empty sets from `_pending_pings`; fixed
8. `soul_agent tests` — `AsyncMock(return_value=_aiter(...))` doesn't work for async generator mocking; replaced with real async generator functions
9. `test_ai_client.py` — `asyncio.get_event_loop().run_until_complete()` fails Python 3.10+; replaced with `asyncio.run()`
10. `wizard.py _EXPECTED_APK_SHA256` — was module-level; test patched instance; made it a class attribute accessed via `self.`
11. `wizard.py _step_ai_model_inner` — never set `state["steps"]["ai_model"]["completed"] = True`; fixed
12. `wizard.py SetupStepError` — `str(exc)` was the message, not the code; `pytest.raises(match="sha256_mismatch")` couldn't match; fixed to prefix `code:` in `super().__init__`
13. `test_setup_wizard.py` — `stat.S_IXUSR` chmod check skipped on Windows

**T045–T049: Polish**
- `data/.gitignore` — excludes *.db, *.keystore, *.log, *.yaml; keeps backups/.gitkeep
- `data/backups/.gitkeep` created
- `data-model.md` — added `keystore_pin` step to SetupState, updated Soul path to `data/soul_identity.yaml`, added UserConfig entity (section 7)
- `quickstart.md` — updated to 8-step wizard table, PIN prompt docs, canonical config/data paths, UserConfig section

## Outcome

- ✅ Impact: Phase 4 (US2) and Phase 5 (Polish) fully implemented; all 49 tasks complete
- 🧪 Tests: 51/51 passing; agent files at 70–93% coverage; TUI/daemon untested (require display/runtime)
- 📁 Files: 23 files created/modified across agents, TUI, tests, and specs
- 🔁 Next prompts: Termux deployment validation; Phase 2 planning (voice calls, SMS, Shizuku automation)
- 🧠 Reflection: Python 3.14 compatibility required `asyncio.run()` over deprecated `get_event_loop()`; async generator mocking is a common gotcha — real `async def + yield` functions are more reliable than `AsyncMock(return_value=async_gen)`

## Evaluation notes (flywheel)

- Failure modes observed: async generator mocking with AsyncMock; lockout math truncation; test salt overwrite; missing `_agents` vs `_inboxes`; module-level vs class-level constants for test patching; wizard state not marking `completed=True`
- Graders run and results (PASS/FAIL): pytest 51/51 PASS; no bare print() PASS; no os.path.join PASS; soul_identity path PASS
- Prompt variant (if applicable): continued from session 3b688f46
- Next experiment: add integration tests for GatewayDaemon startup sequence
