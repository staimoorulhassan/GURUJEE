# Agent Message Bus Contracts

**Branch**: `001-gurujee-foundation` | **Date**: 2026-04-11

GURUJEE agents communicate exclusively via typed `Message` objects placed on per-agent
`asyncio.Queue` inboxes. This document defines every `MessageType` in Phase 1, its
required payload fields, and the expected handler behaviour.

**Routing rule**: The `GatewayDaemon` reads from a single central `outbox` Queue and
delivers to the target agent's `inbox` Queue. Agents NEVER hold a reference to another
agent's Queue directly.

---

## Message Envelope

```python
@dataclass
class Message:
    id: str               # uuid4()
    from_agent: str       # "tui" | "gateway" | agent name
    to_agent: str         # agent name | "broadcast" | "gateway"
    type: MessageType
    payload: dict
    timestamp: datetime   # UTC
    reply_to: str | None  # id of originating message
    ttl: int = 10         # discard if routed > ttl times
```

---

## MessageType Enum and Contracts

### CHAT_REQUEST

**Direction**: `tui` → `gateway` → `soul`
**Purpose**: User sends a chat message; soul agent handles AI inference.

```python
payload = {
    "text": str,           # raw user input text
    "session_id": str,     # uuid for grouping turns
}
```

**Handler (SoulAgent)**:
1. Build system prompt from `soul_identity.yaml` + current date + user name.
2. Request short-term context from `MemoryAgent` via `MEMORY_CONTEXT_REQUEST`.
3. Await `MEMORY_CONTEXT_RESPONSE`.
4. Stream AI response chunks → emit `CHAT_CHUNK` messages to gateway → TUI.
5. On stream complete → emit `CHAT_RESPONSE_COMPLETE`.
6. Emit `MEMORY_STORE` with the full exchange.

---

### CHAT_CHUNK

**Direction**: `soul` → `gateway` → `tui`
**Purpose**: Streaming token delivery to TUI chat panel.

```python
payload = {
    "session_id": str,
    "chunk": str,          # partial text token(s)
    "done": bool,          # True on final chunk
}
```

---

### CHAT_RESPONSE_COMPLETE

**Direction**: `soul` → `gateway` → `tui`
**Purpose**: Signals end of streaming response; TUI finalises the message widget.

```python
payload = {
    "session_id": str,
    "full_text": str,      # complete assembled response
    "tokens_used": int | None,
}
```

---

### CHAT_ERROR

**Direction**: `soul` → `gateway` → `tui`
**Purpose**: AI endpoint unreachable or returned error after all retries exhausted.

```python
payload = {
    "session_id": str,
    "error_code": str,     # "ENDPOINT_UNREACHABLE" | "RATE_LIMITED" | "MALFORMED_RESPONSE"
    "error_message": str,
    "queued_for_retry": bool,
}
```

**TUI behaviour**: Show error inline in chat; if `queued_for_retry=True` show a
"Will retry when connection restores" indicator.

---

### MEMORY_CONTEXT_REQUEST

**Direction**: `soul` → `gateway` → `memory`
**Purpose**: Soul agent requests relevant memories to inject into the next prompt.

```python
payload = {
    "query_text": str,     # current user message (for tag extraction)
    "reply_to": str,       # message id to reply with context
}
```

---

### MEMORY_CONTEXT_RESPONSE

**Direction**: `memory` → `gateway` → `soul`
**Purpose**: Memory agent returns relevant context for prompt injection.

```python
payload = {
    "recent_turns": list[dict],    # last ≤10 ConversationTurns as {role, content}
    "long_term_facts": list[str],  # top ≤5 MemoryRecord.content strings
    "reply_to": str,
}
```

---

### MEMORY_STORE

**Direction**: `soul` | `tui` → `gateway` → `memory`
**Purpose**: Persist a memory to long-term storage.

```python
payload = {
    "content": str,
    "category": str,       # person | place | preference | fact | task
    "importance": float,   # 0.0–1.0; default 0.5; explicit "remember" → 1.0
    "source": str,         # "conversation" | "explicit"
}
```

**Handler (MemoryAgent)**: extract tags via heuristic → INSERT into `memories` table.
Emit `MEMORY_STORED` back to sender if `reply_to` present.

---

### MEMORY_STORED

**Direction**: `memory` → `gateway` → `soul` | `tui`
**Purpose**: Acknowledgement of successful persist; TUI may show "✓ Remembered" indicator.

```python
payload = {
    "memory_id": int,
    "reply_to": str,
}
```

---

### HEARTBEAT_PING

**Direction**: `heartbeat` → `gateway` → each agent (broadcast)
**Purpose**: Liveness check. Agents that do not reply within 5 s are considered dead.

```python
payload = {
    "ping_id": str,        # uuid4
    "sent_at": str,        # ISO-8601
}
```

---

### HEARTBEAT_PONG

**Direction**: each agent → `gateway` → `heartbeat`
**Purpose**: Agent alive acknowledgement.

```python
payload = {
    "ping_id": str,        # echoed from PING
    "agent_name": str,
    "status": str,         # "healthy" | "degraded"
    "details": str | None, # optional status detail
}
```

---

### AGENT_STATUS_UPDATE

**Direction**: `gateway` → `tui`
**Purpose**: Notify TUI of agent state change (start / stop / error / restart).

```python
payload = {
    "agent_name": str,
    "status": str,         # STARTING | RUNNING | STOPPED | ERROR
    "restart_count": int,
    "error_message": str | None,
}
```

**TUI behaviour**: Update the Agent Status screen reactive attribute; flash the row on change.

---

### SETUP_COMPLETE

**Direction**: `setup_wizard` → `gateway`
**Purpose**: Signals that guided setup finished; gateway should start all agents.

```python
payload = {
    "completed_steps": list[str],
    "skipped_steps": list[str],
}
```

---

### SHUTDOWN

**Direction**: `gateway` → all agents (broadcast)
**Purpose**: Ordered shutdown. Agents MUST flush state and exit their run loop cleanly.

```python
payload = {
    "reason": str,         # "user_exit" | "signal" | "error"
    "timeout_seconds": int,  # default 5
}
```

**Handler**: Each agent writes any pending state, closes file handles, and sets
`self._running = False`. Gateway waits up to `timeout_seconds` for all Tasks to complete.

---

## Startup Sequence

```
GatewayDaemon.start()
  │
  ├─ start SoulAgent       (P1) → AGENT_STATUS_UPDATE(STARTING → RUNNING)
  ├─ start MemoryAgent     (P2) → loads DB, replays session_context.yaml
  ├─ start HeartbeatAgent  (P3) → begins 30s ping interval
  ├─ start UserAgent       (P4) → loads user profile from soul_identity.yaml
  └─ start CronAgent       (P5, dormant) → loads cron_jobs.yaml (empty)
       │
       └─ All RUNNING → emit AGENT_STATUS_UPDATE × 5 to TUI
```

---

## Error Handling Contracts

| Scenario | Behaviour |
|----------|-----------|
| Agent inbox Queue full (>1000 items) | Discard oldest item; log warning |
| Message TTL exceeded | Discard silently; log at DEBUG level |
| Unknown `to_agent` name | Log WARNING; do not deliver |
| Payload missing required field | Log ERROR; do not deliver; emit DEAD_LETTER to gateway |
| Agent non-responsive to PING | HeartbeatAgent cancels Task; restarts agent; emits AGENT_STATUS_UPDATE(ERROR → STARTING) |
