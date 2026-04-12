"""Launcher bootstrap — installs Termux if needed and polls daemon readiness (T058)."""
from __future__ import annotations

import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Optional


_HEALTH_URL = "http://127.0.0.1:7171/health"
_TERMUX_PACKAGE = "com.termux"
_TERMUX_API_PACKAGE = "com.termux.api"
_GURUJEE_BOOTSTRAP_SCRIPT = "gurujee_bootstrap.sh"


def check_termux_installed() -> bool:
    try:
        result = subprocess.run(
            ["pm", "list", "packages", _TERMUX_PACKAGE],
            capture_output=True, text=True, timeout=5,
        )
        return _TERMUX_PACKAGE in result.stdout
    except Exception:
        return False


def install_termux(apk_path: Optional[str] = None) -> bool:
    """Install Termux from *apk_path* (bundled asset copied to /sdcard/DCIM/)."""
    if apk_path is None:
        apk_path = "/sdcard/DCIM/termux.apk"
    try:
        result = subprocess.run(
            ["pm", "install", "-r", apk_path],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_termux_api_installed() -> bool:
    try:
        result = subprocess.run(
            ["pm", "list", "packages", _TERMUX_API_PACKAGE],
            capture_output=True, text=True, timeout=5,
        )
        return _TERMUX_API_PACKAGE in result.stdout
    except Exception:
        return False


def install_termux_api(apk_path: Optional[str] = None) -> bool:
    if apk_path is None:
        apk_path = "/sdcard/DCIM/termux-api.apk"
    try:
        result = subprocess.run(
            ["pm", "install", "-r", apk_path],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False


def inject_bootstrap(script_path: str) -> bool:
    """Inject and run *script_path* inside Termux via am start."""
    try:
        result = subprocess.run(
            [
                "am", "start",
                "-n", f"{_TERMUX_PACKAGE}/.app.TermuxActivity",
                "--es", "com.termux.app.RUN_COMMAND_PATH", script_path,
                "--ez", "com.termux.app.RUN_COMMAND_SESSION_ACTION", "0",
            ],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def poll_daemon_ready(timeout_seconds: int = 180) -> bool:
    """Poll GET /health every 3 seconds until status=='ready' or timeout."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(_HEALTH_URL, timeout=3) as resp:
                import json
                data = json.loads(resp.read())
                if data.get("status") == "ready":
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False
