"""AgentStatusScreen — live view of all five agent states."""
from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.message import Message as TextualMessage
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label

from gurujee.tui.theme import PRIMARY_AMBER

logger = logging.getLogger(__name__)

# Ordered list of agents displayed in the table
_AGENT_NAMES: tuple[str, ...] = ("soul", "memory", "heartbeat", "user_agent", "cron")


# ------------------------------------------------------------------ #
# Custom Textual message                                                #
# ------------------------------------------------------------------ #


class AgentStatusUpdate(TextualMessage):
    """An agent's status has changed."""

    def __init__(self, agent: str, status: str, restarts: int = 0, error: str = "") -> None:
        super().__init__()
        self.agent = agent
        self.status = status
        self.restarts = restarts
        self.error = error


# ------------------------------------------------------------------ #
# Screen                                                                #
# ------------------------------------------------------------------ #


class AgentStatusScreen(Screen):
    """Displays a live-updating table of agent statuses."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    CSS = f"""
    AgentStatusScreen {{
        layout: vertical;
        align: center top;
        padding: 1 2;
    }}
    #status-title {{
        color: {PRIMARY_AMBER};
        text-style: bold;
        padding: 0 0 1 0;
    }}
    #agent-table {{
        width: 100%;
        height: auto;
    }}
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label("Agent Status", id="status-title")
        yield DataTable(id="agent-table", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#agent-table", DataTable)
        table.add_columns("Name", "Status", "Restarts", "Last Error")
        for agent_name in _AGENT_NAMES:
            table.add_row(agent_name, "STARTING", "0", "", key=agent_name)

    # ------------------------------------------------------------------ #
    # Status update handler                                                 #
    # ------------------------------------------------------------------ #

    def on_agent_status_update(self, event: AgentStatusUpdate) -> None:
        table = self.query_one("#agent-table", DataTable)
        try:
            table.update_cell(event.agent, "Status", event.status, update_width=True)
            table.update_cell(event.agent, "Restarts", str(event.restarts), update_width=True)
            table.update_cell(event.agent, "Last Error", event.error, update_width=True)
            # Flash the row in PRIMARY_AMBER to indicate a state change
            # (Textual doesn't have a built-in flash; we rely on CSS highlighting)
            logger.debug(
                "AgentStatusScreen: %s → %s (restarts=%d)",
                event.agent, event.status, event.restarts,
            )
        except Exception as exc:
            logger.warning("AgentStatusScreen: could not update row for %s: %s", event.agent, exc)

    def action_back(self) -> None:
        self.app.pop_screen()
