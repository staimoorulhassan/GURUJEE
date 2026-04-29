"""Tests for automation action modules (T056)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from gurujee.automation.actions.apps import open_app, resolve_package
from gurujee.automation.actions.device import set_volume, set_wifi
from gurujee.automation.actions.input import tap, swipe, type_text, press_back


def _mock_executor(stdout="ok", returncode=0):
    ex = MagicMock()
    ex.execute = AsyncMock(return_value=(stdout, "", returncode))
    return ex


class TestResolvePackage:
    def test_whatsapp_mapped(self):
        assert resolve_package("WhatsApp") == "com.whatsapp"

    def test_unknown_returned_as_is(self):
        assert resolve_package("com.custom.app") == "com.custom.app"


class TestOpenApp:
    @pytest.mark.asyncio
    async def test_open_app_uses_am_start(self):
        ex = _mock_executor("Activity started")
        result = await open_app(ex, "com.whatsapp")
        ex.execute.assert_called_once()
        cmd = ex.execute.call_args[0][0]
        assert "am start" in cmd
        assert "com.whatsapp" in cmd

    @pytest.mark.asyncio
    async def test_open_app_fallback_on_failure(self):
        # First call fails (rc=1), second succeeds
        ex = MagicMock()
        ex.execute = AsyncMock(side_effect=[("", "error", 1), ("ok", "", 0)])
        await open_app(ex, "com.example.app")
        assert ex.execute.call_count == 2
        fallback_cmd = ex.execute.call_args_list[1][0][0]
        assert "MainActivity" in fallback_cmd


class TestDeviceActions:
    @pytest.mark.asyncio
    async def test_set_volume_correct_command(self):
        ex = _mock_executor()
        await set_volume(ex, 10)
        cmd = ex.execute.call_args[0][0]
        assert "media volume" in cmd
        assert "10" in cmd

    @pytest.mark.asyncio
    async def test_set_wifi_enable(self):
        ex = _mock_executor()
        await set_wifi(ex, True)
        cmd = ex.execute.call_args[0][0]
        assert "svc wifi enable" in cmd

    @pytest.mark.asyncio
    async def test_set_wifi_disable(self):
        ex = _mock_executor()
        await set_wifi(ex, False)
        cmd = ex.execute.call_args[0][0]
        assert "svc wifi disable" in cmd


class TestInputActions:
    @pytest.mark.asyncio
    async def test_tap_coordinates(self):
        ex = _mock_executor()
        await tap(ex, 100, 200)
        cmd = ex.execute.call_args[0][0]
        assert "input tap 100 200" in cmd

    @pytest.mark.asyncio
    async def test_swipe_command(self):
        ex = _mock_executor()
        await swipe(ex, 0, 500, 0, 100, duration_ms=200)
        cmd = ex.execute.call_args[0][0]
        assert "input swipe 0 500 0 100 200" in cmd

    @pytest.mark.asyncio
    async def test_press_back_sends_keyevent_4(self):
        ex = _mock_executor()
        await press_back(ex)
        cmd = ex.execute.call_args[0][0]
        assert "keyevent 4" in cmd
