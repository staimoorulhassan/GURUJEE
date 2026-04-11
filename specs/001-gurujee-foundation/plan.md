# Implementation Plan: GURUJEE Foundation

**Branch**: `001-gurujee-foundation` | **Date**: 2026-04-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-gurujee-foundation/spec.md`

---

## Summary

Build the Phase 1 foundation of GURUJEE: a persistent AI companion running as an asyncio
daemon inside Termux on a non-rooted Android phone. Phase 1 delivers guided first-run setup,
a 5-agent always-on daemon (soul + memory + heartbeat + user_agent + cron-dormant), a
Textual TUI with Chat and Agent Status screens, hybrid memory retrieval (recency + SQLite
keyword/tag search), AES-256-GCM keystore, and full Pollinations AI integration via the
openai SDK with streaming. The entire system runs in a single Python process under 50 MB
at idle.

---

## Technical Context

**Language/Version**: Python 3.11+ (Termux, Android ARM64)
**Primary Dependencies**: openai 1.x, Textual 0.47+, Rich 13+, cryptography 41+,
  PyYAML 23+, ruamel.yaml 0.18+, tenacity 8.2+, elevenlabs 1+ (install Phase 1, use Phase 2),
  faster-whisper 1+ (install Phase 1, use Phase 2), sqlite3 (stdlib), asyncio (stdlib)
**Storage**: SQLite (`data/memory.db`, stdlib sqlite3, WAL mode); YAML files for config/state
**Testing**: pytest 7.4+ with pytest-asyncio 0.23+ and responses 0.25+ for HTTP mocking;
  target 70% coverage on all agent files
**Target Platform**: Android 10+ non-rooted, Termux (F-Droid), aarch64 (ARM64)
**Project Type**: Single Python package; daemon + TUI in one process (R-007)
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
| **P2** Single Endpoint AI | ✅ PASS | `AsyncOpenAI(base_url="https://gen.pollinations.ai/v1", api_key="")`. Model IDs from `config/models.yaml`. No hardcoded model in logic (R-006). |
| **P3** No Root Required | ✅ PASS | All Termux operations are user-space. `android_id` via `settings get` (no root). Shizuku guided but not used until Phase 3. |
| **P4** Security First | ✅ PASS | AES-256-GCM keystore; PBKDF2-HMAC-SHA256 key derivation (R-004). Network allowlist enforced in `ai/client.py`. No secrets in config. Consent gate before voice sample (FR-001, US1-S5). |
| **P5** Guided Setup Mandatory | ✅ PASS | Rich wizard covers all 7 FR-001 steps. `data/setup_state.yaml` persists progress (FR-002). Termux:Boot script created by wizard (R-005). |
| **P6** Python-First Stack | ✅ PASS | All packages ARM64-compatible (R-003, R-004, R-006). No Node.js, no Electron, no JVM. |
| **P7** Agent Architecture Sacred | ✅ PASS | All 5 Phase-1 agents (soul, memory, heartbeat, user_agent, cron-dormant) implemented as asyncio Tasks. All comms via MessageBus/Queue. No direct inter-agent references (contracts/message-bus.md). |
| **P8** Voice/SIP First-Class | ✅ PASS | ElevenLabs SDK installed Phase 1; voice sample + consent in FR-001 step 6. streaming=True enforced in `ai/client.py` (P1-compliant). |
| **P9** Distribution | ✅ PASS | `install.sh` is the entry point. Accessibility APK from GitHub Releases + SHA-256 check (FR-001 step 3). `install.sh` idempotent by design. |
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
gurujee/                       # Python package root
├── __main__.py                # python -m gurujee entry point
├── agents/
│   ├── __init__.py
│   ├── base_agent.py          # BaseAgent ABC, MessageBus, MessageType enum
│   ├── soul_agent.py          # SoulAgent: identity + prompt injection + AI stream
│   ├── memory_agent.py        # MemoryAgent: short-term deque + SQLite long-term
│   ├── heartbeat_agent.py     # HeartbeatAgent: ping/pong watchdog + restart
│   ├── user_agent.py          # UserAgent: user profile from soul_identity.yaml
│   └── cron_agent.py          # CronAgent: dormant, empty schedule, Phase 1
├── daemon/
│   └── gateway_daemon.py      # GatewayDaemon: starts/monitors/routes all agents
├── tui/
│   ├── __init__.py
│   ├── app.py                 # Textual App; runs daemon as Worker
│   ├── theme.py               # CSS constants: bg=#0a0a0a amber=#f0a500 orange=#ff6b00
│   └── screens/
│       ├── chat_screen.py     # Chat: scrollable history + input
│       ├── agent_status_screen.py  # Agent Status: live status table
│       └── settings_screen.py     # Settings: soul edit + model select + Phase 2 stubs
├── setup/
│   ├── __init__.py
│   └── wizard.py              # Rich guided setup (7 steps)
├── keystore/
│   ├── __init__.py
│   └── keystore.py            # AES-256-GCM; PBKDF2-HMAC-SHA256 (contracts/keystore-api.md)
├── memory/
│   ├── __init__.py
│   ├── short_term.py          # ConversationTurn deque(maxlen=10)
│   └── long_term.py           # MemoryRecord SQLite CRUD; WAL; backup (ADR-002)
├── ai/
│   ├── __init__.py
│   └── client.py              # AsyncOpenAI wrapper; tenacity retry; streaming
└── config/
    ├── __init__.py
    └── loader.py              # PyYAML + ruamel.yaml loaders; env var overrides

agents/                        # shipped defaults (version-controlled)
└── soul_identity.yaml         # GURUJEE identity template — copied to data/ on first run

config/                        # version-controlled app config
├── models.yaml                # AI model catalogue + endpoint
├── agents.yaml                # heartbeat intervals, memory limits, logging
└── voice.yaml                 # voice provider config (ElevenLabs model, streaming mode)

data/                          # GITIGNORED — created by setup wizard
├── memory.db                  # SQLite long-term memories (WAL mode)
├── soul_identity.yaml         # GURUJEE identity — runtime copy (ruamel.yaml R/W)
├── user_config.yaml           # user runtime prefs (active_model, active_voice_id, tui_theme)
├── setup_state.yaml           # guided setup progress
├── cron_jobs.yaml             # scheduled jobs (empty Phase 1)
├── gurujee.keystore           # AES-256-GCM encrypted secrets
├── session_context.yaml       # short-term context serialised on shutdown
├── heartbeat.log              # RotatingFileHandler 5MB × 3
├── memory.log                 # memory agent + backup events
├── boot.log                   # Termux:Boot startup events
└── backups/                   # weekly memory.db snapshots

tests/
├── conftest.py                # fixtures: mock MessageBus, temp data dir, fake openai
├── test_soul_agent.py
├── test_memory_agent.py
├── test_heartbeat_agent.py
├── test_user_agent.py
├── test_cron_agent.py
├── test_keystore.py
├── test_ai_client.py
└── test_setup_wizard.py

install.sh                     # Termux bootstrap (idempotent)
requirements.txt               # pinned production deps
pyproject.toml                 # package metadata + pytest config
.gitignore                     # excludes data/, *.keystore, *.log, __pycache__
```

**Structure Decision**: Single Python package. One process: Textual App runs the event
loop; `GatewayDaemon` and all agents run as asyncio Tasks within Textual's loop via
`app.run_worker()`. Headless mode (`--headless`) skips Textual and runs a bare asyncio
loop directly — used by Termux:Boot.

---

## Architecture Decisions Applied

| ADR | Decision | Applied where |
|-----|----------|---------------|
| ADR-001 | Skill sandboxing via multiprocessing (Phase 3) | `agents/base_agent.py` leaves hook for skill dispatch; Phase 3 adds multiprocessing |
| ADR-002 | Hybrid recency-10 + keyword/tag SQLite retrieval | `memory/long_term.py` + `memory/short_term.py` |
| R-007 | Single process: Textual + daemon as Workers | `tui/app.py` + `daemon/gateway_daemon.py` |
| R-008 | SQLite WAL + single writer (MemoryAgent) | `memory/long_term.py` |
| R-009 | PyYAML for machine files; ruamel.yaml for `data/soul_identity.yaml` | `config/loader.py` |

---

## Non-Functional Requirements Budget

| Requirement | Target | Implementation lever |
|-------------|--------|---------------------|
| Idle RAM | < 50 MB | No ML models loaded at idle; sqlite3 WAL; deque(10); Textual lazy widget load |
| First AI response | < 5 s (3G) | AsyncOpenAI streaming; first chunk to TUI before completion |
| TUI keystroke render | < 100 ms | Textual reactive updates; no blocking in UI thread |
| Daemon restart detection | < 10 s | HeartbeatAgent 30 s ping interval; 5 s timeout; restart on no-pong |
| Setup completion | < 10 min | All steps scripted; no manual copy-paste |
| Memory DB backup | weekly | `threading.Timer` or asyncio scheduled in MemoryAgent |

---

## Security Architecture

```
User PIN (4–8 digits; set in guided setup step 5; prompted on every launch)
  │
  └─► PBKDF2-HMAC-SHA256(pin, salt=device_fingerprint[:16], iterations=480_000)
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

Network allowlist (ai/client.py):
  - gen.pollinations.ai     (AI inference)
  - api.elevenlabs.io       (voice clone setup)
  All other outbound: blocked / warned
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
| faster-whisper ctranslate2 wheel missing for Termux Python version | Medium | Low (Phase 2) | Documented fallback to `pywhispercpp`; Phase 1 has no active STT |
| Textual 80-column layout breaks on narrow Android screen | Medium | Medium | Design all screens for ≥80 cols; test at 80-col minimum |
| PBKDF2 480k iterations too slow on low-end ARM64 | Low | Medium | Benchmark on target device; reduce to 260k if > 2 s unlock time |
| `android_id` unavailable in Termux on some ROMs | Low | Low | Fallback to `data/.device_salt` (random, stored) documented in keystore contract |
