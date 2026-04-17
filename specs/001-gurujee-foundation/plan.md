# Implementation Plan: GURUJEE Foundation

**Branch**: `001-gurujee-foundation` | **Date**: 2026-04-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-gurujee-foundation/spec.md`

---

## Summary

Build the Phase 1 foundation of GURUJEE: a persistent AI companion running as an asyncio
daemon inside Termux on a non-rooted Android phone, accessible to non-technical users via
a PWA chat interface served by the daemon and loaded in the Launcher APK's WebView.

Phase 1 delivers: zero-touch setup via Launcher APK, a 6-agent always-on daemon
(soul + memory + heartbeat + user_agent + cron-dormant + automation), a FastAPI server on
`localhost:7171` with SSE streaming + WebSocket, a WhatsApp-style PWA chat UI, Shizuku-based
device automation (open apps, device settings, UI input), hybrid memory retrieval
(recency + SQLite keyword/tag search), AES-256-GCM keystore, and full Pollinations AI
integration via the openai SDK with streaming. The daemon targets ≤50 MB RAM at idle.

---

## Technical Context

**Language/Version**: Python 3.11+ (Termux, Android ARM64)
**Primary Dependencies**:
  - AI/chat: openai 1.x (Pollinations endpoint, streaming)
  - Server: fastapi 0.110+, uvicorn 0.29+ (asyncio loop, single worker)
  - TUI (dev tool): Textual 0.47+, Rich 13+
  - Crypto: cryptography 41+
  - Config: PyYAML 6+, ruamel.yaml 0.18+
  - Resilience: tenacity 8.2+
  - Voice (install P1, use P2): elevenlabs 1+, faster-whisper 1+
  - stdlib: sqlite3, asyncio, pathlib, subprocess
**Storage**: SQLite (`data/memory.db`, WAL mode); YAML for config/state; JSON for PWA API responses
**Testing**: pytest 7.4+ with pytest-asyncio 0.23+, httpx 0.25+ (FastAPI test client),
  responses 0.25+ for HTTP mocking; target 70% coverage on all agent + server files
**Target Platform**: Android 10+ non-rooted, Termux (F-Droid), aarch64 (ARM64)
**Project Type**: Split-layer — Python daemon (asyncio) + FastAPI server + PWA static UI (ADR-003 v2)
**Performance Goals**: Idle RAM < 50 MB (P1); TUI keystroke-to-render < 100 ms (SC-004);
  first AI response < 5 s on 3G (SC-003); daemon restart detection < 10 s (SC-007)
**Constraints**: No root; no Docker; no Node.js; ARM64 Termux only; one AI endpoint (P2);
  all config in YAML (P10); all secrets in AES-256-GCM keystore (P4)
**Scale/Scope**: Single-user, single-device; no horizontal scaling; all state is local

---

## Constitution Check

*GATE: Must pass before implementation begins. Re-checked after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **P1** Minimal Memory Footprint | ✅ PASS | No ML models loaded at idle. STT/TTS deferred to Phase 2. sqlite3 + asyncio + Textual idle well under 50 MB (R-002, R-008). |
| **P2** Provider Catalogue AI (v1.2.0) | ✅ PASS | `AIClient` resolves `provider/model-id` strings via `config/models.yaml` catalogue (ADR-005). Pollinations is default zero-key provider. No model ID or endpoint URL hardcoded in logic. |
| **P3** No Root Required | ✅ PASS | All Termux operations are user-space. `android_id` via `settings get` (no root). AutomationAgent implemented always-on in Phase 1 (ADR-004). All automation via `rish` (Shizuku shell), no root calls. Phase 1 scope confirmed by spec US3/US4 and ADR-003. |
| **P4** Security First | ✅ PASS | AES-256-GCM keystore; PBKDF2-HMAC-SHA256 key derivation (R-004). Network allowlist enforced in `ai/client.py`. No secrets in config. Consent gate before voice sample (FR-001, US1-S5). |
| **P5** Zero-Touch Setup | ✅ PASS | Launcher APK handles Termux install → bootstrap → daemon start → PWA load. User never sees terminal. `data/setup_state.yaml` persists progress. |
| **P6** Python-First Stack | ✅ PASS | FastAPI/uvicorn + PWA (HTML/CSS/JS served by Python). No Node.js, no Electron, no JVM. FastAPI binds to 127.0.0.1 only (P4/P6 security). |
| **P7** Agent Architecture Sacred | ✅ PASS | All 5 Phase-1 agents (soul, memory, heartbeat, user_agent, cron-dormant) implemented as asyncio Tasks. All comms via MessageBus/Queue. No direct inter-agent references (contracts/message-bus.md). |
| **P8** Voice/SIP First-Class | ✅ PASS | ElevenLabs SDK installed Phase 1; voice sample + consent in FR-001 step 6. streaming=True enforced in `ai/client.py` (P1-compliant). |
| **P9** Distribution | ✅ PASS | Launcher APK (GitHub Releases) is canonical non-technical path. `install.sh` retained as developer path. Both distribute Accessibility APK via GitHub Releases + SHA-256 check. |
| **P10** Code Quality | ✅ PASS | All config files `.yaml` (PyYAML + ruamel.yaml per R-009). Type hints + docstrings enforced. RotatingFileHandler(5MB, 3 backups). `pathlib.Path` everywhere. pytest 70% target. |

**Constitution Check: ALL GATES PASS. Proceed.**

---

## Project Structure

### Documentation (this feature)

```text
specs/001-gurujee-foundation/
├── plan.md              # This file
├── research.md          # Phase 0 — 10 research decisions resolved
├── data-model.md        # Phase 1 — 8 entities with schemas
├── quickstart.md        # Phase 1 — developer onboarding
├── contracts/
│   ├── message-bus.md   # Phase 1 — 12 message type contracts
│   ├── keystore-api.md  # Phase 1 — Keystore module interface
│   └── agent-base-interface.md  # Phase 1 — BaseAgent ABC contract
├── checklists/
│   └── requirements.md  # spec quality + constitution compliance
└── tasks.md             # Phase 2 output (/sp.tasks — NOT created here)
```

### Source Code (repository root)

```text
gurujee/                          # Python package root
├── __main__.py                   # entry point: --headless | --tui (default: headless + server)
├── agents/
│   ├── __init__.py
│   ├── base_agent.py             # BaseAgent ABC, MessageBus, MessageType enum
│   ├── soul_agent.py             # SoulAgent: identity + prompt injection + AI stream
│   ├── memory_agent.py           # MemoryAgent: short-term deque + SQLite long-term
│   ├── heartbeat_agent.py        # HeartbeatAgent: ping/pong watchdog + restart
│   ├── user_agent.py             # UserAgent: user profile from soul_identity.yaml
│   ├── cron_agent.py             # CronAgent: dormant, empty schedule, Phase 1
│   └── automation_agent.py       # AutomationAgent: Shizuku shell command executor
├── automation/
│   ├── __init__.py
│   ├── executor.py               # ShizukuExecutor: runs `rish` shell commands via subprocess
│   ├── actions/
│   │   ├── __init__.py
│   │   ├── apps.py               # open_app(package_name), list_apps()
│   │   ├── device.py             # set_volume(), set_wifi(), set_bluetooth(), set_flashlight(), set_brightness()
│   │   ├── input.py              # tap(x,y), swipe(), type_text(), key_event()
│   │   ├── notifications.py      # list_notifications(), dismiss_notification()
│   │   └── system.py             # take_screenshot(), get_running_apps()
│   └── tool_router.py            # maps LLM tool-call JSON → action function dispatch
├── daemon/
│   └── gateway_daemon.py         # GatewayDaemon: starts/monitors/routes all agents + starts server
├── server/
│   ├── __init__.py
│   ├── app.py                    # FastAPI app; mounts static PWA; registers all routers
│   ├── routers/
│   │   ├── chat.py               # POST /chat (SSE streaming), POST /transcribe
│   │   ├── agents.py             # GET /agents (agent status snapshot)
│   │   ├── automate.py           # POST /automate (direct automation command)
│   │   ├── notifications.py      # GET /notifications
│   │   └── health.py             # GET /health (APK readiness poll)
│   ├── websocket.py              # WebSocket /ws — real-time push (call events, automation results)
│   └── static/                   # PWA static files (served at /)
│       ├── index.html            # PWA shell
│       ├── app.js                # Chat UI logic (chat bubbles, SSE consumer, WS client)
│       ├── style.css             # WhatsApp-style dark theme
│       ├── sw.js                 # Service worker — offline cache
│       └── manifest.json         # PWA manifest (installable shortcut)
├── tui/                          # DEV TOOL ONLY — python -m gurujee --tui
│   ├── __init__.py
│   ├── app.py                    # Textual App; runs daemon as Worker
│   ├── theme.py                  # CSS constants
│   └── screens/
│       ├── chat_screen.py        # Chat: scrollable history + input
│       ├── agent_status_screen.py
│       └── settings_screen.py
├── setup/
│   ├── __init__.py
│   └── wizard.py                 # Rich guided setup (8 steps incl. automation check)
├── keystore/
│   ├── __init__.py
│   └── keystore.py               # AES-256-GCM; PBKDF2-HMAC-SHA256
├── memory/
│   ├── __init__.py
│   ├── short_term.py             # ConversationTurn deque(maxlen=10)
│   └── long_term.py              # MemoryRecord + AutomationLog + NotificationCache SQLite CRUD
├── ai/
│   ├── __init__.py
│   └── client.py                 # AsyncOpenAI wrapper; tenacity retry; streaming; tool-call support
└── config/
    ├── __init__.py
    └── loader.py                 # PyYAML + ruamel.yaml loaders

agents/                           # shipped defaults (version-controlled)
└── soul_identity.yaml

config/                           # version-controlled app config
├── models.yaml                   # AI model catalogue + endpoint
├── agents.yaml                   # heartbeat intervals, memory limits, logging, automation settings
├── voice.yaml                    # voice provider config
└── automation.yaml               # Shizuku path, action timeouts, allowed app list

data/                             # GITIGNORED — created by setup wizard
├── memory.db                     # SQLite: memories + automation_log + notification_cache (WAL)
├── soul_identity.yaml
├── user_config.yaml
├── setup_state.yaml
├── cron_jobs.yaml
├── gurujee.keystore
├── session_context.yaml
├── heartbeat.log
├── memory.log
├── automation.log                # NEW: automation command log (RotatingFileHandler)
├── server.log                    # NEW: FastAPI/uvicorn access log
├── boot.log
└── backups/

tests/
├── conftest.py
├── test_soul_agent.py
├── test_memory_agent.py
├── test_heartbeat_agent.py
├── test_user_agent.py
├── test_cron_agent.py
├── test_automation_agent.py      # NEW
├── test_automation_actions.py    # NEW
├── test_server_chat.py           # NEW — FastAPI /chat SSE endpoint
├── test_server_automate.py       # NEW — FastAPI /automate endpoint
├── test_keystore.py
├── test_ai_client.py
└── test_setup_wizard.py

launcher/                         # Launcher APK (Kivy thin shell)
├── main.py                       # Kivy App: progress screen → WebView → localhost:7171
├── bootstrap.py                  # Termux install check, inject bootstrap script via am start
└── buildozer.spec                # Buildozer config (Phase 1: debug APK only)

install.sh                        # Termux bootstrap (idempotent, developer path)
requirements.txt                  # pinned production deps (add: fastapi, uvicorn, httpx)
pyproject.toml
.gitignore
```

**Structure Decision (ADR-003 v2)**: Split-layer. Daemon runs `GatewayDaemon` + all agents +
FastAPI/uvicorn as asyncio tasks in one Python process (`--headless` mode, default).
TUI (`--tui`) re-adds Textual to the same process for developer use. PWA served as static
files by FastAPI; loaded in Launcher APK WebView. Non-technical users never see a terminal.

---

## Architecture Decisions Applied

| ADR | Decision | Applied where |
|-----|----------|---------------|
| ADR-001 | Skill sandboxing via multiprocessing (Phase 3) | `agents/base_agent.py` hook; Phase 3 adds multiprocessing |
| ADR-002 | Hybrid recency-10 + keyword/tag SQLite retrieval | `memory/long_term.py` + `memory/short_term.py` |
| ADR-003 v2 | Split-layer: daemon + FastAPI + PWA; TUI = dev tool | `daemon/gateway_daemon.py` starts uvicorn; `server/` serves PWA; `--tui` re-adds Textual |
| R-008 | SQLite WAL + single writer (MemoryAgent) | `memory/long_term.py` (now also automation_log + notification_cache) |
| R-009 | PyYAML for machine files; ruamel.yaml for `data/soul_identity.yaml` | `config/loader.py` |

---

## Non-Functional Requirements Budget

| Requirement | Target | Implementation lever |
|-------------|--------|---------------------|
| Idle RAM (daemon + FastAPI) | ≤ 50 MB | uvicorn single worker, shared asyncio loop; no ML at idle; deque(10). Windows dev estimate: ~35–45 MB (data/benchmarks/idle-ram-001.txt). **T069 done**: profile confirmed ≤ 50 MB on ARM64/Termux. |
| First AI response (SSE) | < 5 s (3G) | AsyncOpenAI streaming; first SSE chunk to PWA before completion |
| PWA first paint | < 1 s (localhost) | Static files <200 KB total; service worker caches after first load |
| Automation command round-trip | < 3 s | Shizuku `rish` subprocess; async subprocess with timeout |
| TUI keystroke render (dev) | < 100 ms | Textual reactive updates; no blocking in UI thread |
| Daemon restart detection | < 10 s | HeartbeatAgent 8 s ping interval; 2 s pong timeout (from config/agents.yaml); worst-case detection = 10 s; restart on no-pong. Error path: no-pong → AGENT_STATUS_UPDATE(ERROR, reason=pong_timeout) → gateway increments restart_count and re-spawns. |
| APK → chat ready time | < 3 min | APK polls `/health`; daemon starts fast; setup resumes from state |
| Memory DB backup | weekly | asyncio scheduled task in MemoryAgent |

---

## Security Architecture

```
User PIN (4–8 digits; set in guided setup step 5; prompted on every launch)
  │
  └─► PBKDF2-HMAC-SHA256(pin, salt=device_fingerprint[:16], iterations=260_000)
         │
         └─► 32-byte AES-256 key (held in memory as bytearray, zeroed on lock())
                │
                └─► AES-256-GCM decrypt ─► data/gurujee.keystore
                                             │
                                             ├─ voice_id
                                             ├─ elevenlabs_api_key
                                             └─ sip_* (null Phase 1)

PIN lockout policy (FR-023):
  3 wrong attempts → 30-second lockout (exponential backoff on further failures)
  Forgot PIN → wipe data/gurujee.keystore + re-run guided setup (consequence shown in UI)

Network allowlist (ai/client.py::_build_allowlist()):
  Dynamic — built at daemon startup from:
  - All base_url hostnames from config/models.yaml (all active providers)
  - Security anchors from config/security.yaml:
      api.elevenlabs.io, sip.suii.us, stun.l.google.com, api.deepgram.com
  All other outbound: AllowlistViolation raised / user prompted for approval
```

---

## Phase 0 Research Outcome

All 10 research decisions resolved. See [research.md](research.md).
No NEEDS CLARIFICATION items remain. Key findings:
- Single-process architecture (R-007) saves ~25 MB RAM vs. split process.
- SQLite WAL + single writer pattern (R-008) eliminates concurrency bugs.
- ruamel.yaml for `data/soul_identity.yaml` only (R-009) preserves user edits; runtime copy in data/.
- Termux:Boot `~/.termux/boot/` mechanism confirmed (R-005).

---

## Phase 1 Design Outcome

All design artifacts generated:

| Artifact | Path | Status |
|----------|------|--------|
| Data model | `specs/001-gurujee-foundation/data-model.md` | ✅ 8 entities |
| Message bus contracts | `contracts/message-bus.md` | ✅ 12 message types |
| Keystore API | `contracts/keystore-api.md` | ✅ full interface |
| BaseAgent interface | `contracts/agent-base-interface.md` | ✅ ABC + lifecycle |
| Developer quickstart | `quickstart.md` | ✅ full layout + config |

**Post-design Constitution Re-check**: All P1–P10 gates pass. No violations introduced
during design. Single-process decision (R-007) strengthens P1 compliance.

---

## Complexity Tracking

> No constitution violations requiring justification.
> All design decisions align with P1–P10.

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| daemon + uvicorn exceeds 50 MB P1 RAM ceiling | Medium | High | Profile on real device before merge; fallback: swap uvicorn → aiohttp (lighter) |
| Shizuku not activated after reboot | High | Medium | AutomationAgent detects Shizuku absence on every command; surfaces friendly PWA error with re-activation steps |
| Shizuku `rish` shell not available on all ROMs | Low | High | Test on 3 ROM variants; fallback to `adb shell` via WiFi ADB if `rish` unavailable |
| PWA WebView blocked by Android WebView security policy | Low | High | Use `setAllowFileAccessFromFileURLs(false)`, `localhost` URL (not `file://`); test on Android 10–14 |
| faster-whisper ctranslate2 wheel missing for Termux | Medium | Low (Phase 2) | Fallback to `pywhispercpp`; Phase 1 has no active STT |
| PBKDF2 iterations too slow on low-end ARM64 | Low | Medium | Benchmarked on ARM64 — reduced to 260k (was 480k); unlock time < 2 s confirmed. |
| `android_id` unavailable in Termux on some ROMs | Low | Low | Fallback to `data/.device_salt` (random, stored) |
| Launcher APK sideload blocked by Android settings | Medium | Medium | Setup flow detects `INSTALL_PACKAGES` permission; guides user to Settings > Install unknown apps |
