"""Tests for ShizukuExecutor and system actions."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


class TestShizukuExecutorIsAvailable:
    def test_returns_false_when_rish_not_found(self, tmp_path: Path) -> None:
        from gurujee.automation.executor import ShizukuExecutor

        executor = ShizukuExecutor.__new__(ShizukuExecutor)
        executor._rish_path = str(tmp_path / "nonexistent_rish")
        executor._default_timeout = 10

        assert executor.is_available() is False

    def test_returns_false_when_rish_smoke_test_fails(self, tmp_path: Path) -> None:
        """rish binary exists but returns non-zero."""
        from gurujee.automation.executor import ShizukuExecutor
        import subprocess

        fake_rish = tmp_path / "rish"
        fake_rish.write_text("#!/bin/sh\nexit 1\n")
        fake_rish.chmod(0o755)

        executor = ShizukuExecutor.__new__(ShizukuExecutor)
        executor._rish_path = str(fake_rish)
        executor._default_timeout = 10

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            # rish file "exists" now — patch Path.exists to True
            with patch.object(Path, "exists", return_value=True):
                assert executor.is_available() is False

    def test_returns_false_when_subprocess_raises(self, tmp_path: Path) -> None:
        from gurujee.automation.executor import ShizukuExecutor

        executor = ShizukuExecutor.__new__(ShizukuExecutor)
        executor._rish_path = str(tmp_path / "rish")
        executor._default_timeout = 10

        with patch.object(Path, "exists", return_value=True):
            with patch("subprocess.run", side_effect=OSError("permission denied")):
                assert executor.is_available() is False


class TestShizukuExecutorExecute:
    @pytest.mark.asyncio
    async def test_raises_unavailable_when_rish_missing(self, tmp_path: Path) -> None:
        from gurujee.automation.executor import ShizukuExecutor, ShizukuUnavailableError

        executor = ShizukuExecutor.__new__(ShizukuExecutor)
        executor._rish_path = str(tmp_path / "not_here")
        executor._default_timeout = 10

        with pytest.raises(ShizukuUnavailableError):
            await executor.execute("echo hello")

    @pytest.mark.asyncio
    async def test_raises_timeout_error(self, tmp_path: Path) -> None:
        import asyncio
        from gurujee.automation.executor import ShizukuExecutor, AutomationTimeoutError

        executor = ShizukuExecutor.__new__(ShizukuExecutor)
        executor._rish_path = "/fake/rish"
        executor._default_timeout = 1

        mock_proc = AsyncMock()
        mock_proc.kill = MagicMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch.object(Path, "exists", return_value=True):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                with pytest.raises(AutomationTimeoutError):
                    await executor.execute("sleep 100", timeout=1)

    @pytest.mark.asyncio
    async def test_successful_execute_returns_tuple(self, tmp_path: Path) -> None:
        from gurujee.automation.executor import ShizukuExecutor

        executor = ShizukuExecutor.__new__(ShizukuExecutor)
        executor._rish_path = "/fake/rish"
        executor._default_timeout = 10

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"hello\n", b""))

        with patch.object(Path, "exists", return_value=True):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                stdout, stderr, rc = await executor.execute("echo hello")

        assert stdout == "hello"
        assert stderr == ""
        assert rc == 0


class TestSystemActions:
    @pytest.mark.asyncio
    async def test_take_screenshot_returns_path(self) -> None:
        from gurujee.automation.actions.system import take_screenshot

        executor = MagicMock()
        executor.execute = AsyncMock(return_value=("", "", 0))

        path = await take_screenshot(executor)
        assert "screenshot" in path or "png" in path
        executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_running_apps_returns_stdout(self) -> None:
        from gurujee.automation.actions.system import get_running_apps

        executor = MagicMock()
        executor.execute = AsyncMock(return_value=("com.example.app", "", 0))

        result = await get_running_apps(executor)
        assert result == "com.example.app"
