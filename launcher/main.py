"""GURUJEE Launcher APK — Kivy entry point (T059).

Screens:
  ProgressScreen — shown while bootstrap runs (installs Termux, starts daemon).
  WebViewScreen  — loads http://localhost:7171 in a native Android WebView.

Run flow:
  GurujeeApp.on_start() → bootstrap thread → poll_daemon_ready() → switch screen.

Theme: dark #0a0a0a bg · cyan #00c8d7 primary · copper #c87941 secondary.
"""
from __future__ import annotations

import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.widget import Widget

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

# ── Palette ────────────────────────────────────────────────────────────────
_BG        = (0.039, 0.039, 0.039, 1)   # #0a0a0a
_CYAN      = (0,     0.784, 0.843, 1)   # #00c8d7  — logo eye glow
_COPPER    = (0.784, 0.475, 0.255, 1)   # #c87941  — logo chest feathers
_TEXT      = (0.878, 0.878, 0.878, 1)   # #e0e0e0
_MUTED     = (0.45,  0.45,  0.45,  1)   # #737373
_BTN_BG    = (0.055, 0.055, 0.055, 1)   # slight lift on #0a0a0a

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
    """Boot screen — logo, progress bar, and status messages."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

        root = BoxLayout(orientation="vertical", padding=32, spacing=12)

        # ── top spacer
        root.add_widget(Widget(size_hint=(1, 0.08)))

        # ── Logo ────────────────────────────────────────────────────────
        logo = Image(
            source="assets/icon.png",
            size_hint=(1, 0.30),
            allow_stretch=True,
            keep_ratio=True,
        )
        root.add_widget(logo)

        # ── Title ───────────────────────────────────────────────────────
        self._title = Label(
            text="[b]GURU[color=00c8d7]JEE[/color][/b]",
            markup=True,
            font_size="30sp",
            color=_TEXT,
            size_hint=(1, 0.10),
        )
        root.add_widget(self._title)

        # ── Status ──────────────────────────────────────────────────────
        self._status = Label(
            text="Starting…",
            font_size="14sp",
            color=_CYAN,
            size_hint=(1, 0.07),
        )
        root.add_widget(self._status)

        # ── Progress bar ────────────────────────────────────────────────
        self._bar = ProgressBar(max=100, value=0, size_hint=(1, 0.025))
        root.add_widget(self._bar)

        # ── Detail / sub-status ─────────────────────────────────────────
        self._detail = Label(
            text="",
            font_size="11sp",
            color=_MUTED,
            size_hint=(1, 0.07),
        )
        root.add_widget(self._detail)

        # ── Action buttons (hidden until needed) ────────────────────────
        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint=(1, 0.09),
            spacing=16,
            padding=[0, 4, 0, 4],
        )

        self._retry_btn = Button(
            text="Retry",
            font_size="14sp",
            size_hint=(0.45, 1),
            pos_hint={"center_y": 0.5},
            opacity=0,
            disabled=True,
            background_color=_CYAN,
            color=(0, 0, 0, 1),
        )
        self._retry_btn.bind(on_press=self._on_retry)

        self._skip_btn = Button(
            text="Skip",
            font_size="14sp",
            size_hint=(0.45, 1),
            pos_hint={"center_y": 0.5},
            opacity=0,
            disabled=True,
            background_color=_COPPER,
            color=(1, 1, 1, 1),
        )
        self._skip_btn.bind(on_press=self._on_skip)

        btn_row.add_widget(Widget(size_hint=(0.05, 1)))
        btn_row.add_widget(self._retry_btn)
        btn_row.add_widget(self._skip_btn)
        btn_row.add_widget(Widget(size_hint=(0.05, 1)))
        root.add_widget(btn_row)

        # ── Manual-install hint (hidden until needed) ────────────────────
        self._manual_hint = Label(
            text="",
            font_size="10sp",
            color=_MUTED,
            size_hint=(1, 0.06),
            halign="center",
            text_size=(None, None),
        )
        root.add_widget(self._manual_hint)

        root.add_widget(Widget(size_hint=(1, 0.06)))  # bottom filler
        self.add_widget(root)

    # ------------------------------------------------------------------
    # Public helpers (called from background thread via Clock.schedule_once)
    # ------------------------------------------------------------------

    def set_status(self, text: str, progress: float = -1) -> None:
        def _u(_dt: float) -> None:
            self._status.text = text
            if 0 <= progress <= 100:
                self._bar.value = progress
        Clock.schedule_once(_u, 0)

    def set_detail(self, text: str) -> None:
        def _u(_dt: float) -> None:
            self._detail.text = text
        Clock.schedule_once(_u, 0)

    def show_retry_skip(self, hint: str = "") -> None:
        def _u(_dt: float) -> None:
            self._retry_btn.opacity = 1
            self._retry_btn.disabled = False
            self._skip_btn.opacity = 1
            self._skip_btn.disabled = False
            self._manual_hint.text = hint
        Clock.schedule_once(_u, 0)

    def hide_retry_skip(self) -> None:
        def _u(_dt: float) -> None:
            self._retry_btn.opacity = 0
            self._retry_btn.disabled = True
            self._skip_btn.opacity = 0
            self._skip_btn.disabled = True
            self._manual_hint.text = ""
        Clock.schedule_once(_u, 0)

    # keep backward-compat with old show_retry callers
    def show_retry(self) -> None:
        self.show_retry_skip()

    def hide_retry(self) -> None:
        self.hide_retry_skip()

    # ------------------------------------------------------------------

    def _on_retry(self, _btn: Button) -> None:
        app = App.get_running_app()
        if app:
            self.hide_retry_skip()
            app.start_bootstrap()

    def _on_skip(self, _btn: Button) -> None:
        """Skip Termux install — proceed directly to daemon polling."""
        app = App.get_running_app()
        if app:
            self.hide_retry_skip()
            app.start_bootstrap(skip_termux=True)


class WebViewScreen(Screen):
    """Full-screen Android WebView loading the PWA at localhost:7171."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._webview_loaded = False

    def on_enter(self) -> None:
        if self._webview_loaded:
            return
        self._webview_loaded = True
        try:
            self._load_native_webview()
        except Exception as exc:
            fallback = Label(
                text=f"WebView unavailable\n{exc}\n\nOpen: {_WEBVIEW_URL}",
                color=_TEXT,
                halign="center",
            )
            self.add_widget(fallback)

    def _load_native_webview(self) -> None:
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
            settings.setCacheMode(0)
            wv.setWebViewClient(WebViewClient())
            wv.loadUrl(_WEBVIEW_URL)

            from android.runnable import run_on_ui_thread  # type: ignore[import-untyped]

            @run_on_ui_thread
            def _attach() -> None:
                activity.addContentView(
                    wv,
                    autoclass("android.view.ViewGroup$LayoutParams")(-1, -1),
                )

            _attach()

        Clock.schedule_once(_create, 0)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class GurujeeApp(App):

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

    def start_bootstrap(self, skip_termux: bool = False) -> None:
        t = threading.Thread(
            target=self._bootstrap,
            kwargs={"skip_termux": skip_termux},
            daemon=True,
        )
        t.start()

    def _switch_to_webview(self, _dt: float = 0) -> None:
        self._sm.current = "webview"

    # ------------------------------------------------------------------
    # Bootstrap sequence
    # ------------------------------------------------------------------

    def _bootstrap(self, skip_termux: bool = False) -> None:
        ps = self._progress

        # Step 1 — Termux (skippable)
        if not skip_termux:
            ps.set_status("Checking Termux…", 5)
            if not check_termux_installed():
                ps.set_status("Installing Termux…", 10)
                ps.set_detail("This may take a moment")
                ok = install_termux()
                if not ok:
                    ok = _try_intent_install("/sdcard/DCIM/termux.apk", ps)
                if not ok:
                    ps.set_status("[color=c87941]Termux install failed[/color]", 10)
                    ps.set_detail(
                        "Tap Retry to try again, or Skip to continue\n"
                        "You can install Termux manually from F-Droid"
                    )
                    ps.show_retry_skip(
                        hint="F-Droid: search 'Termux' — install, then tap Retry"
                    )
                    return
            ps.set_status("Termux ready", 20)
        else:
            ps.set_status("Skipped Termux install", 20)
            ps.set_detail("Assuming Termux is already installed")

        # Step 2 — Termux:API (non-fatal)
        ps.set_status("Checking Termux:API…", 25)
        if not check_termux_api_installed():
            ps.set_status("Installing Termux:API…", 30)
            install_termux_api()
        ps.set_status("Termux:API ready", 40)

        # Step 3 — Inject bootstrap script
        ps.set_status("Starting GURUJEE…", 50)
        ps.set_detail("Injecting bootstrap script into Termux")
        inject_bootstrap(_BOOTSTRAP_SCRIPT)
        ps.set_status("Bootstrap injected", 60)

        # Step 4 — Poll daemon
        ps.set_status("Connecting…", 65)
        ps.set_detail("Waiting for GURUJEE daemon (up to 3 min)")
        ready = poll_daemon_ready(timeout_seconds=180)

        if not ready:
            ps.set_status("[color=c87941]Connection timed out[/color]", 65)
            ps.set_detail("GURUJEE did not start in time")
            ps.show_retry_skip(hint="Tap Skip to open the UI anyway")
            return

        ps.set_status("[color=00c8d7]Connected![/color]", 100)
        ps.set_detail("Opening GURUJEE…")
        Clock.schedule_once(self._switch_to_webview, 0.5)


def _try_intent_install(apk_path: str, ps: "ProgressScreen") -> bool:
    """Fallback: use Android ACTION_INSTALL_PACKAGE intent via jnius."""
    try:
        from jnius import autoclass  # type: ignore[import-untyped]
        from pathlib import Path

        if not Path(apk_path).exists():
            return False

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        Build = autoclass("android.os.Build")

        activity = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_INSTALL_PACKAGE)

        # Android 7+ requires FileProvider URI
        if Build.VERSION.SDK_INT >= 24:
            FileProvider = autoclass("androidx.core.content.FileProvider")
            File = autoclass("java.io.File")
            uri = FileProvider.getUriForFile(
                activity,
                f"{activity.getPackageName()}.fileprovider",
                File(apk_path),
            )
        else:
            uri = Uri.fromFile(autoclass("java.io.File")(apk_path))

        intent.setData(uri)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        intent.putExtra("android.intent.extra.NOT_UNKNOWN_SOURCE", True)

        ps.set_detail("Waiting for manual install confirmation…")

        def _start(_dt: float) -> None:
            activity.startActivityForResult(intent, 1001)

        Clock.schedule_once(_start, 0)
        # Wait up to 60 s for the user to confirm install
        import time
        deadline = time.time() + 60
        while time.time() < deadline:
            from launcher.bootstrap import check_termux_installed
            if check_termux_installed():
                return True
            time.sleep(2)
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    GurujeeApp().run()


if __name__ == "__main__":
    main()
