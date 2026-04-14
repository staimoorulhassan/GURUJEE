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


# ---------------------------------------------------------------------------
# Package detection — use PackageManager API; fall back to pm shell command
# ---------------------------------------------------------------------------

def _pkg_installed_jnius(package: str) -> Optional[bool]:
    """Return True/False via Android PackageManager, or None if jnius unavailable."""
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        NameNotFoundException = autoclass(
            "android.content.pm.PackageManager$NameNotFoundException"
        )
        pm = PythonActivity.mActivity.getPackageManager()
        try:
            pm.getPackageInfo(package, 0)
            return True
        except Exception:
            return False
    except Exception:
        return None


def _pkg_installed_pm(package: str) -> bool:
    """Fallback: call /system/bin/pm directly (works in some environments)."""
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


def check_termux_api_installed() -> bool:
    result = _pkg_installed_jnius(_TERMUX_API_PACKAGE)
    if result is not None:
        return result
    return _pkg_installed_pm(_TERMUX_API_PACKAGE)


# ---------------------------------------------------------------------------
# Termux installation
# ---------------------------------------------------------------------------

def install_termux(apk_path: Optional[str] = None) -> bool:
    """Install Termux from *apk_path* using the system PackageInstaller intent."""
    if apk_path is None:
        apk_path = "/sdcard/DCIM/termux.apk"
    if not Path(apk_path).exists():
        return False
    try:
        # Use ACTION_INSTALL_PACKAGE via system installer (no root needed).
        from jnius import autoclass  # type: ignore[import-untyped]
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        Build = autoclass("android.os.Build")
        File = autoclass("java.io.File")

        activity = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_INSTALL_PACKAGE)

        if Build.VERSION.SDK_INT >= 24:
            FileProvider = autoclass("androidx.core.content.FileProvider")
            uri = FileProvider.getUriForFile(
                activity,
                f"{activity.getPackageName()}.fileprovider",
                File(apk_path),
            )
        else:
            uri = Uri.fromFile(File(apk_path))

        intent.setData(uri)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        intent.putExtra("android.intent.extra.NOT_UNKNOWN_SOURCE", True)

        from kivy.clock import Clock

        def _start(_dt: float) -> None:
            activity.startActivityForResult(intent, 1001)

        Clock.schedule_once(_start, 0)
        return True  # intent launched; caller polls check_termux_installed()
    except Exception:
        pass

    # Last resort: pm install via shell
    try:
        result = subprocess.run(
            ["/system/bin/pm", "install", "-r", apk_path],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False


def install_termux_api(apk_path: Optional[str] = None) -> bool:
    if apk_path is None:
        apk_path = "/sdcard/DCIM/termux-api.apk"
    if not Path(apk_path).exists():
        return False
    try:
        result = subprocess.run(
            ["/system/bin/pm", "install", "-r", apk_path],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Open Termux (simpler than RUN_COMMAND_PATH which needs allow-external-apps)
# ---------------------------------------------------------------------------

def open_termux() -> bool:
    """Launch Termux via intent so the user can interact with it."""
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
            ["am", "start", "-n",
             f"{_TERMUX_PACKAGE}/.app.TermuxActivity"],
            timeout=5,
        )
        return True
    except Exception:
        return False


def inject_bootstrap(script_path: str) -> bool:
    """Try to run *script_path* inside Termux via RUN_COMMAND broadcast.

    Requires allow-external-apps = true in ~/.termux/termux.properties.
    Falls back gracefully — caller should open_termux() as a secondary hint.
    """
    try:
        result = subprocess.run(
            [
                "am", "broadcast",
                "-a", "com.termux.app.RUN_COMMAND",
                "-n", f"{_TERMUX_PACKAGE}/.app.RunCommandService",
                "--es", "com.termux.app.RUN_COMMAND_PATH", script_path,
                "--ez", "com.termux.app.RUN_COMMAND_SESSION_ACTION", "0",
            ],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Daemon readiness
# ---------------------------------------------------------------------------

def poll_daemon_ready(
    timeout_seconds: int = 180,
    tick_cb=None,
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
        remaining = int(deadline - time.time())
        if tick_cb:
            tick_cb(elapsed, remaining)
        time.sleep(3)
    return False
