# ADR-003: TUI + Daemon Single-Process Architecture

- **Status:** Accepted
- **Date:** 2026-04-11
- **Feature:** 001-gurujee-foundation
- **Context:** GURUJEE requires two logical subsystems: a gateway daemon (always-on,
  manages all agents, routes messages via asyncio.Queue) and a TUI (user-facing Textual
  interface for chat, agent status, and settings). The fundamental question is whether
  these run in one OS process or two. The decision is constrained by constitution P1
  (idle RAM < 50 MB), the Termux single-user single-device deployment model, and the
  need for a `--headless` mode for Termux:Boot auto-start without a visible terminal UI.

## Decision

**Run the TUI and the gateway daemon as a single Python process.**

- The Textual `App` is the process entry point.
- All agents (soul, memory, heartbeat, user_agent, cron-dormant) run as asyncio `Task`s
  inside Textual's own event loop, launched via `app.run_worker()`.
- The `GatewayDaemon` is a coroutine managed by the Textual App, not a separate process.
- A `--headless` flag (`python -m gurujee --headless`) bypasses Textual entirely and runs
  a bare `asyncio.run(gateway.start())` — used exclusively by `~/.termux/boot/start-gurujee.sh`.
- Inter-agent communication uses `asyncio.Queue` (in-process); no sockets, no pipes, no
  shared memory segments across process boundaries.
- TUI ↔ agent communication uses Textual's `app.post_message()` / `app.call_from_thread()`
  APIs, which are thread-safe and asyncio-native.

**Entry points**:

| Command | Mode | Process |
|---------|------|---------|
| `python -m gurujee` | TUI + daemon | single process, Textual event loop |
| `python -m gurujee --headless` | daemon only | single process, bare asyncio loop |
| `python -m gurujee.setup` | setup wizard | separate process (Rich; no daemon) |

## Consequences

### Positive

- **P1 compliance**: A second Python interpreter adds ~25 MB RSS on ARM64 Termux. The
  single-process model keeps idle well under the 50 MB constitutional ceiling with headroom
  for agent state growth.
- **Zero IPC complexity**: asyncio `Queue` is in-process. No Unix socket protocol, no
  serialisation format, no connection lifecycle to manage. Message contracts (see
  `contracts/message-bus.md`) are Python dataclasses — never serialised.
- **Single PID to manage**: Termux:Boot, `kill`, `ps`, and the heartbeat agent all track
  one process. Restart semantics are simple.
- **Shared asyncio loop**: Textual's `App` already owns an event loop. Agents share it
  for free — no thread pool, no `run_in_executor` overhead for normal agent operations.
- **Headless mode**: `--headless` gives Termux:Boot exactly the right behaviour (daemon
  running, no terminal UI consuming the window) without a second process.

### Negative

- **TUI crash kills agents**: If a Textual exception propagates to `App.run()` and is
  unhandled, the entire process — including all agents — dies. **Mitigation**: Textual's
  global exception handler is overridden to log and continue; agent `Task`s are wrapped
  in try/except with heartbeat-managed restart.
- **TUI crash in headless mode is contained**: In `--headless`, Textual is never loaded,
  so this risk only applies to normal TUI mode. Termux:Boot uses `--headless` only.
- **Cannot attach a second UI later (without refactor)**: If a future requirement adds a
  web UI or remote monitoring panel, the in-process Queue bus must be replaced with a
  serialisable IPC layer (Unix socket or WebSocket). This refactor is non-trivial.
  **Mitigation**: The `MessageBus` class is the only inter-agent boundary. Replacing its
  internal `asyncio.Queue` delivery with socket delivery is localised to `base_agent.py`
  and `gateway_daemon.py` — not a rewrite.
- **Test isolation**: In tests, instantiating `App` for every agent test adds overhead.
  **Mitigation**: Agent unit tests use a mock `MessageBus` directly; the Textual `App`
  is only tested in integration tests.

## Alternatives Considered

**Option B — Split process: daemon + TUI as separate processes via Unix socket**

- Architecture: `gateway_daemon.py` runs as an independent process. `tui/app.py` connects
  to it via a Unix domain socket (`/tmp/gurujee.sock`). All messages serialised to JSON
  over the socket.
- Pros: TUI can crash and restart without killing agents. Future web UI can connect to
  the same socket. Clean separation of concerns.
- Cons:
  - ~25 MB additional RSS for the second Python interpreter on ARM64 — directly violates
    the P1 50 MB idle ceiling on 2–3 GB RAM devices after OS and other Termux overhead.
  - Unix socket IPC requires a serialisation protocol. The current asyncio.Queue +
    Python dataclass design becomes JSON marshalling/unmarshalling with error handling
    for partial reads, connection drops, and reconnects.
  - Two processes to manage: Termux:Boot must start both; if one dies the other must detect
    it; `ps`, logging, and debugging become more complex.
  - Premature: no current requirement for a web UI or remote monitoring.
  - **Rejected** on P1 RAM grounds and complexity cost for a feature with no current
    requirement.

**Option C — Multiprocessing pool: daemon in main process, each agent as a subprocess**

- Architecture: `gateway_daemon.py` spawns each agent as a `multiprocessing.Process`.
  Message bus becomes `multiprocessing.Queue`.
- Cons: 5 agent processes × ~15 MB each = ~75 MB just for agents, catastrophically violating
  P1. `multiprocessing.spawn` on ARM64 Linux is ~150 ms per process — adds seconds to startup.
  **Rejected immediately** on P1 grounds.

## Revisit Trigger

This decision MUST be revisited if:
1. A Phase 3+ requirement introduces a web UI or remote monitoring panel.
2. Profiling shows TUI exceptions killing the daemon more than once per week in production.
3. A new always-on agent is added that benefits from OS-level process isolation
   (e.g., a network-facing listener).

The revisit path is: swap `MessageBus` internals to Unix socket delivery → agents
become subprocess-compatible without structural changes. The `--headless` flag already
proves the daemon can run without Textual.

## References

- Feature Spec: specs/001-gurujee-foundation/spec.md (FR-010, FR-011, FR-003)
- Implementation Plan: specs/001-gurujee-foundation/plan.md (R-007)
- Research: specs/001-gurujee-foundation/research.md (R-007)
- Agent Interface: specs/001-gurujee-foundation/contracts/agent-base-interface.md
- Message Bus: specs/001-gurujee-foundation/contracts/message-bus.md
- Related ADRs: ADR-001 (Skill Sandboxing — multiprocessing for Phase 3 skills, not agents)
