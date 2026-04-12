"""Tests for FastAPI server endpoints — T042."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from gurujee.agents.base_agent import Message, MessageBus, MessageType
from gurujee.server.app import create_app


# ------------------------------------------------------------------ #
# Helpers                                                               #
# ------------------------------------------------------------------ #

def _make_gateway(*, ready: bool = True) -> MagicMock:
    """Build a minimal GatewayDaemon mock."""
    gw = MagicMock()
    gw.ready = ready
    gw.ws_clients = set()

    from gurujee.daemon.gateway_daemon import AgentState, AgentStatus
    state = AgentState("soul")
    state.status = AgentStatus.RUNNING
    state.restart_count = 0
    state.last_error = None
    gw.agent_states = {"soul": state}

    # Provide a real MessageBus so /chat can publish
    bus = MessageBus()
    gw._bus = bus
    return gw


@pytest.fixture
def app(mock_bus):
    gw = _make_gateway()
    gw._bus = mock_bus
    return create_app(gw)


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as c:
        yield c


# ------------------------------------------------------------------ #
# Health                                                                #
# ------------------------------------------------------------------ #

class TestHealth:
    @pytest.mark.asyncio
    async def test_health_ready(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready"
        assert "agents" in body

    @pytest.mark.asyncio
    async def test_health_starting(self, mock_bus):
        gw = _make_gateway(ready=False)
        gw._bus = mock_bus
        app = create_app(gw)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as c:
            r = await c.get("/health")
        assert r.json()["status"] == "starting"


# ------------------------------------------------------------------ #
# Agents                                                                #
# ------------------------------------------------------------------ #

class TestAgents:
    @pytest.mark.asyncio
    async def test_agents_returns_list(self, client):
        r = await client.get("/agents")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        entry = data[0]
        assert "name" in entry
        assert "status" in entry
        assert "restart_count" in entry


# ------------------------------------------------------------------ #
# Chat SSE                                                              #
# ------------------------------------------------------------------ #

class TestChatStream:
    @pytest.mark.asyncio
    async def test_chat_streams_sse_format(self, app, mock_bus):
        """Inject CHAT_CHUNK + CHAT_RESPONSE_COMPLETE via the bus after /chat is called."""
        async def _inject_replies():
            await asyncio.sleep(0.05)
            # Find the ephemeral chat inbox
            for name, inbox in list(mock_bus._inboxes.items()):
                if name.startswith("chat:"):
                    await inbox.put(Message(
                        type=MessageType.CHAT_CHUNK,
                        from_agent="soul",
                        to_agent=name,
                        payload={"chunk": "Hello"},
                        reply_to=name,
                    ))
                    await inbox.put(Message(
                        type=MessageType.CHAT_RESPONSE_COMPLETE,
                        from_agent="soul",
                        to_agent=name,
                        payload={},
                        reply_to=name,
                    ))
                    return

        asyncio.create_task(_inject_replies())

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as c:
            async with c.stream("POST", "/chat", json={"message": "hi"}) as r:
                assert r.status_code == 200
                assert "text/event-stream" in r.headers["content-type"]
                lines = []
                async for line in r.aiter_lines():
                    lines.append(line)
                    if any('"done": true' in l or '"done":true' in l for l in lines):
                        break

        data_lines = [l for l in lines if l.startswith("data: ")]
        assert len(data_lines) >= 1

        # Check chunk format
        first = json.loads(data_lines[0][6:])
        assert "chunk" in first or "error" in first

    @pytest.mark.asyncio
    async def test_chat_error_event_format(self, app, mock_bus):
        """If agent sends CHAT_ERROR, response contains error field with done=true."""
        async def _inject_error():
            await asyncio.sleep(0.05)
            for name, inbox in list(mock_bus._inboxes.items()):
                if name.startswith("chat:"):
                    await inbox.put(Message(
                        type=MessageType.CHAT_ERROR,
                        from_agent="soul",
                        to_agent=name,
                        payload={"error": "agent unavailable"},
                        reply_to=name,
                    ))
                    return

        asyncio.create_task(_inject_error())

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as c:
            async with c.stream("POST", "/chat", json={"message": "hi"}) as r:
                lines = []
                async for line in r.aiter_lines():
                    lines.append(line)
                    if any('"done"' in l for l in lines):
                        break

        data_lines = [l for l in lines if l.startswith("data: ")]
        assert data_lines
        last = json.loads(data_lines[-1][6:])
        assert last.get("done") is True
