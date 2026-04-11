"""SettingsScreen — identity, AI model, and Phase 2 stubs."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Label, Select

from gurujee.config.loader import ConfigLoader
from gurujee.tui.theme import PRIMARY_AMBER, TEXT_DIM

logger = logging.getLogger(__name__)


class SettingsScreen(Screen):
    """User-facing settings: identity, AI model selection, Phase 2 stubs."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    CSS = f"""
    SettingsScreen {{
        layout: vertical;
        padding: 1 2;
        overflow-y: auto;
    }}
    .settings-section-label {{
        color: {PRIMARY_AMBER};
        text-style: bold;
        padding: 1 0 0 0;
    }}
    .dim {{
        color: {TEXT_DIM};
    }}
    Input {{
        margin: 0 0 1 0;
    }}
    Select {{
        margin: 0 0 1 0;
    }}
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data_dir = Path(os.environ.get("GURUJEE_DATA_DIR", "data"))
        self._config_dir = Path(os.environ.get("GURUJEE_CONFIG_DIR", "config"))
        self._soul_path = self._data_dir / "soul_identity.yaml"
        self._user_config_path = self._data_dir / "user_config.yaml"
        self._models_config_path = self._config_dir / "models.yaml"

        self._soul: dict = {}
        self._available_models: list[str] = []
        self._active_model: str = "nova-fast"

    def on_mount(self) -> None:
        self._load_data()
        self._populate_widgets()

    def _load_data(self) -> None:
        try:
            if self._soul_path.exists():
                self._soul = ConfigLoader.load_soul_identity(self._soul_path)
        except Exception as exc:
            logger.error("SettingsScreen: failed to load soul identity: %s", exc)

        try:
            models_cfg = ConfigLoader.load_yaml(self._models_config_path)
            self._available_models = models_cfg.get("available", ["nova-fast"])
        except Exception as exc:
            logger.warning("SettingsScreen: failed to load models config: %s", exc)
            self._available_models = ["nova-fast"]

        try:
            user_cfg = ConfigLoader.load_user_config(self._user_config_path)
            self._active_model = user_cfg.get("active_model", "nova-fast")
        except Exception as exc:
            logger.warning("SettingsScreen: failed to load user config: %s", exc)

    def _populate_widgets(self) -> None:
        # Identity — pre-fill name input
        name_input = self.query_one("#identity-name", Input)
        name_input.value = str(self._soul.get("name", "GURUJEE"))

        # AI Model — populate select
        model_select = self.query_one("#ai-model-select", Select)
        options = [(m, m) for m in self._available_models]
        model_select.set_options(options)
        try:
            model_select.value = self._active_model
        except Exception:
            pass  # model not in list; leave default

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # ── Identity ──────────────────────────────────────────────────
        yield Label("Identity", classes="settings-section-label")
        yield Input(
            placeholder="GURUJEE",
            id="identity-name",
        )

        # ── AI Model ──────────────────────────────────────────────────
        yield Label("AI Model", classes="settings-section-label")
        yield Select(
            options=[("nova-fast", "nova-fast")],  # populated on_mount
            id="ai-model-select",
        )

        # ── Calls stub ────────────────────────────────────────────────
        yield Label("Calls", classes="settings-section-label")
        yield Label("Auto-Answer: Coming in Phase 2", classes="dim")

        # ── SMS stub ──────────────────────────────────────────────────
        yield Label("SMS", classes="settings-section-label")
        yield Label("SMS Auto-Reply: Coming in Phase 2", classes="dim")

        yield Footer()

    # ------------------------------------------------------------------ #
    # Widget event handlers                                                 #
    # ------------------------------------------------------------------ #

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "identity-name":
            self._save_soul_name(event.value.strip())

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "ai-model-select" and event.value:
            self._save_active_model(str(event.value))

    def _save_soul_name(self, name: str) -> None:
        if not name:
            return
        try:
            self._soul["name"] = name
            ConfigLoader.save_soul_identity(self._soul, self._soul_path)
            logger.info("SettingsScreen: soul name updated to %s", name)
        except Exception as exc:
            logger.error("SettingsScreen: failed to save soul identity: %s", exc)

    def _save_active_model(self, model: str) -> None:
        try:
            ConfigLoader.save_user_config({"active_model": model}, self._user_config_path)
            self._active_model = model
            logger.info("SettingsScreen: active model updated to %s", model)
        except Exception as exc:
            logger.error("SettingsScreen: failed to save user config: %s", exc)

    def action_back(self) -> None:
        self.app.pop_screen()
