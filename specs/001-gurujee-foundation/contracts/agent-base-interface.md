# BaseAgent Interface Contract

**Branch**: `001-gurujee-foundation` | **Date**: 2026-04-11

Every agent in GURUJEE inherits from `BaseAgent` (`gurujee/agents/base_agent.py`).
This contract defines the interface all agents MUST implement.

---

## Abstract Base Class

```python
class BaseAgent(ABC):
    name: str                        # class-level constant; must be unique
    restart_on_failure: bool = True  # override to False for optional agents

    def __init__(self, bus: MessageBus) -> None: ...
        # bus: reference to GatewayDaemon's MessageBus instance
        # self.inbox: asyncio.Queue[Message] — assigned by GatewayDaemon at start

    @abstractmethod
    async def run(self) -> None:
        """
        Main agent loop. MUST:
        - Set self._running = True on entry.
        - Loop on `await self.inbox.get()` while self._running.
        - Handle MessageType.SHUTDOWN by breaking the loop cleanly.
        - NOT raise unhandled exceptions (catch all, log, emit error metric).
        """
        ...

    async def handle_message(self, msg: Message) -> None:
        """
        Dispatch a received message to the appropriate handler.
        Default impl calls self._handlers[msg.type](msg) if registered;
        logs WARNING for unknown types.
        """
        ...

    async def send(self, to_agent: str, type: MessageType, payload: dict,
                   reply_to: str | None = None) -> None:
        """
        Place a Message on the outbox Queue (GatewayDaemon routes it).
        Agents NEVER put messages directly on another agent's inbox.
        """
        ...

    async def broadcast(self, type: MessageType, payload: dict) -> None:
        """Convenience: send to 'broadcast' (gateway delivers to all agents)."""
        ...

    def register_handler(self, msg_type: MessageType,
                          handler: Callable[[Message], Awaitable[None]]) -> None:
        """Register a coroutine to handle a specific MessageType."""
        ...
```

---

## Lifecycle Contract

```
GatewayDaemon                    BaseAgent
     │                               │
     ├─ create_agent()               │
     ├─ assign inbox Queue           │
     ├─ asyncio.create_task(run()) ──►│ run() starts
     │                               │ _running = True
     │                               │ loop: inbox.get() → handle_message()
     │                               │
     ├─ send(HEARTBEAT_PING) ────────►│ handle → send HEARTBEAT_PONG
     │                               │
     ├─ send(SHUTDOWN) ──────────────►│ handle → _running = False
     │                               │ flush state
     │                               │ return (task completes)
     │◄──────────────── task done ───┤
```

---

## Required Agent Implementations (Phase 1)

| Agent | Class | `name` | Always-on | Phase |
|-------|-------|--------|-----------|-------|
| Soul | `SoulAgent` | `"soul"` | Yes | 1 |
| Memory | `MemoryAgent` | `"memory"` | Yes | 1 |
| Heartbeat | `HeartbeatAgent` | `"heartbeat"` | Yes | 1 |
| UserAgent | `UserAgent` | `"user_agent"` | Yes | 1 |
| Cron | `CronAgent` | `"cron"` | Yes (dormant) | 1 |

---

## MessageBus Interface

```python
class MessageBus:
    async def send(self, msg: Message) -> None:
        """Route message to the named agent's inbox Queue."""
        ...

    def register_agent(self, name: str, inbox: asyncio.Queue) -> None:
        """Called by GatewayDaemon when an agent starts."""
        ...

    def deregister_agent(self, name: str) -> None:
        """Called when an agent is stopped or crashes."""
        ...
```

The `MessageBus` is the only shared object between agents and the gateway.
Agents receive a reference at construction; they MUST NOT store references to
sibling agents.
