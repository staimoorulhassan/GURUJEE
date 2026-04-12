"""Shizuku rish executor — runs shell commands via the Shizuku privileged API (T043)."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from gurujee.config.loader import ConfigLoader

logger = logging.getLogger(__name__)


class AutomationError(Exception):
    """Base class for automation errors."""


class ShizukuUnavailableError(AutomationError):
    """Raised when Shizuku / rish is not available."""

    USER_MESSAGE = (
        "Shizuku is not active. To re-activate:\n"
        "1. Open the Shizuku app.\n"
        "2. Tap 'Pairing (wireless debugging)'.\n"
        "3. Follow the on-screen instructions.\n"
        "4. Try your command again."
    )


class AutomationTimeoutError(AutomationError):
    """Raised when a command exceeds its timeout."""


class ShizukuExecutor:
    """Runs commands via `rish -c '<cmd>'` under the Shizuku privileged shell."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        cfg = ConfigLoader.load_automation(config_dir)
        self._rish_path: str = cfg.get(
            "shizuku_rish_path",
            "/data/user/0/moe.shizuku.privileged.api/rish",
        )
        self._default_timeout: int = int(cfg.get("action_timeout_seconds", 10))

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    def is_available(self) -> bool:
        """Return True if rish binary exists and appears runnable."""
        if not Path(self._rish_path).exists():
            return False
        # Quick smoke-test: run 'echo ok' with a 2s timeout
        try:
            import subprocess
            result = subprocess.run(
                [self._rish_path, "-c", "echo ok"],
                capture_output=True,
                timeout=2,
            )
            return result.returncode == 0
        except Exception:
            return False

    async def execute(
        self,
        cmd: str,
        timeout: Optional[int] = None,
    ) -> tuple[str, str, int]:
        """Run *cmd* via rish and return (stdout, stderr, returncode).

        Raises ShizukuUnavailableError if rish is not present.
        Raises AutomationTimeoutError if the command exceeds the timeout.
        """
        if not Path(self._rish_path).exists():
            raise ShizukuUnavailableError(ShizukuUnavailableError.USER_MESSAGE)

        effective_timeout = timeout if timeout is not None else self._default_timeout

        try:
            proc = await asyncio.create_subprocess_exec(
                self._rish_path, "-c", cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), timeout=effective_timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise AutomationTimeoutError(
                    f"Command timed out after {effective_timeout}s: {cmd}"
                )

            stdout = stdout_b.decode("utf-8", errors="replace").strip()
            stderr = stderr_b.decode("utf-8", errors="replace").strip()
            return stdout, stderr, proc.returncode or 0
        except (ShizukuUnavailableError, AutomationTimeoutError):
            raise
        except Exception as exc:
            raise ShizukuUnavailableError(
                f"Failed to run rish: {exc}\n{ShizukuUnavailableError.USER_MESSAGE}"
            ) from exc
