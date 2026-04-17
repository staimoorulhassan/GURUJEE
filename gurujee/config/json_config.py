"""JSON config I/O for data/gurujee.config.json.

This module provides the user-facing flat config file that mirrors key runtime
preferences from data/user_config.yaml in a format that is easy to hand-edit.

gurujee.config.json schema:
  {
    "model": {
      "provider":     str   (provider key, e.g. "openai", or "__custom__")
      "model_id":     str   (model id, e.g. "gpt-4o")
      "alias":        str | null
      "context_size": int
      "base_url":     str | null  (only set for custom/bring-your-own endpoints)
    },
    "ui": {
      "theme": str  (e.g. "dark")
    }
  }

Integration: OnboardWizard writes to this file AND to data/user_config.yaml
simultaneously so AIClient (which reads user_config.yaml) needs no changes.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_JSON_CONFIG: dict[str, Any] = {
    "model": {
        "provider": "pollinations",
        "model_id": "nova-fast",
        "alias": None,
        "context_size": 32000,
        "base_url": None,
    },
    "ui": {
        "theme": "dark",
    },
}


def load_json_config(path: Path) -> dict[str, Any]:
    """Load gurujee.config.json, returning defaults merged with on-disk data.

    - FileNotFoundError  → return a deep copy of _DEFAULT_JSON_CONFIG silently
    - JSONDecodeError    → log a warning, return defaults
    - Missing sub-keys   → filled in from defaults (shallow merge per section)
    """
    result = deepcopy(_DEFAULT_JSON_CONFIG)
    resolved = _resolve(path)
    if not resolved.exists():
        return result
    try:
        raw = resolved.read_text(encoding="utf-8")
        on_disk: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("gurujee.config.json is malformed (%s) — using defaults", exc)
        return result

    # Merge each top-level section, filling missing keys from defaults
    for section, defaults in _DEFAULT_JSON_CONFIG.items():
        if isinstance(defaults, dict):
            disk_section = on_disk.get(section, {})
            if not isinstance(disk_section, dict):
                disk_section = {}
            merged_section = dict(defaults)
            merged_section.update({k: v for k, v in disk_section.items() if k in defaults})
            result[section] = merged_section
        else:
            if section in on_disk:
                result[section] = on_disk[section]

    return result


def save_json_config(data: dict[str, Any], path: Path) -> None:
    """Write *data* to *path* as pretty-printed JSON (indent=2).

    Writes atomically: data is written to a temp file then renamed into place
    so a crash mid-write never produces a truncated config file.
    """
    resolved = _resolve(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    # Atomic write: temp file in same directory, then rename
    fd, tmp_path = tempfile.mkstemp(
        dir=resolved.parent, prefix=".gurujee_cfg_", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.write("\n")
        os.replace(tmp_path, resolved)
    except Exception:
        # Clean up the temp file if rename failed
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def merge_yaml_and_json(
    yaml_cfg: dict[str, Any],
    json_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Merge YAML user_config with JSON config. JSON values take priority.

    Maps json_cfg["model"]["provider"] + "/" + json_cfg["model"]["model_id"]
    into the unified ``active_model`` string (used by AIClient).

    Returns a new dict; neither input is mutated.
    """
    result = dict(yaml_cfg)

    model = json_cfg.get("model", {})
    provider = model.get("provider")
    model_id = model.get("model_id")
    if provider and model_id:
        result["active_model"] = f"{provider}/{model_id}"

    ui = json_cfg.get("ui", {})
    if ui.get("theme"):
        result["tui_theme"] = ui["theme"]

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve(path: Path) -> Path:
    """Apply GURUJEE_DATA_DIR env override for paths under data/."""
    path = Path(path)
    data_dir = os.environ.get("GURUJEE_DATA_DIR")
    if data_dir:
        parts = path.parts
        if len(parts) >= 1 and parts[0] == "data":
            return Path(data_dir) / Path(*parts[1:])
    return path
