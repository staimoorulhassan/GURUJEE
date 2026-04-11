"""Entry point for GURUJEE.

Usage:
  python -m gurujee                # TUI + daemon (normal mode)
  python -m gurujee --headless     # daemon only (Termux:Boot)
  python -m gurujee --reset        # re-run guided setup
  python -m gurujee.setup          # guided setup wizard directly
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import NoReturn

from rich.console import Console
from rich.prompt import Confirm, Prompt

_console = Console()


def main() -> NoReturn:
    parser = argparse.ArgumentParser(prog="gurujee", description="GURUJEE AI companion")
    parser.add_argument("--headless", action="store_true", help="Run daemon without TUI")
    parser.add_argument("--reset", action="store_true", help="Re-run guided setup")
    args = parser.parse_args()

    _setup_logging()

    data_dir = Path(os.environ.get("GURUJEE_DATA_DIR", "data"))
    setup_state_path = data_dir / "setup_state.yaml"
    keystore_path = data_dir / "gurujee.keystore"

    # Detect first run: no setup_state.yaml or completed_at is null
    is_first_run = _is_first_run(setup_state_path)

    if is_first_run or args.reset:
        from gurujee.setup.wizard import SetupWizard
        SetupWizard(data_dir=data_dir).run()
        sys.exit(0)

    # Prompt for PIN before starting
    from gurujee.keystore.keystore import Keystore, KeystoreError

    keystore = Keystore(keystore_path, pin="")  # pin set by _prompt_pin
    _prompt_pin(keystore, keystore_path, data_dir)

    if args.headless:
        os.environ["GURUJEE_HEADLESS"] = "1"
        from gurujee.daemon.gateway_daemon import GatewayDaemon
        asyncio.run(GatewayDaemon(keystore=keystore).start())
    else:
        from gurujee.tui.app import GurujeeApp
        GurujeeApp(keystore=keystore).run()

    sys.exit(0)


# ------------------------------------------------------------------ #
# Helpers                                                               #
# ------------------------------------------------------------------ #

def _is_first_run(setup_state_path: Path) -> bool:
    if not setup_state_path.exists():
        return True
    from gurujee.config.loader import ConfigLoader
    state = ConfigLoader.load_setup_state(setup_state_path)
    return not bool(state.get("completed_at"))


def _prompt_pin(
    keystore: "Keystore",
    keystore_path: Path,
    data_dir: Path,
    *,
    max_display_attempts: int = 6,
) -> None:
    """Prompt the user for their PIN and unlock the keystore.

    Handles lockout display and the forgot-PIN wipe flow.
    """
    from gurujee.keystore.keystore import Keystore, KeystoreError

    attempts_shown = 0
    while attempts_shown < max_display_attempts:
        pin = Prompt.ask("🔐 Enter keystore PIN", password=True)
        # Rebuild Keystore with the entered PIN
        ks = Keystore(keystore_path, pin=pin)
        try:
            ks.unlock()
            # Copy key reference into the passed keystore object
            keystore._pin = pin
            keystore._key = ks._key
            keystore._path = ks._path
            return
        except KeystoreError as exc:
            if exc.code == "locked_out":
                _console.print(
                    f"[red]Too many wrong attempts. Locked for {exc.lockout_seconds}s.[/red]"
                )
                _show_forgot_pin(keystore, keystore_path, data_dir)
                return
            elif exc.code == "invalid_pin":
                attempts_shown += 1
                remaining = max_display_attempts - attempts_shown
                _console.print(f"[red]Incorrect PIN.[/red] ({remaining} attempts remaining)")
                if attempts_shown >= 3:
                    _show_forgot_pin(keystore, keystore_path, data_dir)
                    # Continue loop — user may have cancelled the wipe
            else:
                _console.print(f"[red]Keystore error: {exc}[/red]")
                sys.exit(1)

    _console.print("[red]Too many failed attempts.[/red]")
    sys.exit(1)


def _show_forgot_pin(keystore: "Keystore", keystore_path: Path, data_dir: Path) -> None:
    """Display the forgot-PIN warning and optionally wipe the keystore."""
    _console.print(
        "\n[bold yellow]Forgot PIN?[/bold yellow]\n"
        "Wiping the keystore will [bold red]permanently delete all stored credentials[/bold red]\n"
        "(ElevenLabs voice ID, SIP credentials). You will need to re-run guided setup\n"
        "and re-enter all credentials from scratch.\n"
    )
    if Confirm.ask("Wipe keystore and re-run setup?", default=False):
        keystore._path = keystore_path
        keystore.wipe()
        _console.print("[green]Keystore wiped.[/green]")
        from gurujee.setup.wizard import SetupWizard
        SetupWizard(data_dir=data_dir).run()
        sys.exit(0)


def _setup_logging() -> None:
    data_dir = Path(os.environ.get("GURUJEE_DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    log_level_name = os.environ.get("GURUJEE_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    handler = RotatingFileHandler(
        data_dir / "boot.log",
        maxBytes=5_242_880,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logging.basicConfig(level=log_level, handlers=[handler])


if __name__ == "__main__":
    main()
