"""GURUJEE Launcher APK — Kivy entry point (T059 redesign).

Screens:
  WelcomeScreen    — branding + "Install Termux from F-Droid" / "I have Termux → Next"
  SetupScreen      — copyable curl command + "Open Termux" button
  ConnectingScreen — polls /health with live countdown
  WebViewScreen    — loads http://localhost:7171 in a native Android WebView

Run flow (first time):
  on_start() quick-probe → not ready → WelcomeScreen
  WelcomeScreen → SetupScreen → ConnectingScreen → WebViewScreen

Run flow (subsequent opens):
  on_start() quick-probe → ready → WebViewScreen immediately

Theme: dark #0a0a0a bg · cyan #00c8d7 primary · copper #c87941 secondary.
"""
from __future__ import annotations

import threading
import urllib.request

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.widget import Widget

try:
    from .bootstrap import (
        copy_to_clipboard,
        open_termux,
        open_url,
        poll_daemon_ready,
        run_command_in_termux,
    )
except ImportError:
    from bootstrap import (
        copy_to_clipboard,
        open_termux,
        open_url,
        poll_daemon_ready,
        run_command_in_termux,
    )

_WEBVIEW_URL = "http://localhost:7171"
_HEALTH_URL = "http://127.0.0.1:7171/health"
_FDROID_TERMUX_URL = "https://f-droid.org/en/packages/com.termux/"
_INSTALL_COMMAND = (
    "curl -fsSL "
    "https://raw.githubusercontent.com/staimoorulhassan/GURUJEE/main/install.sh"
    " | bash"
)

# ── Palette ────────────────────────────────────────────────────────────────
_BG        = (0.039, 0.039, 0.039, 1)   # #0a0a0a
_PANEL     = (0.063, 0.063, 0.063, 1)   # #101010
_CYAN      = (0,     0.784, 0.843, 1)   # #00c8d7
_COPPER    = (0.784, 0.475, 0.255, 1)   # #c87941
_TEXT      = (0.878, 0.878, 0.878, 1)   # #e0e0e0
_MUTED     = (0.45,  0.45,  0.45,  1)   # #737373

_KV = """
#:kivy 2.0

<WelcomeScreen>:
    name: 'welcome'
    canvas.before:
        Color:
            rgba: 0.039, 0.039, 0.039, 1
        Rectangle:
            pos: self.pos
            size: self.size

<SetupScreen>:
    name: 'setup'
    canvas.before:
        Color:
            rgba: 0.039, 0.039, 0.039, 1
        Rectangle:
            pos: self.pos
            size: self.size

<ConnectingScreen>:
    name: 'connecting'
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
# Helpers
# ---------------------------------------------------------------------------

def _make_btn(
    text: str,
    bg: tuple,
    fg: tuple = (0, 0, 0, 1),
    size_hint_x: float = 1,
    font_size: str = "15sp",
) -> Button:
    return Button(
        text=text,
        font_size=font_size,
        size_hint=(size_hint_x, None),
        height="48dp",
        background_color=bg,
        color=fg,
    )


# ---------------------------------------------------------------------------
# WelcomeScreen
# ---------------------------------------------------------------------------

class WelcomeScreen(Screen):
    """Branding + F-Droid Termux install prompt."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

        root = BoxLayout(orientation="vertical", padding=32, spacing=14)
        root.add_widget(Widget(size_hint=(1, 0.06)))

        logo = Image(
            source="assets/icon.png",
            size_hint=(1, 0.28),
            allow_stretch=True,
            keep_ratio=True,
        )
        root.add_widget(logo)

        root.add_widget(Label(
            text="[b]GURU[color=00c8d7]JEE[/color][/b]",
            markup=True,
            font_size="32sp",
            color=_TEXT,
            size_hint=(1, None),
            height="48dp",
        ))

        root.add_widget(Label(
            text="The new era of operating your device with AI.",
            font_size="14sp",
            color=_CYAN,
            size_hint=(1, None),
            height="30dp",
        ))

        root.add_widget(Widget(size_hint=(1, 0.04)))

        root.add_widget(Label(
            text=(
                "To get started, you need [b]Termux[/b] installed from F-Droid.\n"
                "(Do NOT use the Play Store version.)"
            ),
            markup=True,
            font_size="13sp",
            color=_TEXT,
            size_hint=(1, None),
            height="52dp",
            halign="center",
            text_size=(None, None),
        ))

        root.add_widget(Widget(size_hint=(1, 0.04)))

        fdroid_btn = _make_btn(
            "Install Termux from F-Droid", _CYAN, (0, 0, 0, 1)
        )
        fdroid_btn.bind(on_press=self._on_fdroid)
        root.add_widget(fdroid_btn)

        root.add_widget(Widget(size_hint=(1, None), height="10dp"))

        have_btn = _make_btn(
            "I already have Termux  >>  Next", _PANEL, _MUTED
        )
        have_btn.bind(on_press=self._on_have_termux)
        root.add_widget(have_btn)

        self._status = Label(
            text="",
            font_size="12sp",
            color=_COPPER,
            size_hint=(1, None),
            height="28dp",
            halign="center",
        )
        root.add_widget(self._status)

        root.add_widget(Widget(size_hint=(1, 1)))
        self.add_widget(root)

    def _on_fdroid(self, _btn: Button) -> None:
        open_url(_FDROID_TERMUX_URL)

    def _on_have_termux(self, _btn: Button) -> None:
        # Trust the user — don't gate on PackageManager detection.
        # Android 13+ visibility restrictions make getPackageInfo and
        # resolveActivity unreliable without a <queries> manifest entry.
        # ConnectingScreen handles the daemon-not-running case gracefully.
        App.get_running_app().go_to("setup")


# ---------------------------------------------------------------------------
# SetupScreen
# ---------------------------------------------------------------------------

class SetupScreen(Screen):
    """Single copyable curl command + Open Termux button."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

        root = BoxLayout(orientation="vertical", padding=32, spacing=14)
        root.add_widget(Widget(size_hint=(1, 0.05)))

        logo = Image(
            source="assets/icon.png",
            size_hint=(1, 0.15),
            allow_stretch=True,
            keep_ratio=True,
        )
        root.add_widget(logo)

        root.add_widget(Label(
            text="[b]Set up GURUJEE[/b]",
            markup=True,
            font_size="24sp",
            color=_TEXT,
            size_hint=(1, None),
            height="40dp",
        ))

        instructions = (
            "1.  Open Termux\n"
            "2.  Paste the command below and press [b]Enter[/b]\n"
            "3.  Follow the on-screen prompts\n"
            "4.  Return here when done"
        )
        root.add_widget(Label(
            text=instructions,
            markup=True,
            font_size="13sp",
            color=_TEXT,
            size_hint=(1, None),
            height="88dp",
            halign="left",
            text_size=(None, None),
        ))

        # Command box
        cmd_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height="72dp",
            padding=[12, 8, 12, 8],
        )
        with cmd_box.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.063, 0.063, 0.063, 1)
            cmd_box._rect = RoundedRectangle(
                pos=cmd_box.pos, size=cmd_box.size, radius=[8]
            )
        cmd_box.bind(
            pos=lambda inst, v: setattr(inst._rect, "pos", v),
            size=lambda inst, v: setattr(inst._rect, "size", v),
        )
        self._cmd_label = Label(
            text=_INSTALL_COMMAND,
            font_size="10sp",
            color=_CYAN,
            halign="left",
            valign="middle",
            text_size=(None, None),
        )
        cmd_box.add_widget(self._cmd_label)
        root.add_widget(cmd_box)

        copy_btn = _make_btn("Copy Command", _CYAN, (0, 0, 0, 1))
        copy_btn.bind(on_press=self._on_copy)
        root.add_widget(copy_btn)

        open_btn = _make_btn("Open Termux", _PANEL, _TEXT)
        open_btn.bind(on_press=self._on_open_termux)
        root.add_widget(open_btn)

        check_btn = _make_btn(
            "I've run it -- Check Connection", _COPPER, (1, 1, 1, 1)
        )
        check_btn.bind(on_press=self._on_check)
        root.add_widget(check_btn)

        self._feedback = Label(
            text="",
            font_size="12sp",
            color=_CYAN,
            size_hint=(1, None),
            height="28dp",
        )
        root.add_widget(self._feedback)

        root.add_widget(Widget(size_hint=(1, 1)))
        self.add_widget(root)

    def _on_copy(self, _btn: Button) -> None:
        copy_to_clipboard(_INSTALL_COMMAND)

        def _u(_dt: float) -> None:
            self._feedback.text = "Copied to clipboard!"
        Clock.schedule_once(_u, 0)
        Clock.schedule_once(lambda _dt: setattr(self._feedback, "text", ""), 2)

    def _on_open_termux(self, _btn: Button) -> None:
        # Always copy the command first so clipboard is ready to paste
        copy_to_clipboard(_INSTALL_COMMAND)

        # Try to auto-run the install command in Termux via RUN_COMMAND intent.
        # This works only after install.sh has set allow-external-apps=true.
        dispatched = run_command_in_termux(_INSTALL_COMMAND)

        if dispatched:
            msg = "Setup started in Termux! Return here when done."
        else:
            # Fallback: open Termux so user can paste manually
            open_termux()
            msg = "Termux opened. Command copied — long-press in Termux to paste, then Enter."

        def _u(_dt: float) -> None:
            self._feedback.text = msg
        Clock.schedule_once(_u, 0)
        Clock.schedule_once(lambda _dt: setattr(self._feedback, "text", ""), 8)

    def _on_check(self, _btn: Button) -> None:
        App.get_running_app().go_to("connecting")


# ---------------------------------------------------------------------------
# ConnectingScreen
# ---------------------------------------------------------------------------

class ConnectingScreen(Screen):
    """Polls /health with live countdown; switches to WebView on success."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

        root = BoxLayout(orientation="vertical", padding=32, spacing=14)
        root.add_widget(Widget(size_hint=(1, 0.08)))

        logo = Image(
            source="assets/icon.png",
            size_hint=(1, 0.18),
            allow_stretch=True,
            keep_ratio=True,
        )
        root.add_widget(logo)

        root.add_widget(Label(
            text="[b]Connecting to GURUJEE...[/b]",
            markup=True,
            font_size="22sp",
            color=_TEXT,
            size_hint=(1, None),
            height="38dp",
        ))

        self._status = Label(
            text="Checking...",
            markup=True,
            font_size="14sp",
            color=_CYAN,
            size_hint=(1, None),
            height="30dp",
        )
        root.add_widget(self._status)

        self._bar = ProgressBar(max=100, value=0, size_hint=(1, None), height="8dp")
        root.add_widget(self._bar)

        self._detail = Label(
            text="",
            font_size="12sp",
            color=_MUTED,
            size_hint=(1, None),
            height="28dp",
            halign="center",
            text_size=(None, None),
        )
        root.add_widget(self._detail)

        # Retry row (hidden initially)
        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height="52dp",
            spacing=12,
        )
        self._open_termux_btn = _make_btn(
            "Open Termux", _PANEL, _TEXT, size_hint_x=0.33
        )
        self._open_termux_btn.bind(on_press=lambda _b: open_termux())
        self._retry_btn = _make_btn(
            "Try Again", _CYAN, (0, 0, 0, 1), size_hint_x=0.34
        )
        self._retry_btn.bind(on_press=self._on_retry)
        self._setup_btn = _make_btn(
            "Back to Setup", _COPPER, (1, 1, 1, 1), size_hint_x=0.33
        )
        self._setup_btn.bind(on_press=lambda _b: App.get_running_app().go_to("setup"))

        for btn in (self._open_termux_btn, self._retry_btn, self._setup_btn):
            btn.opacity = 0
            btn.disabled = True
            btn_row.add_widget(btn)
        root.add_widget(btn_row)

        root.add_widget(Widget(size_hint=(1, 1)))
        self.add_widget(root)
        self._polling = False

    def on_enter(self) -> None:
        self._hide_retry_row()
        self._start_poll()

    def _start_poll(self) -> None:
        if self._polling:
            return
        self._polling = True
        self.set_status("Checking...", 0)
        self.set_detail("")
        t = threading.Thread(target=self._poll_thread, daemon=True)
        t.start()

    def _poll_thread(self) -> None:
        _TIMEOUT = 120

        def _tick(elapsed: int, remaining: int) -> None:
            pct = int(100 * elapsed / _TIMEOUT)
            self.set_status(f"Connecting... ({remaining}s)", min(pct, 95))

        ready = poll_daemon_ready(timeout_seconds=_TIMEOUT, tick_cb=_tick)
        self._polling = False

        if ready:
            self.set_status("[color=00c8d7]Connected![/color]", 100)
            self.set_detail("Opening GURUJEE...")
            Clock.schedule_once(
                lambda _dt: App.get_running_app().go_to("webview"), 0.5
            )
        else:
            self.set_status("[color=c87941]Not responding[/color]", 0)
            self.set_detail(
                "GURUJEE is not running in Termux.\n"
                "Open Termux and check the daemon is running."
            )
            self._show_retry_row()

    def set_status(self, text: str, progress: float = -1) -> None:
        def _u(_dt: float) -> None:
            self._status.text = text
            if 0 <= progress <= 100:
                self._bar.value = progress
        Clock.schedule_once(_u, 0)

    def set_detail(self, text: str) -> None:
        Clock.schedule_once(lambda _dt: setattr(self._detail, "text", text), 0)

    def _show_retry_row(self) -> None:
        def _u(_dt: float) -> None:
            for btn in (self._open_termux_btn, self._retry_btn, self._setup_btn):
                btn.opacity = 1
                btn.disabled = False
        Clock.schedule_once(_u, 0)

    def _hide_retry_row(self) -> None:
        def _u(_dt: float) -> None:
            for btn in (self._open_termux_btn, self._retry_btn, self._setup_btn):
                btn.opacity = 0
                btn.disabled = True
        Clock.schedule_once(_u, 0)

    def _on_retry(self, _btn: Button) -> None:
        self._hide_retry_row()
        self._start_poll()


# ---------------------------------------------------------------------------
# WebViewScreen
# ---------------------------------------------------------------------------

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
        self._sm.add_widget(WelcomeScreen())
        self._sm.add_widget(SetupScreen())
        self._sm.add_widget(ConnectingScreen())
        self._sm.add_widget(WebViewScreen())
        return self._sm

    def on_start(self) -> None:
        # Fast probe: if daemon already running, skip all onboarding
        t = threading.Thread(target=self._quick_probe, daemon=True)
        t.start()

    def _quick_probe(self) -> None:
        """3-second probe — go straight to WebView if daemon already up."""
        try:
            with urllib.request.urlopen(_HEALTH_URL, timeout=3) as resp:
                import json
                data = json.loads(resp.read())
                if data.get("status") == "ready":
                    Clock.schedule_once(lambda _dt: self.go_to("webview"), 0)
                    return
        except Exception:
            pass
        # Not ready — start at WelcomeScreen (already the default)
        Clock.schedule_once(lambda _dt: self.go_to("welcome"), 0)

    def go_to(self, screen: str) -> None:
        self._sm.current = screen


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    GurujeeApp().run()


if __name__ == "__main__":
    main()
