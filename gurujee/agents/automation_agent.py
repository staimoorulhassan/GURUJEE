"""AutomationAgent — handles AUTOMATE_REQUEST messages via ToolRouter (T050)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

from gurujee.agents.base_agent import BaseAgent, Message, MessageBus, MessageType
from gurujee.automation.executor import (
    AutomationError,
    AutomationTimeoutError,
    ShizukuUnavailableError,
    ShizukuExecutor,
)
from gurujee.automation.tool_router import ToolRouter

logger = logging.getLogger(__name__)

_PRUNE_ON_STARTUP_MAX = 500


def _add_rotating_handler(log: logging.Logger, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        h = RotatingFileHandler(str(path), maxBytes=5_242_880, backupCount=3, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        log.addHandler(h)
    except OSError as exc:
        log.warning("Could not attach file handler at %s: %s", path, exc)


class AutomationAgent(BaseAgent):
    """Receives AUTOMATE_REQUEST, dispatches via ToolRouter, logs to automation_log."""

    def __init__(
        self,
        name: str,
        bus: MessageBus,
        long_term_memory: Optional[Any] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        super().__init__(name, bus)
        self._ltm = long_term_memory
        self._executor = ShizukuExecutor()
        self._router = ToolRouter(self._executor)
        _data = Path(data_dir) if data_dir else Path(os.environ.get("GURUJEE_DATA_DIR", "data"))
        _add_rotating_handler(logger, _data / "automation.log")

    # ------------------------------------------------------------------ #
    # Lifecycle                                                             #
    # ------------------------------------------------------------------ #

    async def run(self) -> None:
        """Prune log, then consume inbox until SHUTDOWN."""
        self._prune_log_on_startup()
        async for msg in self._iter_inbox():
            await self._dispatch(msg)

    async def handle_message(self, msg: Message) -> None:
        if msg.type == MessageType.AUTOMATE_REQUEST:
            await self._handle_automate_request(msg)
        elif msg.type == MessageType.SHUTDOWN:
            raise asyncio.CancelledError

    # ------------------------------------------------------------------ #
    # Request handler                                                       #
    # ------------------------------------------------------------------ #

    async def _handle_automate_request(self, msg: Message) -> None:
        tool_call: dict = msg.payload.get("tool_call", {})
        command_type: str = (
            tool_call.get("function", {}).get("name")
            or tool_call.get("name", "unknown")
        )
        input_text: str = msg.payload.get("input_text", json.dumps(tool_call))

        start = time.monotonic()
        status = "success"
        error_message: Optional[str] = None
        result_text = ""

        try:
            coro = self._router.route(tool_call)
            result_text = await coro
        except ShizukuUnavailableError as exc:
            status = "unavailable"
            error_message = str(exc)
            result_text = ShizukuUnavailableError.USER_MESSAGE
            logger.warning("Shizuku unavailable: %s", exc)
        except AutomationTimeoutError as exc:
            status = "timeout"
            error_message = str(exc)
            result_text = "Command timed out."
            logger.warning("Automation timeout: %s", exc)
        except AutomationError as exc:
            status = "failed"
            error_message = str(exc)
            result_text = f"Automation error: {exc}"
            logger.error("Automation error: %s", exc)
        except Exception as exc:
            status = "error"
            error_message = str(exc)
            result_text = f"Unexpected error: {exc}"
            logger.exception("Unexpected automation error")

        duration_ms = int((time.monotonic() - start) * 1000)

        # Log to SQLite
        if self._ltm:
            try:
                self._ltm.log_automation(
                    command_type=command_type,
                    input_text=input_text,
                    action_json=json.dumps(tool_call),
                    status=status,
                    error_message=error_message,
                    duration_ms=duration_ms,
                )
            except Exception as log_exc:
                logger.warning("Failed to log automation: %s", log_exc)

        # Reply
        reply_to = msg.reply_to or msg.from_agent
        await self.send(
            to=reply_to,
            msg_type=MessageType.AUTOMATE_RESULT,
            payload={
                "success": status == "success",
                "result": result_text,
                "command_type": command_type,
                "duration_ms": duration_ms,
                "status": status,
            },
            reply_to=msg.id,
        )

        # If Shizuku unavailable, also emit a ws-targeted event
        if status == "unavailable":
            await self.broadcast(
                MessageType.AGENT_STATUS_UPDATE,
                payload={
                    "type": "shizuku_unavailable",
                    "message": result_text,
                },
            )

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    def _prune_log_on_startup(self) -> None:
        if self._ltm and hasattr(self._ltm, "prune_automation_log"):
            try:
                self._ltm.prune_automation_log(max_entries=_PRUNE_ON_STARTUP_MAX)
            except Exception as exc:
                logger.warning("Failed to prune automation log: %s", exc)

    async def _iter_inbox(self):
        """Async generator over inbox messages until SHUTDOWN."""
        while True:
            try:
                msg = await asyncio.wait_for(self._inbox.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            if msg.type == MessageType.SHUTDOWN:
                return
            yield msg
