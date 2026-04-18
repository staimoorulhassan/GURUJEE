---
id: "031"
title: Test APK on device, 3 bugs found
stage: green
date: 2026-04-15
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: sp.implement
labels: ["testing","android","adb","bug-fix","launcher","install","001-gurujee-foundation"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - launcher/main.py
  - launcher/buildozer.spec
  - install.sh
  - gurujee_fix.sh
tests:
  - Manual device test (Redmi, Android 16, arm64-v8a)
---

## Prompt

test the app and functionality directly without committing on github

## Response snapshot

Continued from previous session where v1.0.17 APK was installed on Redmi device (Android 16, API 36, arm64-v8a). Found GURUJEE app in ConnectingScreen "Not responding" state after 120s polling timeout. Identified 3 bugs via adb screenshots and APK filesystem inspection:

1. **Markup rendering bug** (`launcher/main.py:378`): `_status` Label missing `markup=True`. When daemon poll fails, the status updates to `[color=c87941]Not responding[/color]` which renders as literal BBCode text. Fixed by adding `markup=True` to the Label constructor.

2. **Icon not bundled** (`launcher/buildozer.spec`): `source.include_exts = py,apk,sh,yaml,yml,json,md` excludes `.png`. Confirmed via `run-as ai.gurujee.gurujee ls files/app/launcher/assets/` → "No such file or directory". Icon is never copied into APK source bundle. Fixed by adding `png,jpg` to `source.include_exts`.

3. **install.sh pip failure**: `cryptography` from PyPI has no AArch64-Android wheel; Termux's Rust compiler failed to compile it from source. `set -euo pipefail` caused install.sh to exit before setting `allow-external-apps=true` or starting daemon. Fixed by replacing `pkg install -y rust binutils clang make` with `pkg install -y libffi openssl python-cryptography clang make`.

Created `/sdcard/gurujee_fix.sh` on device with incremental fix (pkg install + pip + daemon start). Unable to auto-execute due to Android 16 blocking `adb shell input` (INJECT_EVENTS permission) and Termux not being a debuggable package (blocks `run-as`).

## Outcome

- ✅ Impact: 3 root-cause bugs identified and fixed locally; device-side fix script ready at /sdcard/gurujee_fix.sh
- 🧪 Tests: Manual device testing — ConnectingScreen timeout observed, APK filesystem confirmed no PNG assets
- 📁 Files: launcher/main.py (markup=True), launcher/buildozer.spec (png,jpg in include_exts), install.sh (cryptography via pkg), gurujee_fix.sh (new device-side recovery script)
- 🔁 Next prompts: user runs `bash /sdcard/gurujee_fix.sh` in Termux → daemon starts → test WebView + chat API; then commit fixes + trigger CI for new APK
- 🧠 Reflection: Android 16 is significantly more locked down than earlier versions — adb input injection requires INJECT_EVENTS permission, run-as requires debuggable flag. Always check API level security model before planning adb automation flows.

## Evaluation notes (flywheel)

- Failure modes observed: adb input injection blocked on Android 16 (API 36); Termux not debuggable prevents run-as write to private dirs
- Graders run and results (PASS/FAIL): Manual device test — ConnectingScreen works (polls, times out, shows retry row) but markup and icon bugs visible
- Prompt variant (if applicable): null
- Next experiment: after daemon starts, test POST /chat streaming endpoint via adb forward + curl from Windows host
