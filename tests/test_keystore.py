"""Tests for Keystore — TDD: these MUST fail before keystore.py behaviour is verified."""
from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from gurujee.keystore.keystore import Keystore, KeystoreError

TEST_PIN = "1234"


def _make_keystore(tmp_path: Path, pin: str = TEST_PIN) -> Keystore:
    """Create a Keystore backed by a fixed device salt at tmp_path."""
    salt_path = tmp_path / ".device_salt"
    if not salt_path.exists():
        salt_path.write_bytes(os.urandom(16))
    ks_path = tmp_path / "test.keystore"
    ks = Keystore(ks_path, pin=pin)

    import types

    def _patched_get_salt(self: Keystore) -> bytes:
        return salt_path.read_bytes()

    ks._get_salt = types.MethodType(_patched_get_salt, ks)  # type: ignore[method-assign]
    return ks


class TestRoundTrip:
    def test_unlock_set_get_lock_unlock_get(self, tmp_path: Path) -> None:
        ks = _make_keystore(tmp_path)
        ks.unlock()
        ks.set("voice_id", "voice_abc123")
        ks.lock()

        ks2 = _make_keystore(tmp_path)
        ks2.unlock()
        assert ks2.get("voice_id") == "voice_abc123"

    def test_delete_removes_key(self, tmp_path: Path) -> None:
        ks = _make_keystore(tmp_path)
        ks.unlock()
        ks.set("foo", "bar")
        ks.delete("foo")
        assert ks.get("foo") is None

    def test_get_missing_key_returns_none(self, tmp_path: Path) -> None:
        ks = _make_keystore(tmp_path)
        ks.unlock()
        assert ks.get("nonexistent") is None


class TestWrongPin:
    def test_wrong_pin_raises_invalid_pin(self, tmp_path: Path) -> None:
        ks = _make_keystore(tmp_path)
        ks.unlock()
        ks.set("x", "y")
        ks.lock()

        ks_bad = _make_keystore(tmp_path, pin="9999")
        with pytest.raises(KeystoreError) as exc_info:
            ks_bad.unlock()
        assert exc_info.value.code == "invalid_pin"

    def test_three_wrong_attempts_trigger_lockout(self, tmp_path: Path) -> None:
        ks = _make_keystore(tmp_path)
        ks.unlock()
        ks.lock()

        ks_bad = _make_keystore(tmp_path, pin="0000")
        for _ in range(3):
            try:
                ks_bad.unlock()
            except KeystoreError:
                pass

        with pytest.raises(KeystoreError) as exc_info:
            ks_bad.unlock()
        assert exc_info.value.code == "locked_out"
        assert exc_info.value.lockout_seconds >= 30

    def test_lockout_duration_is_at_least_30_seconds(self, tmp_path: Path) -> None:
        ks = _make_keystore(tmp_path)
        ks.unlock()
        ks.lock()

        ks_bad = _make_keystore(tmp_path, pin="0000")
        for _ in range(3):
            try:
                ks_bad.unlock()
            except KeystoreError:
                pass

        try:
            ks_bad.unlock()
        except KeystoreError as exc:
            assert exc.lockout_seconds >= 30


class TestLockState:
    def test_lock_prevents_get(self, tmp_path: Path) -> None:
        ks = _make_keystore(tmp_path)
        ks.unlock()
        ks.lock()
        with pytest.raises(KeystoreError) as exc_info:
            ks.get("key")
        assert exc_info.value.code == "locked"

    def test_is_locked_reflects_state(self, tmp_path: Path) -> None:
        ks = _make_keystore(tmp_path)
        assert ks.is_locked()
        ks.unlock()
        assert not ks.is_locked()
        ks.lock()
        assert ks.is_locked()


class TestWipe:
    def test_wipe_deletes_keystore_file(self, tmp_path: Path) -> None:
        ks = _make_keystore(tmp_path)
        ks.unlock()
        assert ks._path.exists()
        ks.wipe()
        assert not ks._path.exists()

    def test_wipe_deletes_device_salt(self, tmp_path: Path) -> None:
        salt_path = tmp_path / ".device_salt"
        ks = _make_keystore(tmp_path)
        ks.unlock()
        ks.wipe()
        assert not salt_path.exists()


class TestDeviceSaltFallback:
    def test_android_id_unavailable_falls_back_to_device_salt(self, tmp_path: Path) -> None:
        """When 'settings get secure android_id' fails, a .device_salt file is used."""
        ks_path = tmp_path / "test.keystore"

        with patch("subprocess.run", side_effect=FileNotFoundError):
            ks = Keystore(ks_path, pin=TEST_PIN)
            ks.unlock()
            ks.set("test", "value")
            ks.lock()

            ks2 = Keystore(ks_path, pin=TEST_PIN)
            ks2.unlock()
            assert ks2.get("test") == "value"

        assert (tmp_path / ".device_salt").exists()


class TestCorruptFile:
    def test_corrupt_file_raises_corrupt(self, tmp_path: Path) -> None:
        ks_path = tmp_path / "corrupt.keystore"
        ks_path.write_bytes(b"\x00" * 30)  # too small / wrong format

        ks = Keystore(ks_path, pin=TEST_PIN)
        salt_path = tmp_path / ".device_salt"
        salt_path.write_bytes(os.urandom(16))

        import types

        def _patched_get_salt(self: Keystore) -> bytes:
            return salt_path.read_bytes()

        ks._get_salt = types.MethodType(_patched_get_salt, ks)  # type: ignore[method-assign]

        with pytest.raises(KeystoreError) as exc_info:
            ks.unlock()
        assert exc_info.value.code in ("invalid_pin", "corrupt")


class TestAtomicWrite:
    def test_partial_write_does_not_corrupt_existing(self, tmp_path: Path) -> None:
        """If the write crashes mid-way, the original file is intact."""
        ks = _make_keystore(tmp_path)
        ks.unlock()
        ks.set("key1", "value1")

        original_bytes = ks._path.read_bytes()

        # Simulate write failure by making os.replace fail
        with patch("os.replace", side_effect=OSError("disk full")):
            try:
                ks.set("key2", "value2")
            except KeystoreError:
                pass

        assert ks._path.read_bytes() == original_bytes
