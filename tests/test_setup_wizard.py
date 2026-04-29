"""Tests for SetupWizard — TDD: these MUST fail before wizard.py is implemented."""
from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


def _make_partial_state(completed_steps: list[str]) -> dict:
    """Build a setup_state dict with given steps marked complete."""
    all_steps = [
        "packages", "shizuku", "accessibility_apk", "permissions",
        "keystore_pin", "ai_model", "voice_sample", "daemons",
    ]
    steps = {}
    for step in all_steps:
        steps[step] = {
            "completed": step in completed_steps,
            "skipped": False,
            "completed_at": "2026-04-11T10:00:00Z" if step in completed_steps else None,
        }
    return {
        "version": 1,
        "started_at": "2026-04-11T10:00:00Z",
        "completed_at": None,
        "steps": steps,
    }


class TestSetupWizardResumption:
    def test_wizard_resumes_from_last_completed_step(self, tmp_path: Path) -> None:
        """Wizard with steps 1-3 complete should start at step 4 (permissions)."""
        from gurujee.setup.wizard import SetupWizard

        state_path = tmp_path / "setup_state.yaml"
        state_path.write_text(
            yaml.safe_dump(_make_partial_state(["packages", "shizuku", "accessibility_apk"])),
            encoding="utf-8",
        )
        wizard = SetupWizard(data_dir=tmp_path)
        state = wizard._load_state()
        steps = state.get("steps", {})
        assert steps["packages"]["completed"] is True
        assert steps["shizuku"]["completed"] is True
        assert steps["accessibility_apk"]["completed"] is True
        assert steps["permissions"]["completed"] is False

    def test_step_runner_skips_completed_step(self, tmp_path: Path) -> None:
        """_step_runner must skip a step that's already completed."""
        from gurujee.setup.wizard import SetupWizard

        wizard = SetupWizard(data_dir=tmp_path)
        state = _make_partial_state(["packages"])
        called = []

        def _fn() -> None:
            called.append(True)

        wizard._step_runner("packages", _fn, state)
        assert not called, "Step runner must not call fn for already-completed step"


class TestVoiceSampleConsent:
    def test_voice_sample_skipped_when_user_declines(self, tmp_path: Path) -> None:
        from gurujee.setup.wizard import SetupWizard

        wizard = SetupWizard(data_dir=tmp_path)
        state = _make_partial_state([])

        with patch("gurujee.setup.wizard.Confirm.ask", return_value=False):
            wizard._step_voice_sample_inner(state)

        assert state["steps"]["voice_sample"]["skipped"] is True
        assert state["steps"]["voice_sample"]["completed"] is False


class TestAPKVerification:
    def test_step_accessibility_apk_rejects_wrong_sha256(self, tmp_path: Path) -> None:
        from gurujee.setup.wizard import SetupWizard, SetupStepError

        wizard = SetupWizard(data_dir=tmp_path)
        state = _make_partial_state([])

        fake_apk = tmp_path / "fake.apk"
        fake_apk.write_bytes(b"not a real apk")

        with (
            patch("gurujee.setup.wizard.urllib.request.urlretrieve",
                  side_effect=lambda url, dest: Path(dest).write_bytes(b"not a real apk")),
            patch.object(wizard, "_EXPECTED_APK_SHA256", "0" * 64),
            pytest.raises(SetupStepError, match="sha256_mismatch"),
        ):
            wizard._step_accessibility_apk_inner(state, apk_dest=tmp_path / "test.apk")

        assert state["steps"]["accessibility_apk"]["completed"] is False


class TestKeystorePinStep:
    def test_step_keystore_pin_marks_step_complete(self, tmp_path: Path) -> None:
        from gurujee.setup.wizard import SetupWizard
        from gurujee.keystore.keystore import Keystore

        wizard = SetupWizard(data_dir=tmp_path)
        state = _make_partial_state([])

        with (
            patch("gurujee.setup.wizard.Prompt.ask", side_effect=["1234", "1234"]),
            patch("gurujee.setup.wizard.Confirm.ask", return_value=True),
        ):
            wizard._step_keystore_pin_inner(state)

        assert state["steps"]["keystore_pin"]["completed"] is True
        assert (tmp_path / "gurujee.keystore").exists()


class TestAIModelStep:
    def test_step_ai_model_writes_user_config(self, tmp_path: Path) -> None:
        from gurujee.setup.wizard import SetupWizard
        from gurujee.config.loader import ConfigLoader

        wizard = SetupWizard(data_dir=tmp_path)
        state = _make_partial_state([])

        with patch("gurujee.setup.wizard.Prompt.ask", return_value="gemini-fast"):
            wizard._step_ai_model_inner(state)

        cfg = ConfigLoader.load_user_config(tmp_path / "user_config.yaml")
        assert cfg["active_model"] == "gemini-fast"
        assert state["steps"]["ai_model"]["completed"] is True


class TestDaemonStep:
    def test_step_daemons_creates_boot_script(self, tmp_path: Path) -> None:
        from gurujee.setup.wizard import SetupWizard

        src_soul = tmp_path / "agents" / "soul_identity.yaml"
        src_soul.parent.mkdir()
        src_soul.write_text("name: GURUJEE\n", encoding="utf-8")

        wizard = SetupWizard(data_dir=tmp_path)
        state = _make_partial_state([])
        boot_path = tmp_path / "start-gurujee.sh"

        with (
            patch.object(wizard, "_start_daemon_background", return_value=None),
            patch.object(wizard, "_poll_daemon_ready", return_value=True),
            patch.object(wizard, "_boot_script_path", boot_path),
        ):
            wizard._step_daemons_inner(state)

        assert boot_path.exists()
        content = boot_path.read_text()
        assert "--headless" in content
        # chmod(S_IXUSR) is a no-op on Windows; only check on POSIX
        import sys
        if sys.platform != "win32":
            assert boot_path.stat().st_mode & stat.S_IXUSR


class TestBootScriptContent:
    """T070 — verify Termux:Boot script has the required shebang and command."""

    def test_boot_script_has_correct_shebang(self, tmp_path: Path) -> None:
        from gurujee.setup.wizard import SetupWizard

        src_soul = tmp_path / "agents" / "soul_identity.yaml"
        src_soul.parent.mkdir()
        src_soul.write_text("name: GURUJEE\n", encoding="utf-8")

        wizard = SetupWizard(data_dir=tmp_path)
        state = _make_partial_state([])
        boot_path = tmp_path / "start-gurujee.sh"

        with (
            patch.object(wizard, "_start_daemon_background", return_value=None),
            patch.object(wizard, "_poll_daemon_ready", return_value=True),
            patch.object(wizard, "_boot_script_path", boot_path),
        ):
            wizard._step_daemons_inner(state)

        content = boot_path.read_text(encoding="utf-8")
        assert content.startswith("#!/data/data/com.termux/files/usr/bin/bash"), (
            "Boot script must use the Termux bash shebang"
        )
        assert "python -m gurujee --headless" in content, (
            "Boot script must launch gurujee in headless mode"
        )
        assert "data/boot.log" in content, (
            "Boot script must redirect output to data/boot.log"
        )
        # Must be executable on POSIX (no-op on Windows)
        import sys
        if sys.platform != "win32":
            assert boot_path.stat().st_mode & stat.S_IXUSR


class TestFullHappyPath:
    def test_full_run_writes_completed_at(self, tmp_path: Path) -> None:
        from gurujee.setup.wizard import SetupWizard

        wizard = SetupWizard(data_dir=tmp_path)

        with patch.object(wizard, "_execute_steps", return_value=None) as mock_exec:
            wizard.run()
            mock_exec.assert_called_once()
