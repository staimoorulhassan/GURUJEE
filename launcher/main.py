"""GURUJEE Launcher APK — Kivy entry point (T059).

Screens:
  ProgressScreen — shown while bootstrap runs (installs Termux, starts daemon).
  WebViewScreen  — loads http://localhost:7171 in a native Android WebView.

Run flow:
  GurujeeApp.on_start() → bootstrap thread → poll_daemon_ready() → switch screen.
"""
from __future__ import annotations

import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen, ScreenManager

from launcher.bootstrap import (
    check_termux_api_installed,
    check_termux_installed,
    inject_bootstrap,
    install_termux,
    install_termux_api,
    poll_daemon_ready,
)

# Bootstrap script that install.sh creates inside Termux home.
_BOOTSTRAP_SCRIPT = "/data/data/com.termux/files/home/gurujee/gurujee_bootstrap.sh"
_WEBVIEW_URL = "http://localhost:7171"

# Kivy .kv inline string (keeps this file self-contained for buildozer).
_KV = """
#:kivy 2.0

<ProgressScreen>:
    name: 'progress'
    canvas.before:
        Color:
            rgba: 0.039, 0.039, 0.039, 1
        Rectangle:
            pos: self.pos
            size: self.size

<WebViewScreen>:
    name: 'webview'
    canvas.before:
        Color:
            rgba: 0.039, 0.039, 0.039, 1
        Rectangle:
            pos: self.pos
            size: self.size
"""


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------

class ProgressScreen(Screen):
    """Boot screen — progress bar and status messages."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=40, spacing=16)

        self._title = Label(
            text="GURUJEE",
            font_size="28sp",
            color=(0.941, 0.647, 0, 1),  # amber #f0a500
            size_hint=(1, 0.15),
        )
        self._status = Label(
            text="Starting…",
            font_size="14sp",
            color=(0.8, 0.8, 0.8, 1),
            size_hint=(1, 0.1),
        )
        self._bar = ProgressBar(max=100, value=0, size_hint=(1, 0.06))
        self._detail = Label(
            text="",
            font_size="11sp",
            color=(0.5, 0.5, 0.5, 1),
            size_hint=(1, 0.1),
        )
        self._retry_btn = Button(
            text="Retry",
            font_size="14sp",
            size_hint=(0.4, 0.07),
            pos_hint={"center_x": 0.5},
            opacity=0,
            disabled=True,
            background_color=(0.941, 0.647, 0, 1),
        )
        self._retry_btn.bind(on_press=self._on_retry)

        layout.add_widget(Label(size_hint=(1, 0.25)))  # top spacer
        layout.add_widget(self._title)
        layout.add_widget(self._status)
        layout.add_widget(self._bar)
        layout.add_widget(self._detail)
        layout.add_widget(self._retry_btn)
        layout.add_widget(Label(size_hint=(1, None)))  # bottom filler
        self.add_widget(layout)

    # ------------------------------------------------------------------
    # Public helpers (called from background thread via Clock.schedule_once)
    # ------------------------------------------------------------------

    def set_status(self, text: str, progress: float = -1) -> None:
        """Update status label and optionally the progress bar (0–100)."""
        def _update(_dt: float) -> None:
            self._status.text = text
            if 0 <= progress <= 100:
                self._bar.value = progress
        Clock.schedule_once(_update, 0)

    def set_detail(self, text: str) -> None:
        def _update(_dt: float) -> None:
            self._detail.text = text
        Clock.schedule_once(_update, 0)

    def show_retry(self) -> None:
        def _update(_dt: float) -> None:
            self._retry_btn.opacity = 1
            self._retry_btn.disabled = False
        Clock.schedule_once(_update, 0)

    def hide_retry(self) -> None:
        def _update(_dt: float) -> None:
            self._retry_btn.opacity = 0
            self._retry_btn.disabled = True
        Clock.schedule_once(_update, 0)

    def _on_retry(self, _btn: Button) -> None:
        app = App.get_running_app()
        if app:
            self.hide_retry()
            app.start_bootstrap()


class WebViewScreen(Screen):
    """Full-screen Android WebView loading the PWA at localhost:7171."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._webview_loaded = False

    def on_enter(self) -> None:
        """Load the WebView the first time this screen is shown."""
        if self._webview_loaded:
            return
        self._webview_loaded = True
        try:
            self._load_native_webview()
        except Exception as exc:
            # Fallback: show a plain label if jnius unavailable (desktop testing).
            fallback = Label(
                text=f"WebView unavailable\n{exc}\n\nOpen: {_WEBVIEW_URL}",
                color=(0.8, 0.8, 0.8, 1),
                halign="center",
            )
            self.add_widget(fallback)

    def _load_native_webview(self) -> None:
        """Attach a native android.webkit.WebView using jnius."""
        from jnius import autoclass  # type: ignore[import-untyped]

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        WebView = autoclass("android.webkit.WebView")
        WebViewClient = autoclass("android.webkit.WebViewClient")
        activity = PythonActivity.mActivity

        def _create(_dt: float) -> None:
            wv = WebView(activity)
            settings = wv.getSettings()
            settings.setJavaScriptEnabled(True)
            settings.setDomStorageEnabled(True)
            settings.setCacheMode(0)  # LOAD_DEFAULT
            wv.setWebViewClient(WebViewClient())
            wv.loadUrl(_WEBVIEW_URL)

            # Attach to the Android view hierarchy.
            from android.runnable import run_on_ui_thread  # type: ignore[import-untyped]

            @run_on_ui_thread
            def _attach() -> None:
                activity.addContentView(
                    wv,
                    autoclass("android.view.ViewGroup$LayoutParams")(
                        -1, -1  # MATCH_PARENT
                    ),
                )

            _attach()

        Clock.schedule_once(_create, 0)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class GurujeeApp(App):
    """Kivy Application — manages screen transitions and bootstrap lifecycle."""

    def build(self) -> ScreenManager:
        from kivy.lang import Builder
        Builder.load_string(_KV)

        self._sm = ScreenManager()
        self._progress = ProgressScreen()
        self._webview = WebViewScreen()
        self._sm.add_widget(self._progress)
        self._sm.add_widget(self._webview)
        return self._sm

    def on_start(self) -> None:
        self.start_bootstrap()

    def start_bootstrap(self) -> None:
        """Launch bootstrap in a background thread (must not block UI)."""
        t = threading.Thread(target=self._bootstrap, daemon=True)
        t.start()

    def _switch_to_webview(self, _dt: float = 0) -> None:
        self._sm.current = "webview"

    # ------------------------------------------------------------------
    # Bootstrap sequence
    # ------------------------------------------------------------------

    def _bootstrap(self) -> None:  # noqa: PLR0912
        ps = self._progress

        # Step 1 — Termux
        ps.set_status("Checking Termux…", 5)
        if not check_termux_installed():
            ps.set_status("Installing Termux…", 10)
            ps.set_detail("This may take a moment")
            ok = install_termux()
            if not ok:
                ps.set_status("Termux install failed", 10)
                ps.set_detail("Tap Retry or install Termux manually")
                ps.show_retry()
                return
        ps.set_status("Termux ready", 20)

        # Step 2 — Termux:API
        ps.set_status("Checking Termux:API…", 25)
        if not check_termux_api_installed():
            ps.set_status("Installing Termux:API…", 30)
            install_termux_api()  # non-fatal if it fails
        ps.set_status("Termux:API ready", 40)

        # Step 3 — Inject bootstrap script into Termux
        ps.set_status("Starting GURUJEE…", 50)
        ps.set_detail("Injecting bootstrap script into Termux")
        inject_bootstrap(_BOOTSTRAP_SCRIPT)
        ps.set_status("Bootstrap injected", 60)

        # Step 4 — Poll until daemon ready
        ps.set_status("Connecting…", 65)
        ps.set_detail("Waiting for GURUJEE daemon (up to 3 min)")
        ready = poll_daemon_ready(timeout_seconds=180)

        if not ready:
            ps.set_status("Connection timed out", 65)
            ps.set_detail("GURUJEE did not start in time")
            ps.show_retry()
            return

        ps.set_status("Connected!", 100)
        ps.set_detail("Opening GURUJEE…")
        Clock.schedule_once(self._switch_to_webview, 0.5)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    GurujeeApp().run()


if __name__ == "__main__":
    main()
