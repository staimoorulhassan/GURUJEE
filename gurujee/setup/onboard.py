"""OpenClaw-style interactive onboarding wizard for GURUJEE.

Entry points:
  python -m gurujee --onboard   → OnboardWizard(show_welcome=True).run()
  python -m gurujee config      → OnboardWizard(show_welcome=False).run()

Flow (8 steps):
  1. Welcome         — branded Rich Panel (skipped when show_welcome=False)
  2. Provider        — numbered list from config/models.yaml + "Bring your own"
  3. Custom URL      — only for "__custom__": prompt for base URL
  4. API key         — hidden prompt; OAuth providers get a note instead
  5. Model           — numbered list for chosen provider + "Enter custom ID"
  6. Alias           — optional short name
  7. Context size    — pre-filled from YAML, user can override
  8. Save & launch   — writes keystore / user_config.yaml / gurujee.config.json
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from gurujee.config.loader import ConfigLoader

if TYPE_CHECKING:
    from gurujee.keystore.keystore import Keystore

logger = logging.getLogger(__name__)
_console = Console()

# Sentinel used when user picks "Bring your own endpoint"
_CUSTOM_PROVIDER = "__custom__"

# Providers where no machine-manageable API key exists (OAuth / gcloud)
_OAUTH_AUTH_TYPES = {"oauth", "gcloud-adc"}


class OnboardWizard:
    """Guides the user through AI provider + model selection and saves config."""

    def __init__(
        self,
        data_dir: Path | None = None,
        config_dir: Path | None = None,
        show_welcome: bool = True,
        keystore: "Keystore | None" = None,
    ) -> None:
        self._data_dir = Path(data_dir) if data_dir else Path("data")
        self._config_dir = Path(
            config_dir
            if config_dir is not None
            else os.environ.get("GURUJEE_CONFIG_DIR", "config")
        )
        self._show_welcome = show_welcome
        self._keystore: "Keystore | None" = keystore

    # ------------------------------------------------------------------ #
    # Public entry point                                                    #
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        """Run all steps sequentially."""
        self._data_dir.mkdir(parents=True, exist_ok=True)

        if self._show_welcome:
            self._step_welcome()

        providers = self._load_all_providers()

        # Step 2: Provider selection
        provider_key = self._step_provider_selection(providers)

        # Step 3: Custom URL (only for __custom__)
        base_url: str | None = None
        if provider_key == _CUSTOM_PROVIDER:
            base_url = self._step_custom_endpoint()
            provider_cfg: dict[str, Any] = {
                "label": base_url,
                "base_url": base_url,
                "auth_env": "CUSTOM_API_KEY",
                "models": [],
            }
        else:
            provider_cfg = providers[provider_key]

        # Step 4: API key
        api_key = self._step_api_key(provider_key, provider_cfg)

        # Step 5: Model selection
        model_id = self._step_model_selection(provider_cfg)

        # Step 6: Alias
        alias = self._step_alias(model_id)

        # Step 7: Context size
        context_size = self._step_context_size(provider_cfg, model_id)

        # Step 8: Save & launch
        auth_env: str | None = provider_cfg.get("auth_env") if provider_key != _CUSTOM_PROVIDER else "CUSTOM_API_KEY"
        self._step_save_and_launch(
            provider_key=provider_key,
            model_id=model_id,
            alias=alias,
            context_size=context_size,
            api_key=api_key,
            base_url=base_url,
            auth_env=auth_env,
        )

    # ------------------------------------------------------------------ #
    # Steps                                                                 #
    # ------------------------------------------------------------------ #

    def _step_welcome(self) -> None:
        """Display GURUJEE branding panel."""
        _console.print()
        _console.print(Panel(
            "[bold cyan]GURUJEE[/bold cyan] [white]— Your AI Companion[/white]\n\n"
            "Let's set up your AI model in a few quick steps.\n\n"
            "  • Pick a provider (30+ supported)\n"
            "  • Enter your API key (stored encrypted in your keystore)\n"
            "  • Choose a model and context size\n\n"
            "Run [bold]gurujee config[/bold] any time to reconfigure.",
            title="Welcome to GURUJEE",
            border_style="cyan",
            expand=False,
        ))
        _console.print()

    def _step_provider_selection(self, providers: dict[str, dict]) -> str:
        """Show numbered provider table; return provider_key or '__custom__'."""
        _console.rule("[bold]Step 1 — Choose your AI provider[/bold]")
        self._display_provider_table(providers)

        keys = list(providers.keys())
        total = len(keys)

        while True:
            raw = Prompt.ask(
                f"Provider number (1–{total + 1})",
                default="1",
            )
            try:
                choice = int(raw)
            except ValueError:
                _console.print("[yellow]Enter a number.[/yellow]")
                continue

            if choice == total + 1:
                return _CUSTOM_PROVIDER
            if 1 <= choice <= total:
                return keys[choice - 1]
            _console.print(f"[yellow]Enter a number between 1 and {total + 1}.[/yellow]")

    def _step_custom_endpoint(self) -> str:
        """Prompt for a custom base URL."""
        _console.rule("[bold]Step 2 — Custom endpoint URL[/bold]")
        _console.print(
            "Enter the base URL of your OpenAI-compatible endpoint.\n"
            "Example: [cyan]http://localhost:11434/v1[/cyan] (Ollama)\n"
        )
        while True:
            url = Prompt.ask("Base URL").strip()
            if url.startswith("http"):
                return url
            _console.print("[yellow]URL must start with http:// or https://[/yellow]")

    def _step_api_key(self, provider_key: str, provider_cfg: dict) -> str | None:
        """Prompt for API key; return None for OAuth/gcloud providers."""
        _console.rule("[bold]Step 3 — API key[/bold]")

        auth_type = provider_cfg.get("auth_type", "")
        if auth_type in _OAUTH_AUTH_TYPES:
            _console.print(Panel(
                f"[yellow]This provider uses [bold]{auth_type}[/bold] authentication.[/yellow]\n\n"
                "No API key can be stored here.\n"
                "Follow your provider's auth flow externally, then the model will be\n"
                "selected correctly when you run GURUJEE.",
                border_style="yellow",
                expand=False,
            ))
            return None

        # Show auth hint if present in catalogue
        auth_note: str = provider_cfg.get("auth_note", "")
        auth_url: str = provider_cfg.get("auth_url", "")
        label: str = provider_cfg.get("label", provider_key)

        if auth_url and not auth_note:
            auth_note = f"Get your key at: {auth_url}"

        if auth_note:
            _console.print(f"[dim]{auth_note}[/dim]")

        key = Prompt.ask(
            f"Enter your [bold]{label}[/bold] API key (press Enter to skip)",
            password=True,
            default="",
        ).strip()

        return key if key else None

    def _step_model_selection(self, provider_cfg: dict) -> str:
        """Show numbered model table; return model_id string."""
        _console.rule("[bold]Step 4 — Choose a model[/bold]")

        models: list[dict] = provider_cfg.get("models", [])
        dynamic_catalog: bool = bool(provider_cfg.get("dynamic_catalog"))

        if not models or dynamic_catalog:
            _console.print(
                "[dim]This provider uses a dynamic model catalogue "
                "(e.g. Ollama local models).[/dim]"
            )
            return Prompt.ask("Enter model ID").strip()

        self._display_model_table(models)
        total = len(models)

        while True:
            raw = Prompt.ask(f"Model number (1–{total + 1})", default="1")
            try:
                choice = int(raw)
            except ValueError:
                _console.print("[yellow]Enter a number.[/yellow]")
                continue

            if choice == total + 1:
                return Prompt.ask("Enter custom model ID").strip()
            if 1 <= choice <= total:
                return models[choice - 1]["id"]
            _console.print(f"[yellow]Enter 1–{total + 1}.[/yellow]")

    def _step_alias(self, model_id: str) -> str | None:
        """Optional alias (short name) for this model configuration."""
        _console.rule("[bold]Step 5 — Alias[/bold]")
        raw = Prompt.ask(
            f"Short alias for this model (press Enter to use '[cyan]{model_id}[/cyan]')",
            default=model_id,
        ).strip()
        return None if raw == model_id else raw

    def _step_context_size(self, provider_cfg: dict, model_id: str) -> int:
        """Prompt for context window size; pre-filled from YAML."""
        _console.rule("[bold]Step 6 — Context window size[/bold]")

        # Look up the model's ctx in the provider config
        default_ctx = 8192
        for m in provider_cfg.get("models", []):
            if m.get("id") == model_id:
                default_ctx = int(m.get("ctx", 8192))
                break
        # Also check ctx_recommended (e.g. Ollama)
        if provider_cfg.get("ctx_recommended"):
            default_ctx = int(provider_cfg["ctx_recommended"])

        _console.print(
            f"Context window: how many tokens the model can 'see' at once.\n"
            f"Larger = more memory usage. Recommended for this model: [cyan]{default_ctx:,}[/cyan]"
        )

        while True:
            raw = Prompt.ask(
                "Context size (tokens)",
                default=str(default_ctx),
            ).strip().replace(",", "")
            try:
                ctx = int(raw)
                if ctx > 0:
                    return ctx
            except ValueError:
                pass
            _console.print("[yellow]Enter a positive integer.[/yellow]")

    def _step_save_and_launch(
        self,
        provider_key: str,
        model_id: str,
        alias: str | None,
        context_size: int,
        api_key: str | None,
        base_url: str | None,
        auth_env: str | None,
    ) -> None:
        """Save API key to keystore and write config files."""
        _console.rule("[bold]Step 7 — Saving configuration[/bold]")

        # ── 1. Save API key to keystore ──────────────────────────────────
        if api_key and auth_env:
            try:
                ks = self._get_unlocked_keystore()
                ks.set(auth_env, api_key)
                ks.lock()
                _console.print(f"[green]✓[/green] API key stored in keystore (key: {auth_env})")
            except Exception as exc:  # noqa: BLE001
                _console.print(
                    f"[yellow]⚠ Could not save API key to keystore: {exc}\n"
                    f"  Add it later via Settings or re-run [bold]gurujee config[/bold].[/yellow]"
                )
        else:
            if not api_key:
                _console.print("[dim]  API key skipped.[/dim]")

        # ── 2. Write user_config.yaml (active_model for AIClient) ────────
        active_model = f"{provider_key}/{model_id}"
        user_config_path = self._data_dir / "user_config.yaml"
        ConfigLoader.save_user_config({"active_model": active_model}, user_config_path)
        _console.print(f"[green]✓[/green] Active model set to [cyan]{active_model}[/cyan]")

        # ── 3. Write gurujee.config.json ─────────────────────────────────
        json_config = {
            "model": {
                "provider": provider_key,
                "model_id": model_id,
                "alias": alias,
                "context_size": context_size,
                "base_url": base_url,
            },
            "ui": {
                "theme": "dark",
            },
        }
        json_config_path = self._data_dir / "gurujee.config.json"
        ConfigLoader.save_json_config(json_config, json_config_path)
        _console.print(f"[green]✓[/green] Config saved to [cyan]{json_config_path}[/cyan]")

        # ── 4. Summary panel ─────────────────────────────────────────────
        display_alias = alias or model_id
        _console.print()
        _console.print(Panel(
            f"[bold]Provider:[/bold]      {provider_key}\n"
            f"[bold]Model:[/bold]         {model_id}\n"
            f"[bold]Alias:[/bold]         {display_alias}\n"
            f"[bold]Context size:[/bold]  {context_size:,} tokens\n"
            + (f"[bold]Endpoint:[/bold]      {base_url}\n" if base_url else ""),
            title="[bold green]✓ GURUJEE configured[/bold green]",
            border_style="green",
            expand=False,
        ))
        _console.print()
        _console.print(
            "Run [bold cyan]gurujee[/bold cyan] to start your AI companion.\n"
            "Run [bold cyan]gurujee config[/bold cyan] any time to reconfigure."
        )
        _console.print()

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    def _load_all_providers(self) -> dict[str, dict]:
        """Return ordered dict of all providers: builtin first, then custom."""
        models_cfg = ConfigLoader.load_models(self._config_dir)
        providers: dict[str, dict] = {}
        for tier in ("builtin_providers", "custom_providers"):
            for key, cfg in models_cfg.get(tier, {}).items():
                if isinstance(cfg, dict):
                    providers[key] = cfg
        return providers

    def _get_unlocked_keystore(self) -> "Keystore":
        """Return an unlocked Keystore.

        If self._keystore was passed in (already unlocked), return it.
        Otherwise prompt for PIN and unlock/create the keystore.
        """
        from gurujee.keystore.keystore import Keystore, KeystoreError

        if self._keystore is not None and not self._keystore.is_locked():
            return self._keystore

        ks_path = self._data_dir / "gurujee.keystore"
        if not ks_path.exists():
            # No keystore yet — create one
            _console.print(Panel(
                "[bold]Keystore not found.[/bold]\n\n"
                "Create a 4–8 digit PIN to protect your credentials.\n"
                "This PIN is [bold red]never stored[/bold red]. If forgotten,\n"
                "the keystore must be wiped and credentials re-entered.",
                border_style="yellow",
                expand=False,
            ))
            for _ in range(3):
                pin = Prompt.ask("Create PIN (4–8 digits)", password=True)
                if not (4 <= len(pin) <= 8 and pin.isdigit()):
                    _console.print("[yellow]PIN must be 4–8 digits.[/yellow]")
                    continue
                confirm = Prompt.ask("Confirm PIN", password=True)
                if pin != confirm:
                    _console.print("[yellow]PINs do not match.[/yellow]")
                    continue
                ks = Keystore(ks_path, pin=pin)
                ks.unlock()
                return ks
            raise RuntimeError("Could not create keystore PIN after 3 attempts.")

        # Keystore exists — prompt for existing PIN
        ks = Keystore(ks_path, pin="")
        for attempt in range(3):
            pin = Prompt.ask(
                f"Enter keystore PIN (attempt {attempt + 1}/3)",
                password=True,
            )
            ks.set_pin(pin)
            try:
                ks.unlock()
                return ks
            except KeystoreError as exc:
                if exc.code == "locked_out":
                    _console.print(
                        f"[red]Too many wrong attempts — locked for {exc.lockout_seconds}s.[/red]"
                    )
                    raise
                _console.print(f"[red]Incorrect PIN.[/red] ({2 - attempt} attempt(s) remaining)")

        raise RuntimeError("Could not unlock keystore — too many wrong PIN attempts.")

    def _display_provider_table(self, providers: dict[str, dict]) -> None:
        """Render a Rich Table of all providers."""
        table = Table(show_header=True, show_lines=False, expand=False)
        table.add_column("#",        style="bold", width=4)
        table.add_column("Provider", min_width=28)
        table.add_column("Tier",     width=10)
        table.add_column("Auth",     width=14)

        builtin_keys = set()
        models_cfg = ConfigLoader.load_models(self._config_dir)
        for k in models_cfg.get("builtin_providers", {}):
            builtin_keys.add(k)

        for i, (key, cfg) in enumerate(providers.items(), 1):
            tier = "Built-in" if key in builtin_keys else "Custom"
            auth_type = cfg.get("auth_type", "")
            auth_env = cfg.get("auth_env", "")
            auth_url = cfg.get("auth_url", "")

            if auth_type in _OAUTH_AUTH_TYPES:
                auth_label = f"[dim]{auth_type}[/dim]"
            elif auth_url:
                auth_label = "[green]Free key[/green]"
            elif auth_env:
                auth_label = "API key"
            else:
                auth_label = "[dim]none[/dim]"

            label = cfg.get("label", key)
            table.add_row(str(i), label, tier, auth_label)

        # Last row: bring your own
        table.add_row(
            str(len(providers) + 1),
            "[dim]Bring your own endpoint[/dim]",
            "[dim]Custom[/dim]",
            "[dim]optional[/dim]",
        )

        _console.print(table)

    def _display_model_table(self, models: list[dict]) -> None:
        """Render a Rich Table of available models for a provider."""
        table = Table(show_header=True, show_lines=False, expand=False)
        table.add_column("#",       style="bold", width=4)
        table.add_column("Model ID",             min_width=28)
        table.add_column("Label",                min_width=20)
        table.add_column("Context",              width=12)
        table.add_column("Caps",                 min_width=18)

        for i, m in enumerate(models, 1):
            ctx = m.get("ctx", "")
            ctx_str = f"{int(ctx):,}" if ctx else ""
            caps = m.get("caps", [])
            caps_str = ", ".join(caps) if caps else ""
            table.add_row(str(i), m.get("id", ""), m.get("label", ""), ctx_str, caps_str)

        table.add_row(
            str(len(models) + 1),
            "[dim]Custom model ID[/dim]",
            "", "", "",
        )

        _console.print(table)
