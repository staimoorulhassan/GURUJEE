"""Tests for install.sh — covers the native-package bootstrap approach.

install.sh uses Termux pkg for native extensions instead of compiling from source:
  pkg install -y libffi openssl python-cryptography clang make

This avoids Rust compilation failures on AArch64/Android where the cryptography
PyPI wheel cannot be built from source.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
INSTALL_SH = REPO_ROOT / "install.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _script_lines() -> list[str]:
    """Return all lines of install.sh."""
    return INSTALL_SH.read_text(encoding="utf-8").splitlines()


def _script_text() -> str:
    return INSTALL_SH.read_text(encoding="utf-8")


def _bash(script: str, env: dict | None = None) -> subprocess.CompletedProcess:
    import os
    merged = {**os.environ, **(env or {})}
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=merged,
    )


# ---------------------------------------------------------------------------
# Tests: base package install line
# ---------------------------------------------------------------------------

class TestBasePackageInstallLine:
    """Verifies the base pkg install line (python + git only)."""

    def test_base_install_line_contains_python_and_git(self):
        """Base install line must include python and git."""
        text = _script_text()
        assert "pkg install -y python git" in text

    def test_base_install_line_does_not_include_rust(self):
        """rust must NOT appear on the base install line."""
        for line in _script_lines():
            stripped = line.strip()
            if stripped.startswith("pkg install -y python"):
                assert "rust" not in stripped, (
                    f"rust must not be in the base install line; got: {stripped!r}"
                )

    def test_base_install_line_exact_content(self):
        """The base install line must be exactly `pkg install -y python git`."""
        found = False
        for line in _script_lines():
            stripped = line.strip()
            if stripped == "pkg install -y python git":
                found = True
                break
        assert found, (
            "Expected to find exactly `pkg install -y python git` "
            "in install.sh; available lines:\n"
            + "\n".join(line for line in _script_lines() if "pkg install" in line)
        )

    def test_no_python_git_rust_line_exists(self):
        """The old `pkg install -y python git rust` line must not exist."""
        for line in _script_lines():
            stripped = line.strip()
            assert stripped != "pkg install -y python git rust", (
                "Found obsolete line `pkg install -y python git rust` — "
                "rust should not be installed this way."
            )


# ---------------------------------------------------------------------------
# Tests: native package bootstrap line
# ---------------------------------------------------------------------------

class TestNativePackageInstallLine:
    """Verifies that native packages are installed via Termux pkg."""

    def test_cryptography_installed_via_pkg(self):
        """python-cryptography must be installed via pkg (not compiled from pip)."""
        text = _script_text()
        assert "python-cryptography" in text, (
            "cryptography must be installed via pkg to avoid Rust compilation on AArch64/Android"
        )

    def test_native_install_line_present(self):
        """The native package install line must be present."""
        text = _script_text()
        assert "pkg install -y libffi openssl python-cryptography clang make" in text

    def test_rust_not_installed_via_pkg(self):
        """rust must NOT be installed via pkg install (compilation avoided)."""
        for line in _script_lines():
            stripped = line.strip()
            if stripped.startswith("pkg install") and "rust" in stripped:
                pytest.fail(
                    f"Found `rust` on a pkg install line — use python-cryptography instead: {stripped!r}"
                )

    def test_cargo_version_check_not_present(self):
        """cargo --version must not be in install.sh (no Rust toolchain installed)."""
        assert "cargo --version" not in _script_text(), (
            "cargo --version check must be removed now that Rust is not installed"
        )


# ---------------------------------------------------------------------------
# Tests: install ordering
# ---------------------------------------------------------------------------

class TestInstallOrdering:
    """Verifies that native packages are installed before pip install."""

    def _line_number(self, substring: str) -> int:
        for i, line in enumerate(_script_lines()):
            if substring in line:
                return i
        return -1

    def test_base_packages_before_native_packages(self):
        """pkg install python git must appear before the native package line."""
        base_idx = self._line_number("pkg install -y python git")
        native_idx = self._line_number("python-cryptography")
        assert base_idx != -1, "Base install line not found"
        assert native_idx != -1, "Native package install line not found"
        assert base_idx < native_idx, (
            f"Base packages (line {base_idx}) should come before "
            f"native packages (line {native_idx})"
        )

    def test_native_packages_before_pip_install(self):
        """Native pkg install must appear before pip install -r requirements.txt."""
        native_idx = self._line_number("python-cryptography")
        pip_idx = self._line_number("pip install -r")
        assert native_idx != -1, "Native package install line not found"
        assert pip_idx != -1, "pip install -r line not found"
        assert native_idx < pip_idx, (
            f"Native packages (line {native_idx}) should come before "
            f"pip install (line {pip_idx})"
        )


# ---------------------------------------------------------------------------
# Tests: static syntax / shell validity
# ---------------------------------------------------------------------------

class TestShellSyntax:
    """Verify install.sh passes bash syntax check."""

    def test_bash_syntax_valid(self):
        """`bash -n install.sh` must exit 0 (no syntax errors)."""
        result = _bash(f"bash -n '{INSTALL_SH}'")
        assert result.returncode == 0, (
            f"install.sh has syntax errors:\n{result.stderr}"
        )

    def test_script_is_executable_or_readable(self):
        """install.sh must exist and be readable."""
        assert INSTALL_SH.exists(), "install.sh not found"
        assert INSTALL_SH.stat().st_size > 0, "install.sh is empty"

    def test_shebang_targets_bash(self):
        """install.sh must start with a bash shebang."""
        first_line = _script_lines()[0]
        assert first_line.startswith("#!"), "Missing shebang"
        assert "bash" in first_line, f"Shebang does not target bash: {first_line!r}"

    def test_set_euo_pipefail_present(self):
        """install.sh must use `set -euo pipefail` for strict error handling."""
        assert "set -euo pipefail" in _script_text(), (
            "install.sh should use `set -euo pipefail`"
        )


# ---------------------------------------------------------------------------
# Tests: regression — surrounding code unchanged
# ---------------------------------------------------------------------------

class TestRegressionBaseSetup:
    """Regression tests to ensure surrounding code was not accidentally modified."""

    def test_pkg_update_present(self):
        """pkg update -y must still be present."""
        assert "pkg update -y" in _script_text()

    def test_pkg_upgrade_present(self):
        """pkg upgrade -y must still be present."""
        assert "pkg upgrade -y" in _script_text()

    def test_install_section_comment_still_present(self):
        """Section comment for base packages must still be present."""
        assert "Update and install base packages" in _script_text()

    def test_native_package_comment_present(self):
        """Section comment explaining the native package approach must be present."""
        assert "cryptography ships no AArch64-Android wheel" in _script_text()

    def test_pip_install_requirements_still_present(self):
        """pip install -r requirements.txt must still be present."""
        assert "pip install -r" in _script_text()
