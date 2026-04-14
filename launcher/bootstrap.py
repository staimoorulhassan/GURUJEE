"""Launcher bootstrap helpers (T058 / T059 redesign).

Provides only what the 4-screen onboarding flow actually needs:
  - check_termux_installed()  — PackageManager API; pm-shell fallback
  - open_termux()             — launch Termux via Intent
  - open_url(url)             — open URL in system browser via ACTION_VIEW
  - copy_to_clipboard(text)   — copy text using Android ClipboardManager
  - poll_daemon_ready(...)    — GET /health every 3 s with tick_cb
"""
from __future__ import annotations

import subprocess
import time
import urllib.request
from typing import Callable, Optional


_HEALTH_URL = "http://127.0.0.1:7171/health"
_TERMUX_PACKAGE = "com.termux"


# ---------------------------------------------------------------------------
# Package detection — use PackageManager API; fall back to pm shell command
# ---------------------------------------------------------------------------

def _pkg_installed_jnius(package: str) -> Optional[bool]:
    """Return True/False via Android PackageManager, or None if jnius unavailable."""
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        pm = PythonActivity.mActivity.getPackageManager()
        try:
            pm.getPackageInfo(package, 0)
            return True
        except Exception:
            return False
    except Exception:
        return None


def _pkg_installed_pm(package: str) -> bool:
    """Fallback: call /system/bin/pm directly."""
    try:
        result = subprocess.run(
            ["/system/bin/pm", "list", "packages", package],
            capture_output=True, text=True, timeout=5,
        )
        return package in result.stdout
    except Exception:
        return False


def check_termux_installed() -> bool:
    result = _pkg_installed_jnius(_TERMUX_PACKAGE)
    if result is not None:
        return result
    return _pkg_installed_pm(_TERMUX_PACKAGE)


# ---------------------------------------------------------------------------
# Open Termux
# ---------------------------------------------------------------------------

def open_termux() -> bool:
    """Launch Termux via Intent so the user can interact with it."""
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        activity = PythonActivity.mActivity
        intent = Intent()
        intent.setClassName(_TERMUX_PACKAGE, f"{_TERMUX_PACKAGE}.app.TermuxActivity")
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        activity.startActivity(intent)
        return True
    except Exception:
        pass
    try:
        subprocess.run(
            ["am", "start", "-n", f"{_TERMUX_PACKAGE}/.app.TermuxActivity"],
            timeout=5,
        )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Open URL in system browser
# ---------------------------------------------------------------------------

def open_url(url: str) -> bool:
    """Open *url* in the device's default browser via ACTION_VIEW Intent."""
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        activity = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        activity.startActivity(intent)
        return True
    except Exception:
        pass
    try:
        subprocess.run(["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
                       timeout=5)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Copy to clipboard
# ---------------------------------------------------------------------------

def copy_to_clipboard(text: str) -> bool:
    """Copy *text* to Android ClipboardManager (must run on UI thread)."""
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        from kivy.clock import Clock  # type: ignore[import-untyped]

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        ClipboardManager = autoclass("android.content.ClipboardManager")
        ClipData = autoclass("android.content.ClipData")
        activity = PythonActivity.mActivity

        def _copy(_dt: float) -> None:
            cm = activity.getSystemService(ClipboardManager.CLIPBOARD_SERVICE)
            clip = ClipData.newPlainText("GURUJEE", text)
            cm.setPrimaryClip(clip)

        Clock.schedule_once(_copy, 0)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Daemon readiness
# ---------------------------------------------------------------------------

def poll_daemon_ready(
    timeout_seconds: int = 60,
    tick_cb: Optional[Callable[[int, int], None]] = None,
) -> bool:
    """Poll GET /health every 3 s until status=='ready' or timeout.

    *tick_cb(elapsed, remaining)* is called each tick for UI updates.
    """
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
        elapsed = timeout_seconds - int(deadline - time.time())
        remaining = max(0, int(deadline - time.time()))
        if tick_cb:
            tick_cb(elapsed, remaining)
        time.sleep(3)
    return False
