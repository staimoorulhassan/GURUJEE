"""Configuration loader for GURUJEE.

Handles PyYAML (machine-written files) and ruamel.yaml (soul_identity.yaml,
which must preserve user comments on round-trip writes).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from ruamel.yaml import YAML


_DEFAULT_USER_CONFIG: dict[str, Any] = {
    "active_model": "nova-fast",
    "active_voice_id": None,
    "tui_theme": "default",
}


class ConfigLoader:
    """Loads and saves GURUJEE configuration files."""

    # ------------------------------------------------------------------ #
    # Generic YAML (PyYAML — machine-written, comments not preserved)      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def load_yaml(path: Path) -> dict[str, Any]:
        """Load a YAML file with PyYAML safe_load.

        Returns an empty dict if the file does not exist.
        """
        resolved = ConfigLoader._resolve(path)
        if not resolved.exists():
            return {}
        with resolved.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}

    @staticmethod
    def save_yaml(data: dict[str, Any], path: Path) -> None:
        """Write *data* to *path* using PyYAML dump (overwrites)."""
        resolved = ConfigLoader._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with resolved.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, allow_unicode=True, default_flow_style=False)

    # ------------------------------------------------------------------ #
    # soul_identity.yaml (ruamel.yaml — preserves user comments)           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def load_soul_identity(path: Path) -> dict[str, Any]:
        """Load soul_identity.yaml preserving comments (ruamel.yaml round-trip)."""
        resolved = ConfigLoader._resolve(path)
        if not resolved.exists():
            return {}
        ry = YAML()
        with resolved.open("r", encoding="utf-8") as fh:
            data = ry.load(fh)
        return dict(data) if data is not None else {}

    @staticmethod
    def save_soul_identity(data: dict[str, Any], path: Path) -> None:
        """Write soul_identity.yaml preserving block-style and comments."""
        resolved = ConfigLoader._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        ry = YAML()
        ry.default_flow_style = False
        ry.preserve_quotes = True
        with resolved.open("w", encoding="utf-8") as fh:
            ry.dump(data, fh)

    # ------------------------------------------------------------------ #
    # Versioned config catalogues (config/ — version-controlled)           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def load_models(config_dir: Path | None = None) -> dict[str, Any]:
        """Load config/models.yaml (AI model catalogue + endpoint)."""
        base = Path(config_dir) if config_dir else Path("config")
        return ConfigLoader.load_yaml(base / "models.yaml")

    @staticmethod
    def load_agents(config_dir: Path | None = None) -> dict[str, Any]:
        """Load config/agents.yaml (heartbeat intervals, memory limits, logging)."""
        base = Path(config_dir) if config_dir else Path("config")
        return ConfigLoader.load_yaml(base / "agents.yaml")

    @staticmethod
    def load_voice(config_dir: Path | None = None) -> dict[str, Any]:
        """Load config/voice.yaml (voice provider config)."""
        base = Path(config_dir) if config_dir else Path("config")
        return ConfigLoader.load_yaml(base / "voice.yaml")

    @staticmethod
    def load_automation(config_dir: Path | None = None) -> dict[str, Any]:
        """Load config/automation.yaml (Shizuku path, action timeouts, app packages)."""
        base = Path(config_dir) if config_dir else Path("config")
        return ConfigLoader.load_yaml(base / "automation.yaml")

    # ------------------------------------------------------------------ #
    # setup_state.yaml (PyYAML — machine-written)                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def load_setup_state(path: Path) -> dict[str, Any]:
        """Load setup_state.yaml; returns empty dict if missing."""
        return ConfigLoader.load_yaml(path)

    @staticmethod
    def save_setup_state(data: dict[str, Any], path: Path) -> None:
        """Write setup_state.yaml atomically."""
        ConfigLoader.save_yaml(data, path)

    # ------------------------------------------------------------------ #
    # data/user_config.yaml (PyYAML — user runtime preferences)            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def load_user_config(path: Path) -> dict[str, Any]:
        """Load user_config.yaml, returning defaults for any missing keys."""
        on_disk = ConfigLoader.load_yaml(path)
        config = dict(_DEFAULT_USER_CONFIG)
        config.update({k: v for k, v in on_disk.items() if k in _DEFAULT_USER_CONFIG})
        return config

    @staticmethod
    def save_user_config(data: dict[str, Any], path: Path) -> None:
        """Write user_config.yaml, merging with existing values."""
        existing = ConfigLoader.load_user_config(path)
        existing.update(data)
        ConfigLoader.save_yaml(existing, path)

    @staticmethod
    def init_user_config(path: Path) -> None:
        """Write default user_config.yaml only if the file does not exist."""
        resolved = ConfigLoader._resolve(path)
        if not resolved.exists():
            ConfigLoader.save_yaml(dict(_DEFAULT_USER_CONFIG), resolved)

    # ------------------------------------------------------------------ #
    # data/gurujee.config.json (JSON — user-facing, manually editable)     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def load_json_config(path: Path) -> dict[str, Any]:
        """Load data/gurujee.config.json with defaults for missing keys."""
        from gurujee.config.json_config import load_json_config
        return load_json_config(path)

    @staticmethod
    def save_json_config(data: dict[str, Any], path: Path) -> None:
        """Write data/gurujee.config.json atomically."""
        from gurujee.config.json_config import save_json_config
        save_json_config(data, path)

    @staticmethod
    def load_merged_config(data_dir: Path) -> dict[str, Any]:
        """Return user_config.yaml merged with gurujee.config.json (JSON wins).

        Suitable for callers that need the richer JSON fields (alias,
        context_size, base_url) alongside the standard user_config keys.
        AIClient continues reading user_config.yaml directly — no change needed.
        """
        from gurujee.config.json_config import merge_yaml_and_json
        data_dir = Path(data_dir)
        yaml_cfg = ConfigLoader.load_user_config(data_dir / "user_config.yaml")
        json_cfg = ConfigLoader.load_json_config(data_dir / "gurujee.config.json")
        return merge_yaml_and_json(yaml_cfg, json_cfg)

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _resolve(path: Path) -> Path:
        """Apply GURUJEE_DATA_DIR / GURUJEE_CONFIG_DIR env overrides."""
        path = Path(path)
        data_dir = os.environ.get("GURUJEE_DATA_DIR")
        config_dir = os.environ.get("GURUJEE_CONFIG_DIR")
        parts = path.parts
        if data_dir and len(parts) >= 1 and parts[0] == "data":
            return Path(data_dir) / Path(*parts[1:])
        if config_dir and len(parts) >= 1 and parts[0] == "config":
            return Path(config_dir) / Path(*parts[1:])
        return path
