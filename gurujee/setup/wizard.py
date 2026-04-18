import os
import sys
import subprocess
import urllib.request
import hashlib
from typing import Dict, Any, Callable
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

console = Console()

class SetupStepError(Exception):
    def __init__(self, step: str, message: str):
        self.step = step
        self.message = message
        super().__init__(self.message)

class SetupWizard:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        # Resolve the project root dynamically based on this file's location
        # wizard.py is in gurujee/setup/ -> project root is 2 levels up
        self.project_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", ".."
        ))
        self.steps = [
            "welcome",
            "packages",
            "accessibility_apk",
            "ai_model"
        ]

    def run(self):
        state = {}
        try:
            self._execute_steps(state)
            console.print("[bold green]✅ Setup completed successfully![/bold green]")
        except SetupStepError as e:
            console.print(f"[bold red]Step '{e.step}' failed: {e.message}[/bold red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
            sys.exit(1)

    def _execute_steps(self, state: Dict[str, Any]):
        step_fns: Dict[str, Callable] = {
            "welcome": self._step_welcome,
            "packages": self._step_packages_inner,
            "accessibility_apk": self._step_accessibility_apk_inner,
            "ai_model": self._step_ai_model_inner
        }

        for step_name in self.steps:
            fn = step_fns.get(step_name)
            if fn:
                fn(state)

    def _step_welcome(self, state: Dict[str, Any]):
        console.print(Panel("GURUJEE Setup Wizard", expand=False))
        console.print("Welcome! This wizard will configure your environment.")

    def _step_packages_inner(self, state: Dict[str, Any]):
        console.print("────────────────── Step: packages ──────────────────")
        
        # 1. Update system packages
        subprocess.run(["pkg", "update", "-y"])
        subprocess.run(["pkg", "install", "python", "git", "-y"])

        # 2. Handle requirements.txt with absolute path
        req_path = os.path.join(self.project_root, "requirements.txt")
        
        if not os.path.exists(req_path):
            # Fallback check if user is running from a different install type
            req_path = "requirements.txt" 

        console.print(f"Installing dependencies from: {req_path}")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_path],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            console.print(f"[red]{result.stderr}[/red]")
            raise SetupStepError("packages", "pip install failed.")

    def _step_accessibility_apk_inner(self, state: Dict[str, Any]):
        console.print("────────────── Step: accessibility_apk ─────────────")
        # Update URL to your repository
        apk_url = "https://github.com/staimoorulhassan/GURUJEE/releases/latest/download/gurujee-accessibility.apk"
        apk_dest = os.path.join(self.data_dir, "gurujee-accessibility.apk")

        os.makedirs(self.data_dir, exist_ok=True)

        try:
            console.print(f"Downloading APK from: {apk_url}")
            urllib.request.urlretrieve(apk_url, apk_dest)
        except Exception as e:
            # For development, we might not have a release yet
            console.print(f"[yellow]Warning: Could not download APK (404). Skipping...[/yellow]")
            return

        console.print("[green]APK downloaded successfully.[/green]")

    def _step_ai_model_inner(self, state: Dict[str, Any]):
        console.print("──────────────── Step: ai_model ──────────────────")
        default_model = "nova-fast"
        choice = Prompt.ask(
            f"Choose a model",
            choices=["nova-fast", "gemini-fast", "mistral"],
            default=default_model
        )
        state["model"] = choice
        console.print(f"Selected model: [bold cyan]{choice}[/bold cyan]")
