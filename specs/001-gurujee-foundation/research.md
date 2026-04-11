# Research: GURUJEE Foundation — Phase 0

**Branch**: `001-gurujee-foundation` | **Date**: 2026-04-11
**Purpose**: Resolve all technical uncertainties before design begins.

---

## R-001 — faster-whisper / ctranslate2 on Termux ARM64

**Question**: Does faster-whisper (which depends on ctranslate2, a compiled C++ library)
install and run correctly on Termux ARM64 without root?

**Decision**: Defer to Phase 2. Use **openai-whisper** (pure Python) as Phase 1 placeholder
if STT is needed during setup testing; switch to faster-whisper in Phase 2 when calls are
introduced.

**Rationale**: ctranslate2 provides pre-built `aarch64` wheels on PyPI (as of v3.x), so
`pip install ctranslate2` works on Termux ARM64 Python 3.11 without compilation. However:
- Phase 1 has no active STT use (voice calls are Phase 2).
- The install.sh should attempt `pip install faster-whisper` and fall back gracefully.
- The model file (`tiny.en`) is ~39 MB and should be downloaded on first STT use (lazy load,
  P1-compliant), not at install time.

**Risk**: If ctranslate2 wheel is missing for a specific Termux Python version, the fallback
is `whisper.cpp` via `pywhispercpp` (also provides ARM64 wheels). Document both in
`install.sh`.

**Alternatives considered**:
- `openai-whisper` (pure Python, uses PyTorch) — rejected: PyTorch on ARM64 is 800MB+,
  catastrophic P1 violation.
- `whisper.cpp` + `pywhispercpp` — viable fallback but adds a compilation step.

---

## R-002 — Textual 0.47+ on Termux / Android Terminal

**Question**: Does Textual render correctly inside the Termux terminal emulator on Android?

**Decision**: **Yes, confirmed compatible.** Use Textual 0.47+.

**Rationale**:
- Termux uses `$TERM=xterm-256color` by default, which Textual fully supports.
- Textual's mouse support (optional) works via Termux's touch-to-mouse emulation.
- Known issue: Termux on Android may limit terminal columns to the screen width in portrait
  mode (~80–100 chars). TUI layout MUST be designed for ≥80-column terminals with graceful
  wrapping; test at 80-column minimum.
- Textual's `App.run()` blocks the main thread — the TUI and the gateway daemon run in the
  same process via Textual's built-in asyncio loop integration (`App.run_async()` or worker
  tasks within the App).

**Design implication**: The TUI App IS the entry point. It launches the gateway daemon as
a Textual Worker (background asyncio task), not as a separate process. This keeps RAM usage
minimal (one Python process for both TUI + daemon).

**Alternatives considered**:
- Separate TUI process + daemon process communicating via Unix socket — rejected: doubles
  idle RAM; more complex IPC.
- `urwid` TUI library — rejected: less maintained, weaker Termux support.

---

## R-003 — ElevenLabs Python SDK on Android ARM64

**Question**: Does the ElevenLabs Python SDK (`elevenlabs`) work on Termux ARM64?

**Decision**: **Yes.** The SDK is pure Python, backed by `httpx`. No native compilation.

**Rationale**: `pip install elevenlabs` succeeds on Termux ARM64. The SDK's streaming mode
uses `httpx` async streaming, which integrates cleanly with asyncio.

**Phase 1 usage**: Only the `clone` endpoint (instant clone, 30s sample upload) is called
during guided setup. The `generate` endpoint (streaming TTS) is Phase 2. The SDK is
installed in Phase 1 so Phase 2 requires no new packages.

**Alternatives considered**:
- Direct `httpx` calls to ElevenLabs API — viable but more maintenance burden.

---

## R-004 — cryptography library on ARM64

**Question**: Does `pip install cryptography` succeed on Termux ARM64?

**Decision**: **Yes, via pre-built wheel.** Termux's pip resolves `cryptography` to a
pre-built `aarch64` wheel (Rust-backed via `maturin`). No compilation required.

**Rationale**: The `cryptography` package provides pre-built wheels for
`manylinux_2_17_aarch64` which Termux's pip accepts. The specific functions used
(AES-256-GCM, PBKDF2-HMAC-SHA256) are in `cryptography.hazmat.primitives` — standard,
well-tested, no issues on ARM.

**Key derivation design**:
```
device_fingerprint = sha256(android_id + build_fingerprint)
salt = device_fingerprint[:16]   # 16-byte salt
key = PBKDF2HMAC(SHA256, length=32, salt=salt, iterations=480000)
```
`android_id` retrieved via `subprocess` calling `settings get secure android_id`
(available without root via Termux). Falls back to a stored random salt if unavailable.

**Alternatives considered**:
- `PyNaCl` (libsodium) — also ARM64-compatible, but cryptography is more explicit for
  PBKDF2 + AES-GCM requirements.

---

## R-005 — Termux:Boot Auto-Start Mechanism

**Question**: How does Termux:Boot start the GURUJEE daemon reliably on phone reboot?

**Decision**: Create `~/.termux/boot/start-gurujee.sh` during guided setup.

**Rationale**: Termux:Boot (separate F-Droid app) runs all scripts in `~/.termux/boot/`
when the device boots. The script must:
1. Source the Termux environment (`source ~/.bashrc` or `export PATH=$PREFIX/bin:$PATH`).
2. `cd` to the GURUJEE install directory.
3. Launch the TUI + daemon: `python -m gurujee.tui.app >> data/boot.log 2>&1 &`

The `&` backgrounds the process; `nohup` is NOT needed in Termux:Boot context.
A `sleep 5` before the launch command avoids race conditions with Termux initialization.

**Guided setup step**: The wizard creates and `chmod +x`-es the boot script, then asks
the user to install Termux:Boot if not already present (with a direct F-Droid link).

**Alternatives considered**:
- Termux:Widget shortcut — manual launch only, not auto-boot.
- Android `WorkManager` via Kivy — too complex for daemon start; reserved for APK layer.

---

## R-006 — openai SDK 1.x with Pollinations Endpoint

**Question**: Does `AsyncOpenAI(base_url=..., api_key="")` work with gen.pollinations.ai?

**Decision**: **Yes.** The Pollinations endpoint is OpenAI-compatible. Use `AsyncOpenAI`.

**Rationale**: The openai 1.x SDK allows full endpoint override:
```python
from openai import AsyncOpenAI
client = AsyncOpenAI(
    base_url="https://gen.pollinations.ai/v1",
    api_key=""           # required by SDK but ignored by endpoint
)
```
`chat.completions.create(model=..., messages=..., stream=True)` works identically.

**Streaming**: Streaming (`stream=True`) is mandatory (P1 — no buffering). The SDK returns
an `AsyncStream[ChatCompletionChunk]` which integrates cleanly with `async for` in asyncio.

**Retry logic**: Wrap all calls in `tenacity.retry` with exponential backoff
(max 3 attempts, 2s base, 30s cap). On final failure, emit a `CHAT_ERROR` message to the
bus and surface in TUI. Queue the original message for retry on reconnect.

**Alternatives considered**:
- `httpx` direct calls — more control but loses SDK typing and retry helpers.
- `aiohttp` — unnecessary when `httpx` is already available via openai SDK.

---

## R-007 — TUI Architecture: Single Process vs. Split Process

**Question**: Should the TUI and the gateway daemon run in the same Python process or
separate processes communicating via IPC?

**Decision**: **Single process.** The Textual App IS the process; the gateway daemon runs
as a Textual Worker (asyncio Task within the App's event loop).

**Rationale**:
- Saves ~20–30 MB RAM (no second Python interpreter).
- Textual's `App.run_async()` exposes the same asyncio loop that agents use for their
  Queues — no cross-process serialisation needed.
- `app.call_from_thread()` / `app.post_message()` provides clean TUI updates from agent
  tasks without thread safety issues.
- If the TUI is closed, a `--headless` flag allows `gateway_daemon.py` to run without
  Textual (for Termux:Boot background mode).

**Startup modes**:
1. `python -m gurujee` (or `gurujee` CLI) — TUI + daemon (normal use)
2. `python -m gurujee --headless` — daemon only, no TUI (Termux:Boot auto-start)
3. `python -m gurujee.setup` — guided setup wizard (first run)

**Alternatives considered**:
- Separate processes via Unix socket — rejected (doubles RAM, P1 violation risk).
- `multiprocessing` for each agent — rejected (P1 RAM; asyncio Tasks are sufficient).

---

## R-008 — SQLite WAL Mode and Concurrent Agent Access

**Question**: Multiple agents (memory + heartbeat + cron) may read/write SQLite concurrently.
Is stdlib `sqlite3` safe here?

**Decision**: Enable **WAL (Write-Ahead Logging)** mode on DB open. Serialize all writes
via a dedicated `MemoryAgent` queue — other agents NEVER write directly to SQLite.

**Rationale**:
- SQLite in WAL mode allows one writer + many concurrent readers without blocking.
- All write operations go through `MemoryAgent` (which owns the connection), satisfying
  the "single writer" contract.
- Read operations (context injection) also go through `MemoryAgent` via message bus — no
  direct DB access from other agents.
- This avoids `sqlite3.OperationalError: database is locked` under asyncio concurrent tasks.

**Connection setup**:
```python
conn = sqlite3.connect("data/memory.db", check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")   # safe with WAL
```

---

## R-009 — PyYAML vs. ruamel.yaml for Config Round-Trips

**Question**: Should we use `PyYAML` or `ruamel.yaml` to preserve comments in YAML config
files when writing back (especially `agents/soul_identity.yaml` which users edit)?

**Decision**: **PyYAML** for all read/write except `soul_identity.yaml` which uses
**ruamel.yaml** (comment-preserving) to protect user edits.

**Rationale**: PyYAML's `yaml.safe_dump` strips all comments. For `soul_identity.yaml`
(user-editable personality file), stripping comments on every TUI save would destroy
user annotations. `ruamel.yaml` preserves comments exactly. It installs cleanly on ARM64.

**Rule**: All machine-written config (`setup_state.yaml`, `config/*.yaml`) use PyYAML.
Only `soul_identity.yaml` uses ruamel.yaml for round-trip safety.

**Alternatives considered**:
- All ruamel.yaml — overkill for machine-only files, slightly heavier import.
- All PyYAML — breaks user comments in soul_identity.yaml.

---

## R-010 — tenacity for Retry Logic

**Question**: Is `tenacity` compatible with asyncio and ARM64 Termux?

**Decision**: **Yes.** Use `tenacity` with `AsyncRetrying` for all async retries.

**Rationale**: `tenacity` is pure Python, ARM64-compatible, asyncio-native via
`AsyncRetrying`. Used for: AI endpoint calls, ElevenLabs calls (Phase 2), SQLite
transient errors. Configured with:
- `stop=stop_after_attempt(3)`
- `wait=wait_exponential(multiplier=1, min=2, max=30)`
- `retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException))`

---

## Summary of Technical Decisions

| # | Topic | Decision |
|---|-------|----------|
| R-001 | STT (Phase 2) | faster-whisper + ctranslate2 ARM64 wheel; lazy model load |
| R-002 | Textual on Termux | Confirmed compatible; design for 80-col minimum |
| R-003 | ElevenLabs SDK | Pure Python; install Phase 1, use Phase 2 |
| R-004 | cryptography ARM64 | Pre-built wheel; PBKDF2+AES-GCM confirmed |
| R-005 | Termux:Boot | `~/.termux/boot/start-gurujee.sh` created by setup wizard |
| R-006 | openai SDK + Pollinations | `AsyncOpenAI(base_url=..., api_key="")` confirmed |
| R-007 | TUI architecture | Single process; Textual Workers for agents |
| R-008 | SQLite concurrency | WAL mode; all writes via MemoryAgent only |
| R-009 | YAML library | PyYAML for machine files; ruamel.yaml for soul_identity.yaml |
| R-010 | Retry logic | tenacity AsyncRetrying; 3 attempts, exponential backoff |
