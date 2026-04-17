# Contributing to GURUJEE

Thank you for your interest in contributing to GURUJEE!

## Project Overview

GURUJEE is an autonomous AI agent Android application designed to run on non-rooted phones via Termux. It features a split-layer architecture:
- **Daemon**: A Python-based backend running in Termux that handles the AI logic, automation, and local API.
- **Launcher**: A Kivy/KivyMD-based Android APK that provides the UI and manages the daemon lifecycle.

## Codebase Structure

- `gurujee/`: Core Python package for the daemon and agent logic.
- `launcher/`: Kivy source code and `buildozer.spec` for the Android APK.
- `specs/`: Project specifications and task tracking.
- `config/`: Default configurations (models, security).

## Development Guidelines

- **Python**: Follow PEP 8. Use type hints where possible.
- **Kivy**: Use KivyMD for modern UI components. Keep the UI thread responsive.
- **Security**: Be mindful of API key handling. Never hardcode secrets.
- **Testing**: Add tests for new features in the `tests/` directory.

## Build Process

- Local Windows builds are not supported for the APK.
- APK builds are handled via GitHub Actions when a new version tag (e.g., `v1.0.18-fix`) is pushed.

## How to Contribute

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and ensure tests pass.
4. Submit a Pull Request.

## Security Policies

- Network requests are governed by a dynamic allowlist in `config/security.yaml`.
- Keystore uses AES-256-GCM with PBKDF2-HMAC-SHA256 (600,000 iterations).
