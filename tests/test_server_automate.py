"""Tests for /automate and /notifications server endpoints (T057)."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import httpx
import pytest

from gurujee.agents.base_agent import Message, MessageBus, MessageType
from gurujee.daemon.gateway_daemon import AgentState, AgentStatus
from gurujee.server.app import create_app


def _make_gateway(mock_bus):
    gw = MagicMock()
    gw.ready = True
    gw.ws_clients = set()

    state = AgentState("automation")
    state.status = AgentStatus.RUNNING
    state.restart_count = 0
    state.last_error = None
    gw.agent_states = {"automation": state}
    gw._bus = mock_bus
    gw._ltm = None
    return gw


@pytest.fixture
def app(mock_bus):
    gw = _make_gateway(mock_bus)
    return create_app(gw), mock_bus


@pytest.fixture
async def client(app):
    a, bus = app
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=a),
        base_url="http://testserver",
    ) as c:
        yield c, bus, a


class TestAutomate:
    @pytest.mark.asyncio
    async def test_success_response_format(self, app):
        a, mock_bus = app

        async def _inject_result():
            await asyncio.sleep(0.05)
            for name, inbox in list(mock_bus._inboxes.items()):
                if name.startswith("automate:"):
                    await inbox.put(Message(
                        type=MessageType.AUTOMATE_RESULT,
                        from_agent="automation",
                        to_agent=name,
                        payload={
                            "success": True,
                            "result": "WhatsApp launched",
                            "command_type": "open_app",
                            "duration_ms": 250,
                            "status": "success",
                        },
                        reply_to=name,
                    ))
                    return

        asyncio.create_task(_inject_result())

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=a),
            base_url="http://testserver",
        ) as c:
            r = await c.post("/automate", json={"command": "open WhatsApp"})

        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "command_type" in body
        assert "duration_ms" in body

    @pytest.mark.asyncio
    async def test_timeout_returns_504(self, app):
        a, mock_bus = app
        # Don't inject any reply — let it time out
        # Patch the timeout to 0.01s so the test doesn't wait 15s
        import gurujee.server.routers.automate as automate_mod
        original = automate_mod._REPLY_TIMEOUT
        automate_mod._REPLY_TIMEOUT = 0.05
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=a),
                base_url="http://testserver",
            ) as c:
                r = await c.post("/automate", json={"command": "open chrome"})
            assert r.status_code == 504
        finally:
            automate_mod._REPLY_TIMEOUT = original


class TestNotifications:
    @pytest.mark.asyncio
    async def test_get_notifications_returns_list(self, app):
        a, _ = app
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=a),
            base_url="http://testserver",
        ) as c:
            r = await c.get("/notifications")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
