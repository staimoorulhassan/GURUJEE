"""GatewayDaemon — supervises all GURUJEE agents and routes messages."""
from __future__ import annotations

import asyncio
import logging
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

from gurujee.agents.base_agent import BaseAgent, Message, MessageBus, MessageType

if TYPE_CHECKING:
    from gurujee.keystore.keystore import Keystore

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    STARTING = auto()
    RUNNING = auto()
    STOPPED = auto()
    ERROR = auto()


class AgentState:
    """Runtime state of one agent, tracked by the daemon."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.status: AgentStatus = AgentStatus.STARTING
        self.task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
        self.restart_count: int = 0
        self.last_error: Optional[str] = None


class GatewayDaemon:
    """Starts, monitors, and routes messages for all GURUJEE agents."""

    def __init__(self, keystore: Optional[Keystore] = None) -> None:
        self._keystore = keystore
        self._bus = MessageBus()
        self._states: dict[str, AgentState] = {}
        self._shutdown_event = asyncio.Event()
        # Register the gateway's own inbox so agents can address "gateway".
        self._inbox: asyncio.Queue[Message] = asyncio.Queue()
        self._bus.register_agent("gateway", self._inbox)
        self._consumer_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
        self._ws_clients: set = set()  # WebSocket connections managed by server/websocket.py

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Start all agents and run until shutdown."""
        logger.info("GatewayDaemon: starting")
        self._consumer_task = asyncio.create_task(
            self._consume_inbox(), name="gateway:consumer"
        )
        await self._start_agents()
        await self._shutdown_event.wait()
        logger.info("GatewayDaemon: shutdown complete")

    @property
    def agent_states(self) -> dict[str, AgentState]:
        """Dict of agent_name → AgentState (read by /agents endpoint and conftest)."""
        return self._states

    @property
    def ready(self) -> bool:
        """True once all agents have been started (running, error, or stopped).

        An ERROR or STOPPED state still means the daemon started and is
        accepting API requests — only STARTING means "not yet ready".
        """
        if not self._states:
            return False
        return all(
            s.status in (AgentStatus.RUNNING, AgentStatus.ERROR, AgentStatus.STOPPED)
            for s in self._states.values()
        )

    @property
    def healthy(self) -> bool:
        """True only when every agent is currently RUNNING (no errors)."""
        if not self._states:
            return False
        return all(s.status == AgentStatus.RUNNING for s in self._states.values())

    @property
    def ws_clients(self) -> set:
        """Set of active WebSocket connections (populated by websocket handler)."""
        return self._ws_clients

    def get_agent_statuses(self) -> dict[str, str]:
        """Return {agent_name: status_name} for all registered agents."""
        return {name: state.status.name for name, state in self._states.items()}

    def shutdown(self, reason: str = "requested") -> None:
        """Signal all agents to stop and initiate graceful shutdown.

        Safe to call from synchronous contexts (e.g. Textual on_unmount).
        Uses call_soon_threadsafe when a running loop exists; falls back to
        setting the shutdown event directly so the start() wait unblocks.
        """
        logger.info("GatewayDaemon: shutdown requested (%s)", reason)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast_shutdown(reason))
        except RuntimeError:
            # No running loop (called from a non-async context) — set the
            # event directly so start() returns; agents will be GC'd.
            self._shutdown_event.set()

    # ------------------------------------------------------------------ #
    # Agent startup                                                         #
    # ------------------------------------------------------------------ #

    async def _start_agents(self) -> None:
        """Instantiate and start agents in startup order (P1–P5)."""
        from gurujee.agents.soul_agent import SoulAgent
        from gurujee.agents.memory_agent import MemoryAgent
        from gurujee.agents.heartbeat_agent import HeartbeatAgent
        from gurujee.agents.user_agent import UserAgent
        from gurujee.agents.cron_agent import CronAgent

        startup_order: list[tuple[str, type[BaseAgent]]] = [
            ("soul", SoulAgent),
            ("memory", MemoryAgent),
            ("heartbeat", HeartbeatAgent),
            ("user_agent", UserAgent),
            ("cron", CronAgent),
        ]

        for name, AgentClass in startup_order:
            state = AgentState(name)
            self._states[name] = state
            agent = AgentClass(name=name, bus=self._bus)
            task = asyncio.create_task(
                self._run_agent_with_supervision(agent, state),
                name=f"agent:{name}",
            )
            state.task = task
            state.status = AgentStatus.RUNNING
            logger.info("GatewayDaemon: started agent '%s'", name)
            await self._emit_status_update(name, AgentStatus.RUNNING)

    # ------------------------------------------------------------------ #
    # Supervision                                                           #
    # ------------------------------------------------------------------ #

    async def _run_agent_with_supervision(
        self, agent: BaseAgent, state: AgentState
    ) -> None:
        """Run agent.run(), catch exceptions, and update state accordingly."""
        try:
            await agent.run()
            state.status = AgentStatus.STOPPED
        except asyncio.CancelledError:
            state.status = AgentStatus.STOPPED
            raise
        except Exception as exc:
            state.status = AgentStatus.ERROR
            state.last_error = str(exc)
            logger.error("Agent '%s' crashed: %s", state.name, exc, exc_info=True)
            await self._emit_status_update(state.name, AgentStatus.ERROR, str(exc))

    async def _on_agent_failure(self, name: str) -> None:
        """Called by HeartbeatAgent when an agent misses a pong."""
        state = self._states.get(name)
        if state is None:
            return
        logger.warning("GatewayDaemon: restarting agent '%s'", name)
        if state.task and not state.task.done():
            state.task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(state.task), timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        state.restart_count += 1
        state.status = AgentStatus.STARTING
        await self._emit_status_update(name, AgentStatus.STARTING)
        # Re-import and re-instantiate the agent
        from gurujee.agents.soul_agent import SoulAgent
        from gurujee.agents.memory_agent import MemoryAgent
        from gurujee.agents.heartbeat_agent import HeartbeatAgent
        from gurujee.agents.user_agent import UserAgent
        from gurujee.agents.cron_agent import CronAgent

        class_map: dict[str, type[BaseAgent]] = {
            "soul": SoulAgent,
            "memory": MemoryAgent,
            "heartbeat": HeartbeatAgent,
            "user_agent": UserAgent,
            "cron": CronAgent,
        }
        AgentClass = class_map.get(name)
        if AgentClass is None:
            return
        agent = AgentClass(name=name, bus=self._bus)
        task = asyncio.create_task(
            self._run_agent_with_supervision(agent, state),
            name=f"agent:{name}",
        )
        state.task = task
        state.status = AgentStatus.RUNNING
        await self._emit_status_update(name, AgentStatus.RUNNING)

    # ------------------------------------------------------------------ #
    # Gateway inbox consumer                                                #
    # ------------------------------------------------------------------ #

    async def _consume_inbox(self) -> None:
        """Drain the gateway inbox and dispatch messages until shutdown."""
        while not self._shutdown_event.is_set():
            try:
                msg = await asyncio.wait_for(self._inbox.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            if msg.type == MessageType.AGENT_STATUS_UPDATE:
                agent_name = msg.payload.get("agent", "")
                reason = msg.payload.get("reason", "")
                if reason == "pong_timeout" and agent_name:
                    await self._on_agent_failure(agent_name)
            elif msg.type == MessageType.SHUTDOWN:
                break

    # ------------------------------------------------------------------ #
    # Messaging helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _emit_status_update(
        self,
        name: str,
        status: AgentStatus,
        error: Optional[str] = None,
    ) -> None:
        payload: dict = {"agent": name, "status": status.name}
        if error:
            payload["error"] = error
        await self._bus.send(
            Message(
                type=MessageType.AGENT_STATUS_UPDATE,
                from_agent="gateway",
                to_agent="broadcast",
                payload=payload,
            )
        )

    async def _broadcast_shutdown(self, reason: str) -> None:
        await self._bus.send(
            Message(
                type=MessageType.SHUTDOWN,
                from_agent="gateway",
                to_agent="broadcast",
                payload={"reason": reason},
            )
        )
        tasks = [
            state.task
            for state in self._states.values()
            if state.task and not state.task.done()
        ]
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=5.0)
            for task in pending:
                task.cancel()
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
        self._shutdown_event.set()
