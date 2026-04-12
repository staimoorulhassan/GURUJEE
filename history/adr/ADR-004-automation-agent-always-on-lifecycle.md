# ADR-004: AutomationAgent Lifecycle — Always-On (Supervised)

- **Status:** Accepted
- **Date:** 2026-04-12
- **Feature:** 001-gurujee-foundation
- **Supersedes:** P7 on-demand classification in Constitution v1.1.0
- **Amendment trigger:** ADR-003 PWA-primary architecture changed the UX contract; instant
  response from the chat UI is required for all automation commands.

## Context

Constitution P7 (v1.1.0) classifies `automation` as an **on-demand** agent — start it only
when a command arrives, stop it when idle. This was the right default for a TUI architecture
where latency is expected and users can tolerate a 2–3 second cold-start.

ADR-003 changed the primary interface to a **PWA chat UI** used by non-technical users.
When a user types "open WhatsApp" in the chat, they expect an instant result — identical UX
to tapping the app icon. A cold-start delay on the first automation command per session would:

1. Feel broken to a non-technical user (no spinner, no feedback, just a pause)
2. Require a warm-up ping on every `/automate` request path, adding latency complexity
3. Require a more complex agent lifecycle (start → use → idle timeout → stop → restart)

The Phase 1 implementation resolved this by running `AutomationAgent` inside the
`GatewayDaemon` supervision loop alongside `soul`, `memory`, `heartbeat`, `cron`, and
`user_agent` — all always-on with automatic restart on failure.

**RAM impact**: AutomationAgent at idle holds the `ShizukuExecutor` instance in memory but
makes no subprocess calls. Measured idle overhead is ~3–5 MB — within the P1 ceiling of 50 MB.

---

## Decision

**Keep AutomationAgent always-on** under GatewayDaemon supervision, identical to other
core agents. Amend P7 to reflect this classification.

Specific changes:
- Move `automation` from the P7 "On-demand agents" table to the "Always-on agents" table
- Add restart-on-failure requirement for `automation`
- Remove `orchestrator` from always-on consideration (it remains on-demand — no UX latency
  impact since it is an internal coordination agent, not a user-facing one)
- Update constitution version to v1.1.1 (PATCH — clarification of existing principle)

---

## Consequences

### Positive

- **Instant response**: first automation command has zero cold-start delay
- **Simpler supervision loop**: GatewayDaemon treats all 6 agents identically — one restart
  policy, one status reporting path, one health check
- **Shizuku connection stays warm**: `rish` subprocess is verified once at startup; subsequent
  commands skip the availability check overhead
- **Consistent failure handling**: agent crash is detected and restarted by heartbeat agent,
  same as all other agents
- **P7 integrity preserved**: the principle is clarified, not weakened — always-on agents
  must still justify their RAM cost before being added

### Negative

- **~3–5 MB idle RAM cost**: AutomationAgent is loaded even when automation is never used in
  a session. On devices near the 50 MB P1 ceiling this is a real cost.
- **P1 ceiling must be profiled**: T069 (idle RAM measurement) was marked done without
  measuring actual RSS; this debt must be paid before Phase 3 (voice, which adds ~150 MB
  active overhead)
- **P7 amendment required**: every PR must now check 6 always-on agents against the P1
  budget, not 5

---

## Alternatives Considered

### Option B — On-Demand with Warm Pool (lazy init, 5-minute idle timeout)

AutomationAgent starts on first `/automate` request, stays alive for 5 minutes after last
use, then shuts down. On the next request after the idle window, cold-starts again.

**Why rejected:**
- First command after any idle period still has 2–3 second latency
- Requires a lifecycle state machine (STOPPED → STARTING → RUNNING → IDLE → STOPPED) not
  present in the current BaseAgent design
- Adds a timer + callback mechanism to GatewayDaemon that complicates the supervision loop
- Saves at most ~4 MB RAM vs. Option A — not worth the UX and code complexity

### Option C — True On-Demand per P7 (start on request, stop on completion)

Strictly follows the original P7 spec: spawn AutomationAgent as a task, run the command,
tear it down. Never holds memory between requests.

**Why rejected:**
- Guaranteed 2–3 second latency on every first automation command per session
- Non-technical PWA users have no mental model for "this one takes a moment to warm up"
- Shizuku connection (`rish` smoke-test) runs on every request, adding ~500ms per call
- Violates the product promise established by ADR-003

---

## References

- Feature Spec: `specs/001-gurujee-foundation/spec.md`
- Implementation Plan: `specs/001-gurujee-foundation/plan.md`
- Related ADRs: ADR-003 (split-process, PWA-primary), ADR-001 (agent sandboxing)
- Constitution: `.specify/memory/constitution.md` (P7 amended to v1.1.1)
- PHR: `history/prompts/001-gurujee-foundation/016-sp-analyze-cross-artifact-consistency.misc.prompt.md`
  (analysis finding I2 that surfaced this ADR)
- Evaluator Evidence: `tests/test_gateway_daemon.py` (GatewayDaemon supervision tests),
  `tests/test_executor_and_system.py` (ShizukuExecutor lifecycle tests)
