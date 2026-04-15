"""Launcher bootstrap helpers (T058 / T059 redesign).

Provides only what the 4-screen onboarding flow actually needs:
  - check_termux_installed()       — PackageManager API; pm-shell fallback
  - open_termux()                  — launch Termux via Intent
  - open_url(url)                  — open URL in system browser via ACTION_VIEW
  - copy_to_clipboard(text)        — copy text using Android ClipboardManager
  - run_command_in_termux(cmd)     — run cmd in Termux via RUN_COMMAND intent
  - poll_daemon_ready(...)         — GET /health every 3 s with tick_cb
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
    """Return True/False via Android PackageManager, or None if jnius unavailable.

    Uses two strategies in order:
    1. getPackageInfo() — works when QUERY_ALL_PACKAGES appop is granted.
    2. resolveActivity() with explicit component — bypasses Android 11+
       package-visibility restrictions entirely (no permission needed).
    """
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        pm = PythonActivity.mActivity.getPackageManager()

        # Strategy 1: direct package info lookup
        try:
            pm.getPackageInfo(package, 0)
            return True
        except Exception:
            pass

        # Strategy 2: explicit-component resolveActivity — exempt from visibility gate
        try:
            Intent = autoclass("android.content.Intent")
            intent = Intent()
            # Termux main activity — well-known stable component name
            intent.setClassName(package, f"{package}.app.TermuxActivity")
            return pm.resolveActivity(intent, 0) is not None
        except Exception:
            pass

        return False
    except Exception:
        return None


def _pkg_installed_pm(package: str) -> bool:
    """Fallback: use 'pm path <package>' (less restricted than 'pm list packages')."""
    try:
        # 'pm path <pkg>' returns 'package:/path/apk' if installed, blank/error if not
        result = subprocess.run(
            ["/system/bin/pm", "path", package],
            capture_output=True, text=True, timeout=5,
        )
        if "package:" in result.stdout:
            return True
    except Exception:
        pass
    # Last resort: pm list packages filter
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
        ClipData = autoclass("android.content.ClipData")
        activity = PythonActivity.mActivity

        def _copy(_dt: float) -> None:
            try:
                # Use string literal — more reliable than accessing inherited
                # static field CLIPBOARD_SERVICE via jnius autoclass.
                cm = activity.getSystemService("clipboard")
                clip = ClipData.newPlainText("GURUJEE", text)
                cm.setPrimaryClip(clip)
            except Exception:
                pass

        Clock.schedule_once(_copy, 0)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Run command in Termux via RUN_COMMAND intent
# ---------------------------------------------------------------------------

def run_command_in_termux(cmd: str) -> bool:
    """Send a com.termux.RUN_COMMAND intent to execute *cmd* in a visible Termux session.

    Requires ``allow-external-apps = true`` in ``~/.termux/termux.properties``
    (install.sh sets this automatically). Returns True if the intent was sent;
    silently returns False on any failure so callers can fall back gracefully.
    """
    # jnius / Android Intent path (preferred — works inside the APK)
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        activity = PythonActivity.mActivity

        intent = Intent()
        intent.setAction("com.termux.RUN_COMMAND")
        intent.setPackage(_TERMUX_PACKAGE)
        intent.setClassName(_TERMUX_PACKAGE, f"{_TERMUX_PACKAGE}.app.RunCommandService")
        intent.putExtra("com.termux.RUN_COMMAND_PATH",
                        "/data/data/com.termux/files/usr/bin/bash")
        # Pass the whole install command as a single "-c <cmd>" invocation
        intent.putExtra("com.termux.RUN_COMMAND_ARGUMENTS", ["-c", cmd])
        intent.putExtra("com.termux.RUN_COMMAND_BACKGROUND", False)
        intent.putExtra("com.termux.RUN_COMMAND_WORKDIR",
                        "/data/data/com.termux/files/home")
        # Use startForegroundService so Android 9+ doesn't block it
        try:
            activity.startForegroundService(intent)
        except Exception:
            activity.startService(intent)
        return True
    except Exception:
        pass

    # am-shell fallback (works if /system/bin/am is accessible in the APK sandbox)
    try:
        result = subprocess.run(
            [
                "/system/bin/am", "startservice",
                "--user", "0",
                "-n", f"{_TERMUX_PACKAGE}/.app.RunCommandService",
                "--es", "com.termux.RUN_COMMAND_PATH",
                "/data/data/com.termux/files/usr/bin/bash",
                "--esa", "com.termux.RUN_COMMAND_ARGUMENTS",
                f"-c,{cmd}",
                "--ez", "com.termux.RUN_COMMAND_BACKGROUND", "false",
            ],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Daemon readiness
# ---------------------------------------------------------------------------

def poll_daemon_ready(
    timeout_seconds: int = 120,
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
