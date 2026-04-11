"""ChatScreen — live streaming chat interface."""
from __future__ import annotations

import logging
from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, RichLog, Footer, Header
from textual.message import Message as TextualMessage

from gurujee.agents.base_agent import MessageType
from gurujee.tui.theme import PRIMARY_AMBER, ACCENT_ORANGE, TEXT_DIM, TEXT_PRIMARY

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Custom Textual messages (posted by the gateway worker)               #
# ------------------------------------------------------------------ #


class ChatChunk(TextualMessage):
    """A streaming token has arrived from the AI."""

    def __init__(self, token: str, request_id: str) -> None:
        super().__init__()
        self.token = token
        self.request_id = request_id


class ChatError(TextualMessage):
    """AI call failed; may be retried automatically."""

    def __init__(self, error: str, queued: bool, request_id: str) -> None:
        super().__init__()
        self.error = error
        self.queued = queued
        self.request_id = request_id


class ChatResponseComplete(TextualMessage):
    """AI response finished (streaming ended or interrupted)."""

    def __init__(self, full_text: str, is_interrupted: bool, request_id: str) -> None:
        super().__init__()
        self.full_text = full_text
        self.is_interrupted = is_interrupted
        self.request_id = request_id


# ------------------------------------------------------------------ #
# Screen                                                                #
# ------------------------------------------------------------------ #


class ChatScreen(Screen):
    """Full-height chat screen with streaming token-by-token rendering."""

    BINDINGS = [
        ("ctrl+a", "app.push_screen('agents')", "Agents"),
        ("ctrl+s", "app.push_screen('settings')", "Settings"),
    ]

    CSS = f"""
    ChatScreen {{
        layout: vertical;
    }}
    #chat-log {{
        height: 1fr;
        border: none;
    }}
    #chat-input {{
        dock: bottom;
        height: 3;
        border: tall {PRIMARY_AMBER};
    }}
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._streaming_request_id: Optional[str] = None
        self._cursor_written: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="chat-log", auto_scroll=True, markup=True)
        yield Input(placeholder="Message GURUJEE…", id="chat-input")
        yield Footer()

    # ------------------------------------------------------------------ #
    # User input                                                            #
    # ------------------------------------------------------------------ #

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return

        # Clear the input field
        self.query_one("#chat-input", Input).clear()

        # Show user turn in the log
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold {TEXT_PRIMARY}]You:[/] {user_text}")

        # Forward to gateway via app message bus
        try:
            self.app.post_message_to_gateway(  # type: ignore[attr-defined]
                MessageType.CHAT_REQUEST,
                {"text": user_text},
            )
        except AttributeError:
            logger.warning("ChatScreen: app does not expose post_message_to_gateway")

    # ------------------------------------------------------------------ #
    # Streaming handlers                                                    #
    # ------------------------------------------------------------------ #

    def on_chat_chunk(self, event: ChatChunk) -> None:
        log = self.query_one("#chat-log", RichLog)

        if self._streaming_request_id != event.request_id:
            # New response starting — write opening label with cursor
            self._streaming_request_id = event.request_id
            self._cursor_written = True
            log.write(
                f"[bold {PRIMARY_AMBER}]GURUJEE:[/] "
                f"[bold {ACCENT_ORANGE}]●[/] {event.token}",
            )
        else:
            # Append token to last line in-place
            log.write(event.token, end="")  # type: ignore[call-arg]

    def on_chat_error(self, event: ChatError) -> None:
        log = self.query_one("#chat-log", RichLog)
        retry_hint = "  [italic](Will retry automatically)[/]" if event.queued else ""
        log.write(f"[bold red]Error:[/] {event.error}{retry_hint}")
        self._streaming_request_id = None
        self._cursor_written = False

    def on_chat_response_complete(self, event: ChatResponseComplete) -> None:
        log = self.query_one("#chat-log", RichLog)

        if event.is_interrupted:
            log.write(f" [{TEXT_DIM}][interrupted][/]", end="")  # type: ignore[call-arg]
            log.write("")  # newline to close the line

        # Remove the blinking cursor indicator (add blank line as separator)
        log.write("")
        self._streaming_request_id = None
        self._cursor_written = False
