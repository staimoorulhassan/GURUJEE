# ADR-003: Split-Process Architecture — Daemon + PWA + TUI as Dev Tool

- **Status:** Accepted (supersedes ADR-003 v1: TUI + Daemon Single-Process)
- **Date:** 2026-04-12
- **Supersedes:** ADR-003-tui-daemon-single-process-architecture.md (2026-04-11)
- **Feature:** 001-gurujee-foundation
- **Amendment trigger:** User requirement shift — non-technical users cannot use a terminal.
  Primary UI must be a user-friendly chat app (WhatsApp-style), not a Textual TUI.

## Context

The original ADR-003 (2026-04-11) chose a **single-process** architecture: Textual TUI + daemon
as asyncio Tasks in one Python process. That decision was correct given the original requirement
(TUI as primary UI, P1 RAM budget, no web UI requirement).

The requirement has now fundamentally changed:

1. **Primary users are non-technical** — they cannot use a terminal. A Textual TUI is not viable
   as the primary interface.
2. **The Launcher APK** (thin Kivy shell) must load a user-friendly PWA chat interface in a
   WebView — WhatsApp/iMessage style, voice input, works offline.
3. **The PWA must be served by the daemon** on `localhost:7171` via FastAPI + uvicorn.
4. **The TUI is now a developer/admin tool only** — launched with `python -m gurujee --tui`.
5. **Phase 3 automation** requires Shizuku shell commands, which are subprocess calls — the
   process isolation this enables aligns better with a daemon-centric architecture.

The "premature" concern from ADR-003 v1 ("no current requirement for a web UI") is now resolved:
the web UI (PWA) IS the current requirement.

---

## Decision

**Run the daemon and the primary UI as two separate logical layers communicating over localhost.**

```
┌─────────────────────────────────────────────────┐
│  GURUJEE Launcher APK (Kivy thin shell)         │
│  • Bootstrap orchestration                       │
│  • Progress screen during daemon startup         │
│  • WebView → loads localhost:7171 (PWA)          │
│  Phase 2+: full Kivy APK wrapping the PWA        │
└──────────────────┬──────────────────────────────┘
                   │  HTTP + WebSocket
                   │  127.0.0.1:7171
┌──────────────────▼──────────────────────────────┐
│  GURUJEE Daemon (Python asyncio in Termux)      │
│                                                  │
│  GatewayDaemon                                   │
│    ├── soul_agent       (always-on)              │
│    ├── memory_agent     (always-on)              │
│    ├── heartbeat_agent  (always-on)              │
│    ├── user_agent       (always-on)              │
│    ├── cron_agent       (always-on, dormant P1)  │
│    └── automation_agent (on-demand, Phase 1)     │
│                                                  │
│  FastAPI server (uvicorn, 127.0.0.1:7171)        │
│    ├── POST /chat          (SSE streaming)       │
│    ├── GET  /agents        (agent status)        │
│    ├── POST /automate      (automation commands) │
│    ├── GET  /notifications (notification cache)  │
│    ├── GET  /health        (APK readiness poll)  │
│    └── WebSocket /ws       (real-time push)      │
│                                                  │
│  Static PWA served at /  (HTML/CSS/JS)           │
│    • WhatsApp-style chat bubbles                 │
│    • Voice input (Web Speech API or /transcribe) │
│    • Service worker cache (offline-first)        │
│    • Agent status bar (subtle, not full panel)   │
└─────────────────────────────────────────────────┘

TUI (developer/admin only — python -m gurujee --tui)
  • Connects to same daemon via in-process bus OR localhost:7171
  • Used for: debugging, agent status deep-dive, settings admin
  • Never shown to end users
```

**Process model:**

| Command | Mode | Process | Who uses it |
|---------|------|---------|-------------|
| APK tap | Full user flow | Kivy APK + Termux daemon | Non-technical users |
| `python -m gurujee --headless` | Daemon only | Single Python process, bare asyncio | Termux:Boot, CI |
| `python -m gurujee --tui` | TUI + daemon | Single Python process, Textual loop | Developers/admins |
| `python -m gurujee.setup` | Setup wizard | Separate process, Rich CLI | Developer path |

**FastAPI server rules (P6 amendment):**
- MUST bind to `127.0.0.1` only — never `0.0.0.0`.
- MUST be started as an asyncio task inside `GatewayDaemon` via `uvicorn.Config` + `Server.serve()`.
- All API endpoints MUST require a session token for non-localhost callers (Phase 2 hardening).

---

## Consequences

### Positive

- **Non-technical users served**: The PWA in a WebView is indistinguishable from a native app.
  No terminal knowledge required.
- **Clean separation of concerns**: UI layer (PWA/WebView) is completely decoupled from agent
  logic. PWA can be updated without touching Python.
- **Future-proof**: The FastAPI server is the stable interface. Phase 2 Kivy APK, Phase 3
  remote access, and future iOS PWA all connect to the same server without code changes.
- **TUI crash isolation**: TUI running separately (`--tui`) cannot kill daemon agents — the
  in-process risk from ADR-003 v1 is eliminated.
- **Automation-ready**: `automation_agent` runs shell subprocesses (Shizuku commands) inside
  the daemon process — no cross-process complication for Phase 1 automation.

### Negative (and mitigations)

- **RAM increase**: FastAPI + uvicorn adds ~8–12 MB RSS at idle on ARM64.
  **Mitigation**: uvicorn started with `workers=1`, `loop="asyncio"` (no multiprocessing),
  shared event loop with GatewayDaemon. Measured budget: daemon 38 MB + uvicorn 12 MB = 50 MB
  — exactly at the P1 ceiling. Profile before merge; if over, drop uvicorn and use
  `aiohttp` (lighter) or raw `asyncio` HTTP server.
- **PWA static asset serving**: Serving HTML/JS/CSS adds I/O. **Mitigation**: Files are
  small (<200 KB total); served from Termux storage; cached by service worker after first load.
- **No Unix socket for TUI**: The `--tui` mode originally shared an in-process Queue. Now
  the TUI either: (a) runs in the same process in headless-compatible mode, or (b) connects
  via localhost:7171 WebSocket. **Decision**: TUI (`--tui`) runs in same process as the daemon
  (Textual `App` owns the loop, daemon as Worker) — preserving the original R-007 single-process
  benefit for the dev path. The PWA path is always via HTTP/WS.

### RAM Budget Revision

| State | Previous budget | New budget |
|-------|----------------|------------|
| Idle daemon (headless) | 50 MB | 50 MB (unchanged ceiling) |
| Daemon + FastAPI/uvicorn | N/A | ≤50 MB (target; profile required) |
| Active TUI (`--tui`) | 120 MB | 120 MB (unchanged, dev tool) |
| Active AI voice | 200 MB | 200 MB (unchanged) |
| Active PWA in WebView | N/A | ~30 MB (Chrome WebView overhead, APK only) |

---

## Alternatives Considered

**Option A — Keep single-process TUI as primary UI**
- Rejected: Non-technical users cannot use a terminal. Contradicts the core user requirement.

**Option B — Kivy APK with full native UI (no PWA)**
- Rejected for Phase 1: Buildozer compile is slow and brittle on ARM64. PWA ships faster
  and is equally capable for the feature set needed. Kivy APK deferred to Phase 2.

**Option C — PWA served from a separate Node.js/Deno server**
- Rejected: Violates P6 (no Node.js). Python FastAPI serves static files natively.

---

## Revisit Triggers

1. Profiling shows daemon + uvicorn exceeds 50 MB P1 ceiling → switch to `aiohttp` or raw asyncio.
2. Phase 2 Kivy APK requirement → wrap PWA in WebView widget, no server changes needed.
3. Remote access requirement (Phase 3+) → add auth middleware to FastAPI server (already structured for it).

---

## References

- Feature Spec: specs/001-gurujee-foundation/spec.md (FR-010, FR-011, FR-003)
- Implementation Plan: specs/001-gurujee-foundation/plan.md
- Constitution: P1 (RAM), P3 (no root), P5 (zero-touch setup), P6 (PWA+FastAPI), P9 (APK distro)
- Superseded: ADR-003-tui-daemon-single-process-architecture.md
- Related: ADR-001 (Skill Sandboxing), ADR-002 (Memory Retrieval)
