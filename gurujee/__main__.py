"""Entry point for GURUJEE.

Usage:
  python -m gurujee                # TUI + daemon (normal mode)
  python -m gurujee --setup        # run guided setup wizard
  python -m gurujee --headless     # daemon only (Termux:Boot)
  python -m gurujee --start        # start daemon headless (alias)
  python -m gurujee --tui          # start with Textual TUI
  python -m gurujee --status       # print agent status and exit
  python -m gurujee --logs         # tail data/gateway.log
  python -m gurujee --restart      # restart daemon
  python -m gurujee --reset        # re-run guided setup (alias for --setup)
  python -m gurujee.setup          # guided setup wizard directly
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
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
    parser.add_argument("--setup", action="store_true", help="Run guided setup wizard")
    parser.add_argument("--headless", action="store_true", help="Run daemon without TUI")
    parser.add_argument("--start", action="store_true", help="Start daemon headless (alias for --headless)")
    parser.add_argument("--tui", action="store_true", help="Start with Textual TUI")
    parser.add_argument("--status", action="store_true", help="Print agent status and exit")
    parser.add_argument("--logs", action="store_true", help="Tail data/gateway.log")
    parser.add_argument("--restart", action="store_true", help="Restart daemon")
    parser.add_argument("--reset", action="store_true", help="Re-run guided setup (alias for --setup)")
    args = parser.parse_args()

    _setup_logging()

    data_dir = Path(os.environ.get("GURUJEE_DATA_DIR", "data"))
    setup_state_path = data_dir / "setup_state.yaml"
    keystore_path = data_dir / "gurujee.keystore"

    # --status: print agent status and exit
    if args.status:
        _print_status(data_dir)
        sys.exit(0)

    # --logs: tail gateway.log
    if args.logs:
        _tail_logs(data_dir)
        sys.exit(0)

    # Determine mode FIRST so headless always wins over the setup check.
    headless_mode = args.headless or args.start
    tui_mode = args.tui

    # --restart: kill existing daemon process then fall through to start
    if args.restart:
        _restart_daemon(data_dir)
        sys.exit(0)

    # --setup / --reset: run guided setup wizard.
    # SKIP this check in headless mode — the daemon must start regardless of
    # whether setup_state.yaml exists (e.g. Termux:Boot, nohup from install.sh).
    is_first_run = _is_first_run(setup_state_path)
    if (is_first_run or args.setup or args.reset) and not headless_mode:
        from gurujee.setup.wizard import SetupWizard
        SetupWizard(data_dir=data_dir).run()
        sys.exit(0)

    if headless_mode:
        os.environ["GURUJEE_HEADLESS"] = "1"
        # Skip PIN prompt when stdin is not a terminal (e.g. Termux:Boot auto-start).
        # API keys come from ~/.gurujee.env sourced by the boot script.
        if not sys.stdin.isatty():
            keystore = None
        else:
            keystore = _prompt_pin(keystore_path, data_dir)

        from gurujee.daemon.gateway_daemon import GatewayDaemon
        from gurujee.server.app import create_app
        import uvicorn

        async def _run_headless() -> None:
            gateway = GatewayDaemon(keystore=keystore)
            app = create_app(gateway)
            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=7171,
                log_level="warning",
                loop="asyncio",
            )
            server = uvicorn.Server(config)
            await asyncio.gather(gateway.start(), server.serve())

        asyncio.run(_run_headless())
    else:
        # TUI / default: PIN prompt required for interactive use
        keystore = _prompt_pin(keystore_path, data_dir)
        if tui_mode:
            from gurujee.tui.app import GurujeeApp
            GurujeeApp(keystore=keystore).run()
        else:
            # Default: TUI + daemon
            from gurujee.tui.app import GurujeeApp
            GurujeeApp(keystore=keystore).run()

    sys.exit(0)


# ------------------------------------------------------------------ #
# Helpers                                                               #
# ------------------------------------------------------------------ #

def _print_status(data_dir: Path) -> None:
    """Print a brief status summary of the GURUJEE agent."""
    setup_state_path = data_dir / "setup_state.yaml"
    boot_log = data_dir / "boot.log"

    if _is_first_run(setup_state_path):
        _console.print("[yellow]Status: setup not completed[/yellow]")
        return

    _console.print("[bold]GURUJEE Status[/bold]")
    _console.print(f"  Setup state : {setup_state_path}")
    if boot_log.exists():
        try:
            last_lines = boot_log.read_text(encoding="utf-8").strip().splitlines()[-5:]
            _console.print("  Last log entries:")
            for line in last_lines:
                _console.print(f"    {line}")
        except OSError:
            _console.print("  [yellow]Could not read boot log.[/yellow]")
    else:
        _console.print("  [yellow]No boot log found — daemon may not have started yet.[/yellow]")


def _tail_logs(data_dir: Path) -> None:
    """Tail data/gateway.log (falls back to boot.log if gateway.log absent)."""
    gateway_log = data_dir / "gateway.log"
    boot_log = data_dir / "boot.log"
    log_path = gateway_log if gateway_log.exists() else boot_log
    if not log_path.exists():
        _console.print(f"[yellow]No log file found at {log_path}[/yellow]")
        return
    try:
        subprocess.run(["tail", "-f", str(log_path)])
    except KeyboardInterrupt:
        pass


def _restart_daemon(data_dir: Path) -> None:
    """Best-effort restart: kill any running gurujee --headless process and advise re-run."""
    _console.print("[bold]Restarting GURUJEE daemon...[/bold]")
    try:
        result = subprocess.run(
            ["pkill", "-f", "python -m gurujee"],
            capture_output=True,
        )
        if result.returncode == 0:
            _console.print("[green]Existing daemon process terminated.[/green]")
        else:
            _console.print("[yellow]No running daemon found (or pkill unavailable).[/yellow]")
    except FileNotFoundError:
        _console.print("[yellow]pkill not available on this platform.[/yellow]")

    _console.print("To start the daemon again, run: python -m gurujee --headless")


def _is_first_run(setup_state_path: Path) -> bool:
    if not setup_state_path.exists():
        return True
    from gurujee.config.loader import ConfigLoader
    state = ConfigLoader.load_setup_state(setup_state_path)
    return not bool(state.get("completed_at"))


def _prompt_pin(
    keystore_path: Path,
    data_dir: Path,
    *,
    max_display_attempts: int = 6,
) -> "Keystore":
    """Prompt the user for their PIN and return an unlocked Keystore.

    Handles lockout display and the forgot-PIN wipe flow.
    """
    from gurujee.keystore.keystore import Keystore, KeystoreError

    # Single instance reused across all attempts so _attempt_count and
    # _lockout_until persist — recreating each iteration would reset them,
    # allowing unlimited brute-force attempts.
    ks = Keystore(keystore_path, pin="")
    attempts_shown = 0
    while attempts_shown < max_display_attempts:
        pin = Prompt.ask("🔐 Enter keystore PIN", password=True)
        ks.set_pin(pin)
        try:
            ks.unlock()
            return ks
        except KeystoreError as exc:
            if exc.code == "locked_out":
                _console.print(
                    f"[red]Too many wrong attempts. Locked for {exc.lockout_seconds}s.[/red]"
                )
                _show_forgot_pin(ks, keystore_path, data_dir)
                sys.exit(1)
            elif exc.code == "invalid_pin":
                attempts_shown += 1
                remaining = max_display_attempts - attempts_shown
                _console.print(f"[red]Incorrect PIN.[/red] ({remaining} attempts remaining)")
                if attempts_shown >= 3:
                    _show_forgot_pin(ks, keystore_path, data_dir)
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
