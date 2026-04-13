"""
GURUJEE Launcher APK — main.py
Kivy entry point for the thin Android launcher.

Screen flow:
  SplashScreen (2 s) → check Termux installed
    → missing: show "Install Termux" button → F-Droid URL in browser
    → present:  SetupScreen → run install.sh inside Termux
               → poll localhost:7171/health every 3 s
               → 200 OK: switch to ChatScreen (WebView)
"""
from __future__ import annotations

import threading
import time

import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TERMUX_PKG = "com.termux"
FDROID_URL = "https://f-droid.org/packages/com.termux/"
INSTALL_CMD = (
    "curl -fsSL "
    "https://raw.githubusercontent.com/staimoorulhassan/GURUJEE/main/install.sh"
    " | bash"
)
HEALTH_URL = "http://localhost:7171/health"
HEALTH_POLL_INTERVAL = 3  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_termux_installed() -> bool:
    """Return True if the Termux package is installed on the device."""
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        context = PythonActivity.mActivity
        pm = context.getPackageManager()
        pm.getPackageInfo(TERMUX_PKG, 0)
        return True
    except Exception:
        return False


def _open_url_in_browser(url: str) -> None:
    """Open *url* in the default Android browser via an Intent."""
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        PythonActivity.mActivity.startActivity(intent)
    except Exception as exc:
        print(f"[GURUJEE] open_url_in_browser failed: {exc}")


def _launch_termux_command(command: str) -> None:
    """Send *command* to Termux via an explicit Intent."""
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        Intent = autoclass("android.content.Intent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        intent = Intent()
        intent.setClassName(TERMUX_PKG, "com.termux.app.TermuxActivity")
        intent.putExtra("com.termux.app.terminal_command", command)
        # FLAG_ACTIVITY_NEW_TASK required when starting from non-Activity context
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        PythonActivity.mActivity.startActivity(intent)
    except Exception as exc:
        print(f"[GURUJEE] launch_termux_command failed: {exc}")


def _open_webview(url: str) -> None:
    """Open *url* in an Android WebView via pyjnius."""
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        WebView = autoclass("android.webkit.WebView")
        WebSettings = autoclass("android.webkit.WebSettings")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity

        def _run(dt: float) -> None:  # must run on UI thread
            wv = WebView(activity)
            settings = wv.getSettings()
            settings.setJavaScriptEnabled(True)
            settings.setDomStorageEnabled(True)
            settings.setLoadWithOverviewMode(True)
            settings.setUseWideViewPort(True)
            wv.loadUrl(url)
            activity.setContentView(wv)

        Clock.schedule_once(_run, 0)
    except Exception as exc:
        print(f"[GURUJEE] open_webview failed: {exc}")


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------

class SplashScreen(Screen):
    """Black background, amber GURUJEE title, spinner while checking Termux."""

    def on_enter(self) -> None:
        Clock.schedule_once(self._check_termux, 2)

    def _check_termux(self, dt: float) -> None:
        app = App.get_running_app()
        if _is_termux_installed():
            app.root.current = "setup"
        else:
            self.ids.status_label.text = (
                "Termux is required but not installed.\n"
                "Tap the button below to install it from F-Droid."
            )
            self.ids.install_btn.opacity = 1
            self.ids.install_btn.disabled = False
            self.ids.spinner.active = False

    def open_fdroid(self) -> None:
        _open_url_in_browser(FDROID_URL)


class SetupScreen(Screen):
    """Shows install.sh progress and polls the health endpoint."""

    def on_enter(self) -> None:
        self.ids.log_label.text = "Launching install.sh inside Termux…\n"
        _launch_termux_command(INSTALL_CMD)
        threading.Thread(target=self._poll_health, daemon=True).start()

    def _append_log(self, text: str) -> None:
        def _update(dt: float) -> None:
            self.ids.log_label.text += text + "\n"
        Clock.schedule_once(_update, 0)

    def _poll_health(self) -> None:
        self._append_log("Waiting for GURUJEE daemon to start…")
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = requests.get(HEALTH_URL, timeout=2)
                if resp.status_code == 200:
                    self._append_log(f"✓ Daemon ready (attempt {attempt})")
                    Clock.schedule_once(self._switch_to_chat, 0)
                    return
            except Exception:
                pass
            self._append_log(f"  [{attempt}] Not ready yet, retrying in {HEALTH_POLL_INTERVAL}s…")
            time.sleep(HEALTH_POLL_INTERVAL)

    def _switch_to_chat(self, dt: float) -> None:
        App.get_running_app().root.current = "chat"


class ChatScreen(Screen):
    """Opens the GURUJEE PWA in an Android WebView."""

    def on_enter(self) -> None:
        _open_webview("http://localhost:7171")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class GurujeeApp(App):
    def build(self) -> ScreenManager:
        Builder.load_file("gurujee.kv")
        sm = ScreenManager()
        sm.add_widget(SplashScreen(name="splash"))
        sm.add_widget(SetupScreen(name="setup"))
        sm.add_widget(ChatScreen(name="chat"))
        return sm


if __name__ == "__main__":
    GurujeeApp().run()
