"""Guided first-run setup wizard for GURUJEE (Rich terminal UI)."""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import stat
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from gurujee.config.loader import ConfigLoader

logger = logging.getLogger(__name__)
_console = Console()

# ---------------------------------------------------------------------------
# Public exceptions
# ---------------------------------------------------------------------------


class SetupStepError(Exception):
    """Raised when a wizard step fails and cannot be retried."""

    def __init__(self, code: str, message: str = "") -> None:
        # Always include code so pytest.raises(match=...) can match on it
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code


# ---------------------------------------------------------------------------
# Wizard
# ---------------------------------------------------------------------------

_ORDERED_STEPS = [
    "packages",
    "shizuku",
    "accessibility_apk",
    "permissions",
    "keystore_pin",
    "pollinations_key",
    "ai_model",
    "voice_sample",
    "daemons",
]

_OPTIONAL_STEPS = {"accessibility_apk", "voice_sample", "pollinations_key"}

# SHA-256 of the official GURUJEE Accessibility Service APK (placeholder — update on release)
_EXPECTED_APK_SHA256 = "0" * 64  # TODO: replace with real checksum on first release


class SetupWizard:
    # Class-level copy so tests can patch it per-instance via patch.object(wizard, ...)
    _EXPECTED_APK_SHA256: str = _EXPECTED_APK_SHA256
    """Guides the user through all 8 first-run setup steps."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = Path(data_dir) if data_dir else Path("data")
        self._config_dir = Path(os.environ.get("GURUJEE_CONFIG_DIR", "config"))
        self._state_path = self._data_dir / "setup_state.yaml"
        self._boot_script_path = Path.home() / ".termux" / "boot" / "start-gurujee.sh"

    # ------------------------------------------------------------------ #
    # Entry point                                                           #
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        """Run all pending setup steps to completion."""
        _console.print(Panel("[bold amber]GURUJEE Setup Wizard[/bold amber]", expand=False))
        self._data_dir.mkdir(parents=True, exist_ok=True)
        state = self._load_state()
        self._execute_steps(state)

    def _execute_steps(self, state: dict[str, Any]) -> None:
        step_fns: dict[str, Callable[[dict[str, Any]], None]] = {
            "packages": self._step_packages_inner,
            "shizuku": self._step_shizuku_inner,
            "accessibility_apk": self._step_accessibility_apk_inner,
            "permissions": self._step_permissions_inner,
            "keystore_pin": self._step_keystore_pin_inner,
            "pollinations_key": self._step_pollinations_key_inner,
            "ai_model": self._step_ai_model_inner,
            "voice_sample": self._step_voice_sample_inner,
            "daemons": self._step_daemons_inner,
        }
        for step_name in _ORDERED_STEPS:
            fn = step_fns[step_name]
            required = step_name not in _OPTIONAL_STEPS
            self._step_runner(step_name, lambda f=fn: f(state), state, required=required)

        state["completed_at"] = datetime.now(timezone.utc).isoformat()
        self._save_state(state)
        _console.print("\n[bold green]✓ Setup complete — GURUJEE is ready![/bold green]\n")

    # ------------------------------------------------------------------ #
    # State helpers                                                         #
    # ------------------------------------------------------------------ #

    def _load_state(self) -> dict[str, Any]:
        existing = ConfigLoader.load_setup_state(self._state_path)
        if not existing:
            existing = {
                "version": 1,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": None,
                "steps": {
                    step: {
                        "completed": False,
                        "skipped": False,
                        "completed_at": None,
                    }
                    for step in _ORDERED_STEPS
                },
            }
        return existing

    def _save_state(self, state: dict[str, Any]) -> None:
        ConfigLoader.save_setup_state(state, self._state_path)

    def _step_runner(
        self,
        step_name: str,
        fn: Callable[[], None],
        state: dict[str, Any],
        *,
        required: bool = True,
    ) -> None:
        """Run *fn* for *step_name* unless already completed or skipped."""
        step = state.get("steps", {}).get(step_name, {})
        if step.get("completed") or step.get("skipped"):
            return
        _console.rule(f"[bold]Step: {step_name}[/bold]")
        try:
            fn()
            if not step.get("skipped"):
                step["completed"] = True
                step["completed_at"] = datetime.now(timezone.utc).isoformat()
            state["steps"][step_name] = step
            self._save_state(state)
        except SetupStepError as exc:
            _console.print(f"[red]Step '{step_name}' failed: {exc}[/red]")
            if required:
                raise

    # ------------------------------------------------------------------ #
    # Step implementations (inner — called by _step_runner)                #
    # ------------------------------------------------------------------ #

    def _step_packages_inner(self, state: Optional[dict] = None) -> None:
        """Install required Termux packages and Python dependencies."""
        for cmd in [
            ["pkg", "update", "-y"],
            ["pkg", "upgrade", "-y"],
            ["pkg", "install", "-y", "python", "git"],
        ]:
            for attempt in range(3):
                result = subprocess.run(cmd, capture_output=False)
                if result.returncode == 0:
                    break
                if attempt == 2:
                    raise SetupStepError("packages_failed", f"Command failed: {' '.join(cmd)}")
                retry = Prompt.ask("Command failed. Retry?", choices=["y", "n"], default="y")
                if retry != "y":
                    raise SetupStepError("packages_failed", "User aborted.")

        result = subprocess.run(["pip", "install", "-r", "requirements.txt"])
        if result.returncode != 0:
            raise SetupStepError("pip_failed", "pip install -r requirements.txt failed.")

    def _step_shizuku_inner(self, state: Optional[dict] = None) -> None:
        """Guide the user to activate Shizuku for device access."""
        _console.print(Panel(
            "[bold]Shizuku Activation[/bold]\n\n"
            "Shizuku allows GURUJEE to use Android APIs without root.\n\n"
            "1. Install Shizuku from F-Droid or Play Store.\n"
            "2. Launch Shizuku and tap 'Pairing (wireless debugging)'.\n"
            "3. Follow the on-screen instructions to activate.\n\n"
            "Once activated, press Enter to continue.",
            title="Step 2: Shizuku",
        ))
        Prompt.ask("Press [Enter] when Shizuku is activated")

    def _step_accessibility_apk_inner(
        self,
        state: Optional[dict] = None,
        apk_dest: Optional[Path] = None,
    ) -> None:
        """Download and install the GURUJEE Accessibility Service APK."""
        apk_url = (
            "https://github.com/gurujee/gurujee/releases/latest/download/"
            "gurujee-accessibility.apk"
        )
        if apk_dest is None:
            apk_dest = Path("/tmp/gurujee-accessibility.apk")

        _console.print(Panel(
            f"[bold]Accessibility Service APK[/bold]\n\n"
            f"URL: {apk_url}\n"
            f"Expected SHA-256: {_EXPECTED_APK_SHA256}\n\n"
            "The APK will be downloaded, verified, and installed.",
            title="Step 3: Accessibility APK",
        ))

        _console.print("Downloading APK...")
        urllib.request.urlretrieve(apk_url, str(apk_dest))

        actual_sha256 = hashlib.sha256(apk_dest.read_bytes()).hexdigest()
        if actual_sha256 != self._EXPECTED_APK_SHA256:
            apk_dest.unlink(missing_ok=True)
            raise SetupStepError(
                "sha256_mismatch",
                f"APK checksum mismatch!\n  Expected: {self._EXPECTED_APK_SHA256}\n  Got: {actual_sha256}",
            )

        result = subprocess.run(["pm", "install", str(apk_dest)])
        apk_dest.unlink(missing_ok=True)
        if result.returncode != 0:
            raise SetupStepError("apk_install_failed", "pm install returned non-zero exit.")

        if state and "steps" in state:
            state["steps"]["accessibility_apk"]["apk_sha256"] = actual_sha256

    def _step_permissions_inner(self, state: Optional[dict] = None) -> None:
        """Request all required Android permissions."""
        permissions = [
            "android.permission.RECORD_AUDIO",
            "android.permission.READ_CONTACTS",
            "android.permission.READ_CALL_LOG",
        ]
        _console.print("[bold]Requesting Android permissions...[/bold]")
        granted: list[str] = []
        denied: list[str] = []
        for perm in permissions:
            result = subprocess.run(["termux-permission", perm], capture_output=True)
            if result.returncode == 0:
                granted.append(perm)
                _console.print(f"  [green]✓[/green] {perm}")
            else:
                denied.append(perm)
                _console.print(f"  [yellow]✗[/yellow] {perm} (denied — some features may not work)")

        if state and "steps" in state:
            state["steps"]["permissions"]["granted"] = granted
            state["steps"]["permissions"]["denied"] = denied

    def _step_keystore_pin_inner(self, state: Optional[dict] = None) -> None:
        """Set up the AES-256-GCM keystore with user's chosen PIN."""
        from gurujee.keystore.keystore import Keystore

        _console.print(Panel(
            "[bold]Keystore PIN Setup[/bold]\n\n"
            "Choose a 4–8 digit PIN to protect your credentials.\n"
            "This PIN is [bold red]NEVER stored[/bold red] — it is used to derive your\n"
            "encryption key. If you forget it, your keystore must be wiped\n"
            "and all credentials re-entered.\n",
            title="Step 5: Keystore PIN",
        ))

        for attempt in range(3):
            pin = Prompt.ask("Enter PIN (4–8 digits)", password=True)
            if not (4 <= len(pin) <= 8 and pin.isdigit()):
                _console.print("[yellow]PIN must be 4–8 digits.[/yellow]")
                continue
            confirm = Prompt.ask("Confirm PIN", password=True)
            if pin != confirm:
                _console.print("[yellow]PINs do not match.[/yellow]")
                continue

            ks_path = self._data_dir / "gurujee.keystore"
            ks = Keystore(ks_path, pin=pin)
            ks.unlock()
            ks.lock()
            _console.print("[green]✓ Keystore created.[/green]")

            if state and "steps" in state:
                state["steps"]["keystore_pin"]["completed"] = True
                state["steps"]["keystore_pin"]["pin_set"] = True
            return

        raise SetupStepError("pin_setup_failed", "Failed to set PIN after 3 attempts.")

    def _step_pollinations_key_inner(self, state: Optional[dict] = None) -> None:
        """Prompt the user to enter their free Pollinations API key."""
        from gurujee.keystore.keystore import Keystore  # local import to avoid circular

        _console.print(Panel(
            "[bold amber]Pollinations API Key (Optional)[/bold amber]\n\n"
            "GURUJEE uses [bold]Pollinations AI[/bold] as its default provider.\n"
            "A [bold green]free[/bold green] API key is required — no credit card.\n\n"
            "Get yours at: [bold]https://auth.pollinations.ai[/bold]\n"
            "(Sign up takes ~30 seconds)\n\n"
            "You can skip this step and add the key later via\n"
            "Settings → AI Models → Pollinations.",
            title="Step 5.5: Pollinations API Key",
        ))

        poll_key = Prompt.ask(
            "Enter your Pollinations API key (press Enter to skip)",
            password=True,
            default="",
        )

        if poll_key.strip():
            keystore_path = self._data_dir / "gurujee.keystore"
            pin = Prompt.ask("Enter your keystore PIN to save the key", password=True, default="")
            try:
                from gurujee.keystore.keystore import KeystoreError
                ks = Keystore(keystore_path, pin)
                ks.set("POLLINATIONS_API_KEY", poll_key.strip())
                _console.print("[green]✓ Pollinations API key saved to keystore.[/green]")
                if state and "steps" in state:
                    state["steps"]["pollinations_key"]["pollinations_key_set"] = True
            except (OSError, ValueError, KeystoreError) as exc:
                _console.print(f"[yellow]⚠ Could not save key: {exc}. Add it later in Settings.[/yellow]")
                if state and "steps" in state:
                    state["steps"]["pollinations_key"]["skipped"] = True
        else:
            _console.print(
                "[yellow]⚠ Skipped — GURUJEE may not work without a Pollinations key.\n"
                "Add it later: Settings → AI Models → Pollinations[/yellow]"
            )
            if state and "steps" in state:
                state["steps"]["pollinations_key"]["skipped"] = True

    def _step_ai_model_inner(self, state: Optional[dict] = None) -> None:
        """Let the user choose their AI model and write it to data/user_config.yaml."""
        models_cfg = ConfigLoader.load_yaml(self._config_dir / "models.yaml")
        available: list[str] = models_cfg.get("available", ["nova-fast"])
        default_model: str = str(models_cfg.get("default", "nova-fast"))

        table = Table(title="Available AI Models", show_header=True)
        table.add_column("#", style="bold")
        table.add_column("Model")
        for i, model in enumerate(available, 1):
            table.add_row(str(i), model)
        _console.print(table)

        while True:
            choice = Prompt.ask(
                f"Choose a model (default: {default_model})",
                default=default_model,
            )
            if choice in available:
                break
            _console.print(f"[yellow]'{choice}' is not in the list. Choose from: {available}[/yellow]")

        user_config_path = self._data_dir / "user_config.yaml"
        ConfigLoader.init_user_config(user_config_path)
        ConfigLoader.save_user_config({"active_model": choice}, user_config_path)
        _console.print(f"[green]✓ Model set to '{choice}'.[/green]")

        if state and "steps" in state:
            state["steps"]["ai_model"]["selected_model"] = choice
            state["steps"]["ai_model"]["completed"] = True

    def _step_voice_sample_inner(self, state: Optional[dict] = None) -> None:
        """Optionally record a voice sample and clone it via ElevenLabs."""
        _console.print(Panel(
            "[bold]Voice Clone Setup (Optional)[/bold]\n\n"
            "[bold]Purpose[/bold]: Your voice will be cloned via ElevenLabs to power\n"
            "GURUJEE's autonomous call features in Phase 2.\n\n"
            "[bold]Retention[/bold]: The raw recording (30 seconds) is sent directly to\n"
            "ElevenLabs and deleted from your device immediately afterwards.\n\n"
            "[bold]Your right[/bold]: You can delete your voice clone at any time via\n"
            "Settings > Voice > Delete Voice Clone.\n\n"
            "This step is [bold]optional[/bold] — you can skip it and set up voice later.",
            title="Step 7: Voice Sample (Optional)",
        ))

        consent = Confirm.ask("I consent and want to record my voice now. Continue?")
        if not consent:
            _console.print("[yellow]Voice setup skipped.[/yellow]")
            if state and "steps" in state:
                state["steps"]["voice_sample"]["skipped"] = True
                state["steps"]["voice_sample"]["consent_given"] = False
            return

        sample_path = Path("/tmp/voice_sample.wav")
        _console.print("Recording 30 seconds of audio...")
        result = subprocess.run(
            ["termux-microphone-record", "-l", "30", "-f", str(sample_path)]
        )
        if result.returncode != 0 or not sample_path.exists():
            raise SetupStepError("recording_failed", "Could not record voice sample.")

        try:
            voice_id = self._upload_voice_sample(sample_path)
        except Exception:
            # Upload failed — delete the sample and re-raise; voice_id is never used.
            if sample_path.exists():
                sample_path.unlink()
            raise
        else:
            # Upload succeeded — delete the sample before proceeding to keystore.
            try:
                sample_path.unlink(missing_ok=True)
            except OSError as exc:
                raise SetupStepError(
                    "cleanup_failed",
                    f"Could not delete raw audio sample from device: {exc}",
                ) from exc

        ks_path = self._data_dir / "gurujee.keystore"
        pin = Prompt.ask("Re-enter PIN to store voice ID", password=True)
        from gurujee.keystore.keystore import Keystore
        ks = Keystore(ks_path, pin=pin)
        ks.unlock()
        ks.set("voice_id", voice_id)
        ks.lock()
        _console.print("[green]✓ Voice ID stored in keystore.[/green]")

        if state and "steps" in state:
            state["steps"]["voice_sample"]["consent_given"] = True

    def _step_daemons_inner(self, state: Optional[dict] = None) -> None:
        """Copy soul_identity template, init user_config, start daemon, write boot script."""
        # Copy soul_identity.yaml template to data/ if not already present
        template_path = Path("agents") / "soul_identity.yaml"
        runtime_path = self._data_dir / "soul_identity.yaml"
        if template_path.exists() and not runtime_path.exists():
            shutil.copy2(template_path, runtime_path)
            _console.print("[green]✓ Soul identity initialised.[/green]")

        # Init user_config.yaml with defaults if not present
        user_config_path = self._data_dir / "user_config.yaml"
        ConfigLoader.init_user_config(user_config_path)

        # Start daemon in background and poll until ready
        _console.print("Starting GURUJEE daemon...")
        self._start_daemon_background()
        ready = self._poll_daemon_ready(timeout=10)
        if not ready:
            _console.print("[yellow]Warning: daemon did not confirm ready in 10s.[/yellow]")

        # Write Termux:Boot script
        boot_dir = self._boot_script_path.parent
        boot_dir.mkdir(parents=True, exist_ok=True)
        install_dir = Path(os.getcwd()).resolve()
        script_content = (
            "#!/data/data/com.termux/files/usr/bin/bash\n"
            "sleep 5\n"
            "# shellcheck source=/dev/null\n"
            "source \"$HOME/.gurujee.env\" 2>/dev/null || true\n"
            f"cd '{install_dir}'\n"
            "python -m gurujee --headless >> data/boot.log 2>&1 &\n"
        )
        self._boot_script_path.write_text(script_content, encoding="utf-8")
        self._boot_script_path.chmod(
            self._boot_script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP
        )
        _console.print(f"[green]✓ Boot script written to {self._boot_script_path}[/green]")

    # ------------------------------------------------------------------ #
    # Helpers (overridable in tests)                                        #
    # ------------------------------------------------------------------ #

    def _upload_voice_sample(self, sample_path: Path) -> str:
        """Upload voice sample to ElevenLabs and return voice_id.

        Requires elevenlabs package. Raises SetupStepError on failure.
        """
        try:
            from elevenlabs.client import ElevenLabs  # type: ignore[import-untyped]
            client = ElevenLabs()
            with open(sample_path, "rb") as f:
                voice = client.voices.add(
                    name="GURUJEE User",
                    files=[f],
                )
            return str(voice.voice_id)
        except Exception as exc:
            raise SetupStepError("elevenlabs_failed", str(exc)) from exc

    def _start_daemon_background(self) -> None:
        """Start GatewayDaemon as a background asyncio task."""
        import threading

        def _run() -> None:
            import asyncio
            from gurujee.daemon.gateway_daemon import GatewayDaemon
            asyncio.run(GatewayDaemon().start())

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _poll_daemon_ready(self, timeout: int = 10) -> bool:
        """Poll until the boot log confirms agents started, or timeout expires."""
        import time
        boot_log = self._data_dir / "boot.log"
        deadline = time.time() + timeout
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as prog:
            prog.add_task("Waiting for agents...", total=None)
            while time.time() < deadline:
                time.sleep(0.5)
                if boot_log.exists():
                    try:
                        if "GatewayDaemon: started agent" in boot_log.read_text(encoding="utf-8"):
                            return True
                    except OSError:
                        pass
        return False
