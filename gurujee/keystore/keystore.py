"""AES-256-GCM keystore with PBKDF2-HMAC-SHA256 key derivation.

PIN lockout policy:
  3 wrong attempts → 30-second lockout (exponential backoff on further failures).
  Forgot-PIN path: call wipe() — deletes keystore file + device salt.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


_NONCE_SIZE = 12
_TAG_SIZE = 16
_PBKDF2_ITERATIONS = 480_000
_KEY_LEN = 32
_LOCKOUT_BASE_SECONDS = 30
_MAX_ATTEMPTS_BEFORE_LOCKOUT = 3


class KeystoreError(Exception):
    """Raised for all keystore-related errors."""

    def __init__(self, code: str, message: str = "", lockout_seconds: int = 0) -> None:
        super().__init__(message or code)
        self.code = code
        self.lockout_seconds = lockout_seconds


class Keystore:
    """AES-256-GCM encrypted key-value store.

    The user PIN is the sole input to key derivation and is never stored.
    """

    def __init__(self, path: Path, pin: str) -> None:
        self._path = Path(path)
        self._pin = pin
        self._key: Optional[bytearray] = None
        self._attempt_count: int = 0
        self._lockout_until: float = 0.0

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    def set_pin(self, pin: str) -> None:
        """Update the PIN used for the next unlock() call.

        Does NOT reset lockout state — the same instance must be reused across
        attempts so that _attempt_count and _lockout_until are preserved.
        """
        self._pin = pin

    def unlock(self) -> None:
        """Derive key from PIN + device salt and verify by decrypting.

        Raises KeystoreError("locked_out") if still in lockout window.
        Raises KeystoreError("invalid_pin") if PIN is wrong.
        Raises KeystoreError("corrupt") if the file cannot be parsed.
        Creates an empty keystore if the file does not yet exist.
        """
        self._check_lockout()
        salt = self._get_salt()
        key = self._derive_key(self._pin.encode(), salt)

        if self._path.exists():
            try:
                self._decrypt_all(key)
            except KeystoreError as exc:
                if exc.code == "invalid_pin":
                    self._record_failed_attempt()
                raise
            except (ValueError, KeyError, json.JSONDecodeError):
                self._record_failed_attempt()
                raise KeystoreError("invalid_pin", "Incorrect PIN.")
        else:
            # New keystore — initialise with empty entries
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._encrypt_and_write({}, key)

        self._key = bytearray(key)
        self._attempt_count = 0
        self._lockout_until = 0.0

    def get(self, key: str) -> Optional[str]:
        """Return the stored value for *key*, or None if not present."""
        data = self._load_decrypted()
        return data.get(key)

    def set(self, key: str, value: str) -> None:
        """Store *value* under *key*."""
        data = self._load_decrypted()
        data[key] = value
        self._encrypt_and_write(data, bytes(self._key))  # type: ignore[arg-type]

    def delete(self, key: str) -> None:
        """Remove *key* from the keystore (no-op if absent)."""
        data = self._load_decrypted()
        data.pop(key, None)
        self._encrypt_and_write(data, bytes(self._key))  # type: ignore[arg-type]

    def lock(self) -> None:
        """Zero the in-memory key and mark the store as locked."""
        if self._key is not None:
            for i in range(len(self._key)):
                self._key[i] = 0
            self._key = None

    def is_locked(self) -> bool:
        """Return True if the keystore key is not loaded."""
        return self._key is None

    def wipe(self) -> None:
        """Delete keystore file and device salt (forgot-PIN path).

        After calling this, the object is in an unusable state.
        """
        self.lock()
        if self._path.exists():
            self._path.unlink()
        salt_path = self._path.parent / ".device_salt"
        if salt_path.exists():
            salt_path.unlink()

    # ------------------------------------------------------------------ #
    # Internals                                                             #
    # ------------------------------------------------------------------ #

    def _check_lockout(self) -> None:
        remaining = self._lockout_until - time.time()
        if remaining > 0:
            secs = math.ceil(remaining)
            raise KeystoreError(
                "locked_out",
                f"Too many wrong attempts. Try again in {secs} seconds.",
                lockout_seconds=secs,
            )

    def _record_failed_attempt(self) -> None:
        self._attempt_count += 1
        if self._attempt_count >= _MAX_ATTEMPTS_BEFORE_LOCKOUT:
            extra = self._attempt_count - _MAX_ATTEMPTS_BEFORE_LOCKOUT
            duration = _LOCKOUT_BASE_SECONDS * (2 ** extra)
            self._lockout_until = time.time() + duration

    def _get_salt(self) -> bytes:
        """Return 16-byte salt derived from android_id, or from .device_salt file."""
        salt_path = self._path.parent / ".device_salt"
        try:
            result = subprocess.run(
                ["settings", "get", "secure", "android_id"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            android_id = result.stdout.strip()
            if android_id and android_id != "null":
                return hashlib.sha256(f"{android_id}:gurujee".encode()).digest()[:16]
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass

        # Fallback: persistent random salt stored in data/.device_salt
        if salt_path.exists():
            return salt_path.read_bytes()
        salt = os.urandom(16)
        salt_path.parent.mkdir(parents=True, exist_ok=True)
        salt_path.write_bytes(salt)
        return salt

    @staticmethod
    def _derive_key(pin_bytes: bytes, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=_KEY_LEN,
            salt=salt,
            iterations=_PBKDF2_ITERATIONS,
        )
        return kdf.derive(pin_bytes)

    def _load_decrypted(self) -> dict[str, str]:
        if self._key is None:
            raise KeystoreError("locked", "Keystore is locked. Call unlock() first.")
        return self._decrypt_all(bytes(self._key))

    def _decrypt_all(self, key: bytes) -> dict[str, str]:
        try:
            raw = self._path.read_bytes()
        except OSError as exc:
            raise KeystoreError("io_error", str(exc)) from exc

        if len(raw) < _NONCE_SIZE + _TAG_SIZE:
            raise KeystoreError("corrupt", "Keystore file is too small.")

        nonce = raw[:_NONCE_SIZE]
        ciphertext = raw[_NONCE_SIZE:]

        try:
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
        except InvalidTag as exc:
            raise KeystoreError("invalid_pin", "Decryption failed.") from exc

        try:
            return json.loads(plaintext.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise KeystoreError("corrupt", "Keystore payload is corrupt.") from exc

    def _encrypt_and_write(self, data: dict[str, str], key: bytes) -> None:
        plaintext = json.dumps(data).encode("utf-8")
        nonce = os.urandom(_NONCE_SIZE)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
        tmp_path = self._path.with_suffix(".tmp")
        try:
            tmp_path.write_bytes(nonce + ciphertext)
            os.replace(tmp_path, self._path)
        except OSError as exc:
            tmp_path.unlink(missing_ok=True)
            raise KeystoreError("io_error", str(exc)) from exc
