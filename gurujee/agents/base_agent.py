"""Base agent infrastructure: MessageType enum, Message dataclass, MessageBus, BaseAgent ABC."""
from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Optional


class MessageType(Enum):
    # Chat
    CHAT_REQUEST = auto()
    CHAT_CHUNK = auto()
    CHAT_RESPONSE_COMPLETE = auto()
    CHAT_ERROR = auto()
    # Memory
    MEMORY_CONTEXT_REQUEST = auto()
    MEMORY_CONTEXT_RESPONSE = auto()
    MEMORY_STORE = auto()
    MEMORY_STORED = auto()
    # Heartbeat
    HEARTBEAT_PING = auto()
    HEARTBEAT_PONG = auto()
    # Agent lifecycle
    AGENT_STATUS_UPDATE = auto()
    SETUP_COMPLETE = auto()
    SHUTDOWN = auto()
    # User profile
    USER_PROFILE_REQUEST = auto()
    USER_PROFILE_RESPONSE = auto()
    # Automation (Phase 1 — US4)
    AUTOMATE_REQUEST = auto()
    AUTOMATE_RESULT = auto()


@dataclass
class Message:
    """A typed message passed between agents via the message bus."""

    type: MessageType
    from_agent: str
    to_agent: str
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reply_to: Optional[str] = None
    ttl: int = 10


class MessageBus:
    """Routes Message objects to registered agent inboxes."""

    def __init__(self) -> None:
        self._inboxes: dict[str, asyncio.Queue[Message]] = {}

    def register_agent(self, name: str, inbox: asyncio.Queue[Message]) -> None:
        """Register *inbox* under *name* so messages can be routed to it."""
        self._inboxes[name] = inbox

    def deregister_agent(self, name: str) -> None:
        """Remove *name* from the routing table (no-op if absent)."""
        self._inboxes.pop(name, None)

    async def send(self, msg: Message) -> None:
        """Deliver *msg* to its target inbox.

        If to_agent == "broadcast", deliver to all registered agents.
        Drops messages with expired TTL.
        """
        if msg.ttl <= 0:
            return

        msg = Message(
            type=msg.type,
            from_agent=msg.from_agent,
            to_agent=msg.to_agent,
            payload=msg.payload,
            id=msg.id,
            timestamp=msg.timestamp,
            reply_to=msg.reply_to,
            ttl=msg.ttl - 1,
        )

        if msg.to_agent == "broadcast":
            for inbox in self._inboxes.values():
                await inbox.put(msg)
        elif msg.to_agent in self._inboxes:
            await self._inboxes[msg.to_agent].put(msg)


class BaseAgent(ABC):
    """Abstract base class for all GURUJEE agents."""

    def __init__(self, name: str, bus: MessageBus) -> None:
        self.name = name
        self._bus = bus
        self._inbox: asyncio.Queue[Message] = asyncio.Queue()
        self._handlers: dict[MessageType, Callable[[Message], Coroutine[Any, Any, None]]] = {}
        bus.register_agent(name, self._inbox)

    # ------------------------------------------------------------------ #
    # Abstract lifecycle                                                    #
    # ------------------------------------------------------------------ #

    @abstractmethod
    async def run(self) -> None:
        """Main agent coroutine — loop until SHUTDOWN received."""

    @abstractmethod
    async def handle_message(self, msg: Message) -> None:
        """Dispatch a received message."""

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    async def send(
        self,
        to: str,
        msg_type: MessageType,
        payload: Optional[dict[str, Any]] = None,
        reply_to: Optional[str] = None,
    ) -> None:
        """Send a typed message to *to* via the bus."""
        await self._bus.send(
            Message(
                type=msg_type,
                from_agent=self.name,
                to_agent=to,
                payload=payload or {},
                reply_to=reply_to,
            )
        )

    async def broadcast(
        self,
        msg_type: MessageType,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        """Broadcast *msg_type* to all registered agents."""
        await self.send("broadcast", msg_type, payload)

    def register_handler(
        self,
        msg_type: MessageType,
        fn: Callable[[Message], Coroutine[Any, Any, None]],
    ) -> None:
        """Register *fn* as the handler for *msg_type*."""
        self._handlers[msg_type] = fn

    async def _dispatch(self, msg: Message) -> None:
        """Invoke registered handler for *msg.type*, or fall back to handle_message."""
        handler = self._handlers.get(msg.type)
        if handler is not None:
            await handler(msg)
        else:
            await self.handle_message(msg)
