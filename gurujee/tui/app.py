"""GurujeeApp — top-level Textual application."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding

from gurujee.agents.base_agent import MessageType
from gurujee.tui.screens.agent_status_screen import AgentStatusScreen, AgentStatusUpdate
from gurujee.tui.screens.chat_screen import (
    ChatChunk,
    ChatError,
    ChatResponseComplete,
    ChatScreen,
)
from gurujee.tui.screens.settings_screen import SettingsScreen
from gurujee.tui.theme import GURUJEE_CSS

logger = logging.getLogger(__name__)


class GurujeeApp(App):
    """Main Textual application — wraps GatewayDaemon as a background worker."""

    CSS = GURUJEE_CSS

    SCREENS = {
        "chat": ChatScreen,
        "agents": AgentStatusScreen,
        "settings": SettingsScreen,
    }

    BINDINGS = [
        Binding("a", "push_screen('agents')", "Agents", show=True),
        Binding("s", "push_screen('settings')", "Settings", show=True),
        Binding("escape", "pop_screen", "Back", show=False),
        Binding("ctrl+c", "quit", "Quit", show=True),
    ]

    def __init__(self, keystore=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._keystore = keystore
        self._daemon = None

    # ------------------------------------------------------------------ #
    # Lifecycle                                                             #
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        # Screens are pushed imperatively; nothing to yield at root
        return iter([])

    def on_mount(self) -> None:
        self.push_screen("chat")
        self.run_worker(self._start_daemon, thread=False, exclusive=True)

    # ------------------------------------------------------------------ #
    # Daemon worker                                                         #
    # ------------------------------------------------------------------ #

    async def _start_daemon(self) -> None:
        """Start GatewayDaemon and forward agent events to the TUI."""
        from gurujee.daemon.gateway_daemon import GatewayDaemon

        self._daemon = GatewayDaemon(keystore=self._keystore)
        try:
            await self._daemon.start()
        except Exception as exc:
            logger.error("GurujeeApp: daemon exited with error: %s", exc)
            self.notify(f"Daemon error: {exc}", severity="error")

    # ------------------------------------------------------------------ #
    # Gateway message bridge                                                #
    # ------------------------------------------------------------------ #

    def post_message_to_gateway(self, msg_type: MessageType, payload: dict) -> None:
        """Send a message to the gateway daemon from the UI."""
        if self._daemon is None:
            logger.warning("GurujeeApp: daemon not ready, dropping message type=%s", msg_type)
            return
        asyncio.create_task(
            self._daemon._bus.send(
                self._daemon._bus._build_message(  # type: ignore[attr-defined]
                    msg_type=msg_type,
                    from_agent="tui",
                    to_agent="soul",
                    payload=payload,
                )
            )
        )

    # ------------------------------------------------------------------ #
    # Agent status forwarding                                               #
    # ------------------------------------------------------------------ #

    def notify_agent_status(
        self,
        agent: str,
        status: str,
        restarts: int = 0,
        error: str = "",
    ) -> None:
        """Forward a daemon agent-status change into the TUI event system."""
        try:
            self.post_message(AgentStatusUpdate(agent, status, restarts, error))
        except Exception as exc:
            logger.warning("GurujeeApp: could not forward agent status: %s", exc)

    # ------------------------------------------------------------------ #
    # Streaming event forwarding                                            #
    # ------------------------------------------------------------------ #

    def forward_chat_chunk(self, token: str, request_id: str) -> None:
        self.post_message(ChatChunk(token, request_id))

    def forward_chat_error(self, error: str, queued: bool, request_id: str) -> None:
        self.post_message(ChatError(error, queued, request_id))

    def forward_chat_response_complete(
        self, full_text: str, is_interrupted: bool, request_id: str
    ) -> None:
        self.post_message(ChatResponseComplete(full_text, is_interrupted, request_id))

    # ------------------------------------------------------------------ #
    # Exception handling                                                    #
    # ------------------------------------------------------------------ #

    def handle_exception(self, exc: Exception) -> None:
        """Log errors without re-raising (TUI crash must not kill the daemon)."""
        logger.error("GurujeeApp unhandled exception: %s", exc, exc_info=True)
        try:
            self.notify(str(exc), severity="error")
        except Exception:
            pass  # if notify itself fails, swallow silently

    # ------------------------------------------------------------------ #
    # Cleanup                                                               #
    # ------------------------------------------------------------------ #

    async def on_unmount(self) -> None:
        if self._daemon is not None:
            self._daemon.shutdown("tui_exit")
