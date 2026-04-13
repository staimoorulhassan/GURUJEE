"""Tests for install.sh — covers the changes introduced in this PR.

PR change: removed `rust` from the base package install line:
  Before: pkg install -y python git rust
  After:  pkg install -y python git

Rust is still installed via the dedicated toolchain line:
  pkg install -y rust binutils clang make
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
# Tests: base package install line (changed in this PR)
# ---------------------------------------------------------------------------

class TestBasePackageInstallLine:
    """Verifies the base pkg install line after removing the duplicate rust."""

    def test_base_install_line_contains_python_and_git(self):
        """Base install line must include python and git."""
        text = _script_text()
        assert "pkg install -y python git" in text

    def test_base_install_line_does_not_include_rust(self):
        """rust must NOT appear on the base install line (it was duplicated before the PR)."""
        for line in _script_lines():
            stripped = line.strip()
            # Only check the base install line, not the toolchain line
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
            f"in install.sh; available lines:\n"
            + "\n".join(l for l in _script_lines() if "pkg install" in l)
        )

    def test_no_python_git_rust_line_exists(self):
        """The old `pkg install -y python git rust` line must not exist."""
        for line in _script_lines():
            stripped = line.strip()
            assert stripped != "pkg install -y python git rust", (
                "Found obsolete line `pkg install -y python git rust` — "
                "rust should only be installed via the dedicated toolchain line."
            )


# ---------------------------------------------------------------------------
# Tests: dedicated Rust toolchain line (must still be present)
# ---------------------------------------------------------------------------

class TestRustToolchainInstallLine:
    """Verifies that the dedicated Rust toolchain install line is still present."""

    def test_rust_toolchain_line_present(self):
        """pkg install -y rust binutils clang make must still exist."""
        assert "pkg install -y rust binutils clang make" in _script_text(), (
            "Dedicated Rust toolchain install line must remain in install.sh"
        )

    def test_rust_installed_exactly_once(self):
        """rust must appear on exactly one pkg install line."""
        rust_install_lines = [
            line.strip()
            for line in _script_lines()
            if line.strip().startswith("pkg install") and "rust" in line
        ]
        assert len(rust_install_lines) == 1, (
            f"Expected rust to appear on exactly one pkg install line; "
            f"found {len(rust_install_lines)}: {rust_install_lines}"
        )

    def test_rust_toolchain_line_includes_binutils_clang_make(self):
        """The toolchain install line must include the full set of build tools."""
        line = "pkg install -y rust binutils clang make"
        assert line in _script_text()

    def test_cargo_version_check_present(self):
        """install.sh must verify Rust by running `cargo --version`."""
        assert "cargo --version" in _script_text(), (
            "Rust version check (`cargo --version`) must remain after install"
        )


# ---------------------------------------------------------------------------
# Tests: ordering — rust toolchain installed after base packages
# ---------------------------------------------------------------------------

class TestInstallOrdering:
    """Verifies that base packages come before the Rust toolchain line."""

    def _line_number(self, substring: str) -> int:
        for i, line in enumerate(_script_lines()):
            if substring in line:
                return i
        return -1

    def test_base_packages_before_rust_toolchain(self):
        """pkg install python git must appear before pkg install rust."""
        base_idx = self._line_number("pkg install -y python git")
        rust_idx = self._line_number("pkg install -y rust binutils clang make")
        assert base_idx != -1, "Base install line not found"
        assert rust_idx != -1, "Rust toolchain install line not found"
        assert base_idx < rust_idx, (
            f"Base packages (line {base_idx}) should come before "
            f"Rust toolchain (line {rust_idx})"
        )

    def test_cargo_check_after_rust_install(self):
        """cargo --version check must appear after the Rust toolchain install."""
        rust_idx = self._line_number("pkg install -y rust binutils clang make")
        cargo_idx = self._line_number("cargo --version")
        assert rust_idx != -1, "Rust toolchain install line not found"
        assert cargo_idx != -1, "cargo --version check not found"
        assert cargo_idx > rust_idx, (
            f"cargo --version check (line {cargo_idx}) must come after "
            f"Rust install (line {rust_idx})"
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
# Tests: regression — pkg update/upgrade still present
# ---------------------------------------------------------------------------

class TestRegressionBaseSetup:
    """Regression tests to ensure surrounding code was not accidentally modified."""

    def test_pkg_update_upgrade_still_present(self):
        """pkg update -y && pkg upgrade -y must still precede package installs."""
        assert "pkg update -y && pkg upgrade -y" in _script_text()

    def test_install_section_comment_still_present(self):
        """Section comment for base packages must still be present."""
        assert "Update and install base packages" in _script_text()

    def test_rust_toolchain_comment_still_present(self):
        """Section comment for Rust toolchain install must still be present."""
        assert "Install Rust toolchain for Python packages requiring compilation" in _script_text()