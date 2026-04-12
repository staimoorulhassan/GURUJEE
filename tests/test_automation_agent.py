"""Tests for AutomationAgent (T055)."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gurujee.agents.base_agent import Message, MessageType
from gurujee.agents.automation_agent import AutomationAgent


def _make_agent(mock_bus, ltm=None):
    agent = AutomationAgent(name="automation", bus=mock_bus, long_term_memory=ltm)
    # Replace executor with a mock
    executor_mock = MagicMock()
    executor_mock.is_available = MagicMock(return_value=True)
    executor_mock.execute = AsyncMock(return_value=("ok", "", 0))
    agent._executor = executor_mock
    from gurujee.automation.tool_router import ToolRouter
    agent._router = ToolRouter(executor_mock)
    return agent


class TestDispatch:
    @pytest.mark.asyncio
    async def test_open_app_sends_automate_result(self, mock_bus):
        agent = _make_agent(mock_bus)

        tool_call = {"function": {"name": "open_app", "arguments": {"app_name": "whatsapp"}}}
        request_msg = Message(
            type=MessageType.AUTOMATE_REQUEST,
            from_agent="server",
            to_agent="automation",
            payload={"tool_call": tool_call, "input_text": "open whatsapp"},
            reply_to="server",
        )
        await agent._handle_automate_request(request_msg)

        result_msgs = mock_bus.messages_of_type(MessageType.AUTOMATE_RESULT)
        assert result_msgs, "Expected AUTOMATE_RESULT to be sent"
        payload = result_msgs[0].payload
        assert payload["command_type"] == "open_app"

    @pytest.mark.asyncio
    async def test_success_logged_to_ltm(self, mock_bus):
        ltm = MagicMock()
        agent = _make_agent(mock_bus, ltm=ltm)

        tool_call = {"function": {"name": "open_app", "arguments": {"app_name": "chrome"}}}
        msg = Message(
            type=MessageType.AUTOMATE_REQUEST,
            from_agent="server",
            to_agent="automation",
            payload={"tool_call": tool_call, "input_text": "open chrome"},
            reply_to="server",
        )
        await agent._handle_automate_request(msg)
        ltm.log_automation.assert_called_once()
        args = ltm.log_automation.call_args
        assert args.kwargs.get("status") == "success" or args[1].get("status") == "success"


class TestShizukuUnavailable:
    @pytest.mark.asyncio
    async def test_shizuku_unavailable_publishes_friendly_error(self, mock_bus):
        from gurujee.automation.executor import ShizukuUnavailableError

        agent = _make_agent(mock_bus)
        agent._executor.execute = AsyncMock(side_effect=ShizukuUnavailableError("not running"))
        from gurujee.automation.tool_router import ToolRouter
        agent._router = ToolRouter(agent._executor)

        tool_call = {"function": {"name": "open_app", "arguments": {"app_name": "whatsapp"}}}
        msg = Message(
            type=MessageType.AUTOMATE_REQUEST,
            from_agent="server",
            to_agent="automation",
            payload={"tool_call": tool_call, "input_text": "open whatsapp"},
            reply_to="server",
        )
        await agent._handle_automate_request(msg)

        results = mock_bus.messages_of_type(MessageType.AUTOMATE_RESULT)
        assert results
        assert results[0].payload["success"] is False
        assert results[0].payload["status"] == "unavailable"


class TestTimeout:
    @pytest.mark.asyncio
    async def test_timeout_logged(self, mock_bus):
        from gurujee.automation.executor import AutomationTimeoutError

        agent = _make_agent(mock_bus)
        agent._executor.execute = AsyncMock(
            side_effect=AutomationTimeoutError("timed out")
        )
        from gurujee.automation.tool_router import ToolRouter
        agent._router = ToolRouter(agent._executor)

        tool_call = {"function": {"name": "open_app", "arguments": {"app_name": "chrome"}}}
        msg = Message(
            type=MessageType.AUTOMATE_REQUEST,
            from_agent="server",
            to_agent="automation",
            payload={"tool_call": tool_call, "input_text": "open chrome"},
            reply_to="server",
        )
        ltm = MagicMock()
        agent._ltm = ltm
        await agent._handle_automate_request(msg)

        ltm.log_automation.assert_called_once()
        logged_status = ltm.log_automation.call_args[1].get("status") or \
                        ltm.log_automation.call_args[0][3]
        assert logged_status == "timeout"


class TestPruneOnStartup:
    def test_prune_called_on_startup(self, mock_bus):
        ltm = MagicMock()
        agent = AutomationAgent(name="automation", bus=mock_bus, long_term_memory=ltm)
        agent._prune_log_on_startup()
        ltm.prune_automation_log.assert_called_once_with(max_entries=500)
