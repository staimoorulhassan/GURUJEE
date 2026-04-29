"""Tests for GatewayDaemon — agent supervision and message routing."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGatewayDaemonProperties:
    def test_ready_is_false_with_no_states(self) -> None:
        from gurujee.daemon.gateway_daemon import GatewayDaemon

        daemon = GatewayDaemon()
        assert daemon.ready is False

    def test_agent_states_empty_on_init(self) -> None:
        from gurujee.daemon.gateway_daemon import GatewayDaemon

        daemon = GatewayDaemon()
        assert daemon.agent_states == {}

    def test_ws_clients_empty_on_init(self) -> None:
        from gurujee.daemon.gateway_daemon import GatewayDaemon

        daemon = GatewayDaemon()
        assert isinstance(daemon.ws_clients, set)
        assert len(daemon.ws_clients) == 0

    def test_get_agent_statuses_empty_on_init(self) -> None:
        from gurujee.daemon.gateway_daemon import GatewayDaemon

        daemon = GatewayDaemon()
        assert daemon.get_agent_statuses() == {}

    def test_ready_true_when_all_agents_running(self) -> None:
        from gurujee.daemon.gateway_daemon import GatewayDaemon, AgentState, AgentStatus

        daemon = GatewayDaemon()
        for name in ("soul", "memory"):
            state = AgentState(name)
            state.status = AgentStatus.RUNNING
            daemon._states[name] = state

        assert daemon.ready is True

    def test_ready_false_when_any_agent_not_running(self) -> None:
        from gurujee.daemon.gateway_daemon import GatewayDaemon, AgentState, AgentStatus

        daemon = GatewayDaemon()
        s1 = AgentState("soul")
        s1.status = AgentStatus.RUNNING
        s2 = AgentState("memory")
        s2.status = AgentStatus.STARTING
        daemon._states["soul"] = s1
        daemon._states["memory"] = s2

        assert daemon.ready is False


class TestGatewayDaemonShutdown:
    def test_shutdown_from_sync_context_sets_event(self) -> None:
        """shutdown() called outside an event loop must set the shutdown event."""
        from gurujee.daemon.gateway_daemon import GatewayDaemon

        daemon = GatewayDaemon()
        daemon.shutdown("test")
        assert daemon._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_shutdown_from_async_context(self) -> None:
        from gurujee.daemon.gateway_daemon import GatewayDaemon

        daemon = GatewayDaemon()
        daemon.shutdown("async_test")
        # Give the created task a chance to run
        await asyncio.sleep(0.05)
        assert daemon._shutdown_event.is_set()


class TestGatewayDaemonEmitStatus:
    @pytest.mark.asyncio
    async def test_emit_status_update_sends_message(self) -> None:
        from gurujee.daemon.gateway_daemon import GatewayDaemon, AgentStatus
        from gurujee.agents.base_agent import MessageType

        daemon = GatewayDaemon()
        # Register a listener inbox for "broadcast" so send() doesn't block
        broadcast_q: asyncio.Queue = asyncio.Queue()
        daemon._bus.register_agent("broadcast", broadcast_q)

        await daemon._emit_status_update("soul", AgentStatus.RUNNING)

        msg = broadcast_q.get_nowait()
        assert msg.type == MessageType.AGENT_STATUS_UPDATE
        assert msg.payload["agent"] == "soul"
        assert msg.payload["status"] == "RUNNING"

    @pytest.mark.asyncio
    async def test_emit_status_update_includes_error(self) -> None:
        from gurujee.daemon.gateway_daemon import GatewayDaemon, AgentStatus

        daemon = GatewayDaemon()
        broadcast_q: asyncio.Queue = asyncio.Queue()
        daemon._bus.register_agent("broadcast", broadcast_q)

        await daemon._emit_status_update("memory", AgentStatus.ERROR, "oom")

        msg = broadcast_q.get_nowait()
        assert msg.payload["error"] == "oom"


class TestGatewayDaemonAgentState:
    def test_agent_state_initial_values(self) -> None:
        from gurujee.daemon.gateway_daemon import AgentState, AgentStatus

        state = AgentState("heartbeat")
        assert state.name == "heartbeat"
        assert state.status == AgentStatus.STARTING
        assert state.restart_count == 0
        assert state.last_error is None
        assert state.task is None
