# Keystore Module API Contract

**Branch**: `001-gurujee-foundation` | **Date**: 2026-04-11

The `Keystore` class in `gurujee/keystore/keystore.py` is a module (not an agent).
Any code that needs a secret calls `Keystore` directly; secrets are NEVER passed over
the message bus.

---

## Class: `Keystore`

```python
class Keystore:
    def __init__(self, path: Path, pin: str) -> None: ...
```

`path`: absolute path to `data/gurujee.keystore`
`pin`: user PIN from guided setup (cleared from memory immediately after key derivation)

---

## Methods

### `unlock(pin: str) -> None`

Derives the AES-256 key from `PBKDF2-HMAC-SHA256(pin + device_fingerprint_salt)` and
stores it in a `SecretKey` wrapper in process memory. Clears `pin` from local scope.

**Raises**: `KeystoreError("invalid_pin")` if decryption MAC fails.

---

### `get(key: str) -> str | None`

Returns the plaintext value for `key`, or `None` if not found.

**Raises**: `KeystoreError("locked")` if not yet unlocked.

```python
voice_id = keystore.get("voice_id")
```

---

### `set(key: str, value: str) -> None`

Encrypts and persists `value` under `key`. Re-encrypts entire blob atomically
(write to temp file, then `os.replace`).

**Raises**: `KeystoreError("locked")` if not unlocked.

---

### `delete(key: str) -> None`

Removes `key` from the keystore blob. No-op if key does not exist.

---

### `lock() -> None`

Zeroes the in-memory key bytes and clears the reference.

---

### `is_locked() -> bool`

Returns `True` if the derived key is not currently in memory.

---

## On-Disk Format

```
[12 bytes: GCM nonce]
[N bytes: GCM ciphertext of JSON payload]
[16 bytes: GCM authentication tag]
```

The JSON payload structure (decrypted, in-memory only):
```json
{
  "v": 1,
  "entries": {
    "voice_id": "EL_VOICE_ID_STRING_OR_NULL",
    "elevenlabs_api_key": "KEY_OR_NULL",
    "sip_domain": null,
    "sip_user": null,
    "sip_caller_id": null
  }
}
```

**Key derivation**:
```
salt    = sha256(android_id + ":gurujee")[0:16]   # device-bound, 16 bytes
key     = PBKDF2HMAC(SHA256, password=pin.encode(), salt=salt, length=32, iterations=600_000)
```

`android_id` retrieved via:
```
settings get secure android_id   (via subprocess, no root)
```
Falls back to a random 16-byte salt stored in `data/.device_salt` if `android_id`
is unavailable (e.g., running in emulator or CI). Note: Iterations increased
from 480k to 600k (0.5s on ARM64) to maintain modern security standards (SC-006).

---

## Error Types

| Error code | Meaning |
|------------|---------|
| `locked` | `unlock()` not called or `lock()` called |
| `invalid_pin` | AEAD tag verification failed (wrong PIN) |
| `corrupt` | File exists but cannot be parsed as valid ciphertext |
| `io_error` | File read/write failure |
