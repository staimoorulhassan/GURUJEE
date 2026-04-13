"""Entry point for running the setup wizard as a module."""

from gurujee.setup.wizard import SetupWizard

if __name__ == "__main__":
    wizard = SetupWizard()
    wizard.run()
