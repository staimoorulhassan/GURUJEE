"""Tests for HeartbeatAgent."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from gurujee.agents.base_agent import Message, MessageType
from tests.conftest import MockMessageBus


@pytest.fixture
def bus() -> MockMessageBus:
    return MockMessageBus()


@pytest.fixture
def heartbeat_agent(bus, tmp_path):
    from gurujee.agents.heartbeat_agent import HeartbeatAgent
    return HeartbeatAgent(name="heartbeat", bus=bus, log_path=tmp_path / "heartbeat.log")


class TestPingPong:
    @pytest.mark.asyncio
    async def test_heartbeat_ping_broadcast_sent(self, heartbeat_agent, bus) -> None:
        """HeartbeatAgent must broadcast HEARTBEAT_PING."""
        with patch("asyncio.sleep", new=AsyncMock(side_effect=asyncio.CancelledError)):
            task = asyncio.create_task(heartbeat_agent.run())
            try:
                await asyncio.wait_for(task, timeout=0.5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        pings = bus.messages_of_type(MessageType.HEARTBEAT_PING)
        assert len(pings) >= 1

    @pytest.mark.asyncio
    async def test_pong_removes_from_pending(self, heartbeat_agent, bus) -> None:
        """Receiving HEARTBEAT_PONG must remove the agent from pending set."""
        ping_id = "test-ping-123"
        heartbeat_agent._pending_pings[ping_id] = {"soul"}

        pong = Message(
            type=MessageType.HEARTBEAT_PONG,
            from_agent="soul",
            to_agent="heartbeat",
            payload={"ping_id": ping_id, "status": "ok"},
        )
        await heartbeat_agent._inbox.put(pong)
        task = asyncio.create_task(heartbeat_agent.run())
        await asyncio.sleep(0.1)
        task.cancel()

        assert ping_id not in heartbeat_agent._pending_pings

    @pytest.mark.asyncio
    async def test_missing_pong_triggers_status_error(self, heartbeat_agent, bus) -> None:
        """Agent that doesn't pong within timeout must get AGENT_STATUS_UPDATE ERROR."""
        heartbeat_agent._pending_pings["stale-ping"] = {"soul"}

        await heartbeat_agent._check_pending_pings("stale-ping")

        updates = bus.messages_of_type(MessageType.AGENT_STATUS_UPDATE)
        assert any(
            m.payload.get("status") == "ERROR" and m.payload.get("agent") == "soul"
            for m in updates
        )

    @pytest.mark.asyncio
    async def test_restart_count_increments(self, heartbeat_agent, bus) -> None:
        initial = heartbeat_agent._restart_counts.get("soul", 0)
        heartbeat_agent._pending_pings["p1"] = {"soul"}
        await heartbeat_agent._check_pending_pings("p1")
        assert heartbeat_agent._restart_counts.get("soul", 0) == initial + 1
