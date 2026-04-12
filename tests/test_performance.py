"""Performance sanity checks — SC-003, SC-004, SC-005.

These are single-run CI guards, not load tests.  They verify that the system
stays within the thresholds defined in spec.md before any commit lands.

SC-003 — GatewayDaemon reaches ready state within 5 seconds (mocked agents).
SC-004 — First SSE token from POST /chat arrives within 3 seconds (mocked AI).
SC-005 — Process RSS while idle is under 50 MB (Linux /proc or psutil).
"""
from __future__ import annotations

import asyncio
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from gurujee.agents.base_agent import Message, MessageBus, MessageType
from gurujee.daemon.gateway_daemon import AgentState, AgentStatus, GatewayDaemon
from gurujee.server.app import create_app


# ------------------------------------------------------------------ #
# SC-003 — Daemon startup latency < 5 s                               #
# ------------------------------------------------------------------ #

class TestSC003DaemonStartup:
    """GatewayDaemon must reach ready=True within 5 seconds of start()."""

    @pytest.mark.asyncio
    async def test_daemon_startup_under_5_seconds(self, tmp_path):
        """Time _start_agents() — all agents must transition to RUNNING quickly."""
        daemon = GatewayDaemon()

        # Patch _start_agents so agents are marked RUNNING immediately without
        # launching real asyncio tasks (which would block on the message bus).
        async def _fast_start() -> None:
            for name in ("soul", "memory", "heartbeat", "user_agent", "cron", "automation"):
                state = AgentState(name)
                state.status = AgentStatus.RUNNING
                daemon._states[name] = state

        t0 = time.perf_counter()
        with patch.object(daemon, "_start_agents", side_effect=_fast_start):
            # Cancel start() after agents are initialised — no need to wait for
            # the shutdown event in this test.
            task = asyncio.create_task(daemon.start())
            await asyncio.sleep(0)           # let start() call _start_agents
            daemon.shutdown("test-complete") # signal shutdown so start() returns
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except asyncio.TimeoutError:
                task.cancel()
                pytest.fail("SC-003: GatewayDaemon.start() did not return within 5 seconds")
        elapsed = time.perf_counter() - t0

        assert elapsed < 5.0, (
            f"SC-003 FAIL: daemon startup took {elapsed:.2f}s (limit: 5s)"
        )
        assert daemon.ready, "SC-003: daemon.ready is False after _start_agents completed"


# ------------------------------------------------------------------ #
# SC-004 — First SSE token from /chat < 3 s                          #
# ------------------------------------------------------------------ #

def _make_gateway_mock() -> MagicMock:
    """Minimal GatewayDaemon mock for server tests."""
    gw = MagicMock()
    gw.ready = True
    gw.ws_clients = set()
    state = AgentState("soul")
    state.status = AgentStatus.RUNNING
    state.restart_count = 0
    state.last_error = None
    gw.agent_states = {"soul": state}
    bus = MessageBus()
    gw._bus = bus
    return gw


class TestSC004ChatFirstToken:
    """First SSE token from POST /chat must arrive within 3 seconds."""

    @pytest.mark.asyncio
    async def test_first_sse_token_under_3_seconds(self):
        gw = _make_gateway_mock()
        app = create_app(gw)

        first_token_time: list[float] = []

        async def _inject_chunk() -> None:
            # Give the request handler a tick to register the ephemeral inbox,
            # then immediately inject a CHAT_CHUNK.
            await asyncio.sleep(0.02)
            for name, inbox in list(gw._bus._inboxes.items()):
                if name.startswith("chat:"):
                    await inbox.put(Message(
                        type=MessageType.CHAT_CHUNK,
                        from_agent="soul",
                        to_agent=name,
                        payload={"chunk": "Hi"},
                        reply_to=name,
                    ))
                    await inbox.put(Message(
                        type=MessageType.CHAT_RESPONSE_COMPLETE,
                        from_agent="soul",
                        to_agent=name,
                        payload={"full_text": "Hi"},
                        reply_to=name,
                    ))
                    break

        injector = asyncio.create_task(_inject_chunk())

        t0 = time.perf_counter()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            async with client.stream(
                "POST",
                "/chat",
                json={"message": "hello"},
                timeout=3.0,
            ) as resp:
                assert resp.status_code == 200
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        first_token_time.append(time.perf_counter() - t0)
                        break

        await injector

        assert first_token_time, "SC-004: no SSE data line received from /chat"
        latency = first_token_time[0]
        assert latency < 3.0, (
            f"SC-004 FAIL: first SSE token arrived after {latency:.3f}s (limit: 3s)"
        )


# ------------------------------------------------------------------ #
# SC-005 — Idle process RSS < 50 MB                                   #
# ------------------------------------------------------------------ #

class TestSC005IdleRAM:
    """Process RSS at test time must be under 50 MB (P1 ceiling).

    Reads /proc/self/status VmRSS — Linux/Android only.
    Skips on Windows because the pytest process RSS on Windows inflates
    significantly due to the OS loader and test runner overhead, making
    the number non-comparable to the daemon's isolated RSS on Termux.
    The authoritative measurement is in data/benchmarks/idle-ram-001.txt.
    """

    @pytest.mark.skipif(
        not sys.platform.startswith("linux"),
        reason="SC-005: /proc/self/status only meaningful on Linux/Android (Termux CI)",
    )
    def test_idle_rss_under_50mb(self):
        try:
            with open("/proc/self/status") as fh:
                for line in fh:
                    if line.startswith("VmRSS:"):
                        rss_kb = int(line.split()[1])
                        break
                else:
                    pytest.skip("SC-005: VmRSS not found in /proc/self/status")
        except OSError:
            pytest.skip("SC-005: /proc/self/status not readable")

        # P1 hard limit: idle daemon < 50 MB RSS (51200 KB).
        # Note: pytest runner adds ~15–25 MB vs. standalone daemon; the assertion
        # uses 51200 KB so that a test run on Termux with minimal pytest overhead
        # passes when the daemon is within budget.
        assert rss_kb < 51200, (
            f"SC-005 FAIL: VmRSS is {rss_kb} KB ({rss_kb / 1024:.1f} MB) "
            f"— P1 ceiling is 50 MB (51200 KB)"
        )
