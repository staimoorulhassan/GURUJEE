---
id: "032"
title: "Fix daemon: headless guard + audio deps"
stage: green
date: 2026-04-17
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: "continue session — fix GURUJEE daemon not starting in Termux"
labels: ["daemon","termux","headless","adb","debugging","fix"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - gurujee_fix.sh
  - gurujee/__main__.py (patched on device via adb push)
tests:
  - "Port 7171 confirmed LISTEN via adb shell ss"
  - "Python process PID confirmed via adb shell ps"
  - "start_daemon.sh reported SUCCESS: daemon running on port 7171"
---

## Prompt

CONNECTED

(Context: device reconnected after WhatsApp call interrupted the fix session. Fix script `/sdcard/gurujee_fix.sh` was previously started but interrupted. Goal: get GURUJEE daemon running in Termux so APK can connect.)

## Response snapshot

Resumed session. Re-ran fix script via `adb shell input text`. Found two new root causes:

**Root cause 1 — `faster-whisper` → `av` compile failure:**
The fix script's step 3 pip-installed `faster-whisper` which pulls in `av` (PyAV), a Cython+FFmpeg C extension. No pre-built arm64-android wheel exists on PyPI; compilation fails. Fix: removed `faster-whisper` and `elevenlabs` from step 3; installed gurujee package with `--no-deps --no-build-isolation`.

**Root cause 2 — stale `__main__.py` on device missing headless guard:**
The phone's git repo had an older commit of `gurujee/__main__.py` without `and not headless_mode` in the is_first_run check:
```python
# OLD (phone's version):
if is_first_run or args.setup or args.reset:
    SetupWizard(...).run()  # always ran in headless mode too!

# CORRECT (local repo):
if (is_first_run or args.setup or args.reset) and not headless_mode:
    SetupWizard(...).run()  # skipped when --headless
```
Since no `setup_state.yaml` exists, `is_first_run=True` → setup wizard ran → stdin is `/dev/null` (nohup) → `EOFError`. Fixed by pushing the correct `__main__.py` via `adb push` and copying into `~/gurujee/gurujee/__main__.py`.

**Result:** Daemon running on port 7171. `ss -tlnp` shows `LISTEN 127.0.0.1:7171`. Python PID 11913 confirmed.

## Outcome

- ✅ Impact: GURUJEE daemon successfully running on port 7171; APK can now connect
- 🧪 Tests: Port 7171 LISTEN confirmed via adb shell ss; Python process confirmed via ps; start_daemon.sh reported SUCCESS
- 📁 Files: gurujee_fix.sh updated (removed audio packages); __main__.py pushed to device (permanent fix needs git pull on device)
- 🔁 Next prompts: Switch to GURUJEE app → tap Try Again → verify WebView loads; run `git pull` in Termux to sync code permanently; rebuild APK with all visual fixes
- 🧠 Reflection: Two separate root causes masked each other — audio dep failure was the immediate blocker, but even after fixing that, the stale __main__.py would have failed. Systematic read of boot.log + file inspection revealed both.

## Evaluation notes (flywheel)

- adb push + Termux cp via input injection is reliable for pushing single files
- `faster-whisper` / `elevenlabs` are startup-optional; daemon only needs fastapi/uvicorn/rich/openai at boot
- Phone git repos go stale — always verify the running code matches the local repo when debugging
- `and not headless_mode` guard position matters: must evaluate AFTER setting headless_mode variable
