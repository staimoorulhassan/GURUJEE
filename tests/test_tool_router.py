"""Tests for ToolRouter — maps AI tool calls to automation actions."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_executor(stdout: str = "ok", returncode: int = 0):
    executor = MagicMock()
    executor.execute = AsyncMock(return_value=(stdout, "", returncode))
    executor.is_available = MagicMock(return_value=True)
    return executor


class TestToolRouterRouting:
    def test_unknown_tool_raises_automation_error(self) -> None:
        from gurujee.automation.tool_router import ToolRouter
        from gurujee.automation.executor import AutomationError

        router = ToolRouter(_make_executor())
        with pytest.raises(AutomationError, match="Unknown tool"):
            router.route({"name": "non_existent_tool", "arguments": {}})

    def test_tools_list_has_five_entries(self) -> None:
        from gurujee.automation.tool_router import TOOLS
        assert len(TOOLS) == 5
        names = {t["function"]["name"] for t in TOOLS}
        assert names == {"open_app", "device_setting", "ui_input", "read_notifications", "set_reminder"}

    @pytest.mark.asyncio
    async def test_route_open_app(self) -> None:
        from gurujee.automation.tool_router import ToolRouter

        executor = _make_executor("Success")
        router = ToolRouter(executor)
        result = await router.route({
            "name": "open_app",
            "arguments": {"app_name": "calculator"},
        })
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_route_device_setting_volume(self) -> None:
        from gurujee.automation.tool_router import ToolRouter

        executor = _make_executor("ok")
        router = ToolRouter(executor)
        result = await router.route({
            "name": "device_setting",
            "arguments": {"setting": "volume", "value": 10},
        })
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_route_device_setting_wifi_on(self) -> None:
        from gurujee.automation.tool_router import ToolRouter

        executor = _make_executor("ok")
        router = ToolRouter(executor)
        result = await router.route({
            "name": "device_setting",
            "arguments": {"setting": "wifi", "value": True},
        })
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_route_device_setting_unknown_raises(self) -> None:
        from gurujee.automation.tool_router import ToolRouter
        from gurujee.automation.executor import AutomationError

        router = ToolRouter(_make_executor())
        with pytest.raises(AutomationError):
            await router.route({
                "name": "device_setting",
                "arguments": {"setting": "microwave", "value": 5},
            })

    @pytest.mark.asyncio
    async def test_route_ui_input_tap(self) -> None:
        from gurujee.automation.tool_router import ToolRouter

        executor = _make_executor("ok")
        router = ToolRouter(executor)
        result = await router.route({
            "name": "ui_input",
            "arguments": {"action": "tap", "x": 100, "y": 200},
        })
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_route_ui_input_press_back(self) -> None:
        from gurujee.automation.tool_router import ToolRouter

        executor = _make_executor("ok")
        router = ToolRouter(executor)
        result = await router.route({
            "name": "ui_input",
            "arguments": {"action": "press_back"},
        })
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_route_ui_input_unknown_action_raises(self) -> None:
        from gurujee.automation.tool_router import ToolRouter
        from gurujee.automation.executor import AutomationError

        router = ToolRouter(_make_executor())
        with pytest.raises(AutomationError):
            await router.route({
                "name": "ui_input",
                "arguments": {"action": "dance"},
            })

    @pytest.mark.asyncio
    async def test_route_read_notifications_empty(self) -> None:
        from gurujee.automation.tool_router import ToolRouter

        executor = _make_executor("[]")
        router = ToolRouter(executor)
        with patch("gurujee.automation.actions.notifications.list_notifications", new_callable=AsyncMock, return_value=[]):
            result = await router.route({
                "name": "read_notifications",
                "arguments": {},
            })
        assert "No notifications" in result

    @pytest.mark.asyncio
    async def test_route_set_reminder(self) -> None:
        from gurujee.automation.tool_router import ToolRouter

        executor = _make_executor("ok")
        router = ToolRouter(executor)
        result = await router.route({
            "name": "set_reminder",
            "arguments": {"time": "07:30", "label": "Wake up"},
        })
        assert "07:30" in result

    @pytest.mark.asyncio
    async def test_route_accepts_string_arguments(self) -> None:
        """Arguments may arrive as a JSON string from the AI stream."""
        import json
        from gurujee.automation.tool_router import ToolRouter

        executor = _make_executor("ok")
        router = ToolRouter(executor)
        result = await router.route({
            "function": {
                "name": "device_setting",
                "arguments": json.dumps({"setting": "bluetooth", "value": False}),
            }
        })
        assert isinstance(result, str)
