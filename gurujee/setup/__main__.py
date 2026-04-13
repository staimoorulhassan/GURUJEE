"""Entry point for running the setup wizard as a module.

Usage:
  python -m gurujee.setup
"""

from gurujee.setup.wizard import SetupWizard


def main() -> None:
    """Start the guided setup wizard."""
    SetupWizard().run()


if __name__ == "__main__":
    main()
