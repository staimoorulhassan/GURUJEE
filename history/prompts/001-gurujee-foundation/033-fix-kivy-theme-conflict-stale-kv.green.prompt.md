---
id: 033
title: Fix Kivy Theme Conflict — Remove Stale gurujee.kv
stage: green
date: 2026-04-17
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: check the problem and fix theme
labels: ["bugfix","theme","kivy","launcher","apk"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - launcher/gurujee.kv (deleted)
  - launcher/buildozer.spec
  - launcher_build/gurujee.kv (deleted)
tests:
  - visual inspection via gurujee_app.png screenshot
---

## Prompt

check the problem and fix theme

## Response snapshot

Identified two root causes:

1. **Stale `launcher/gurujee.kv` auto-loaded by Kivy** — Kivy convention auto-loads a `.kv` file matching the App class name (`GurujeeApp` → `gurujee.kv`) before `build()` runs. The old amber-themed file defined `<SetupScreen>` rules that injected a second BoxLayout (amber, MDSpinner) alongside the Python-built cyan/copper BoxLayout. This caused duplicate widgets and theme conflict.

2. **`kivymd` in buildozer.spec requirements but unused** — `main.py` uses plain `kivy.app.App`, not `MDApp`. KivyMD was wasting build time, APK size, and running theme init on every launch.

Fixes:
- Deleted `launcher/gurujee.kv` and `launcher_build/gurujee.kv`
- Removed `kivymd` from `buildozer.spec` requirements (now: `python3,kivy,requests,jnius,android`)

The `markup=True` on `_status` label in `ConnectingScreen` was already correct in the source — raw tag display was from an older APK build.

## Outcome

- ✅ Impact: Eliminates amber/cyan theme conflict in SetupScreen; removes duplicate widget injection; reduces APK requirements
- 🧪 Tests: Requires APK rebuild and device test to verify SetupScreen shows only cyan/copper theme with no duplicate widgets
- 📁 Files: launcher/gurujee.kv deleted, launcher/buildozer.spec updated, launcher_build/gurujee.kv deleted
- 🔁 Next prompts: Rebuild APK with `buildozer android debug`, test SetupScreen and ConnectingScreen visually on device
- 🧠 Reflection: Kivy's auto-load convention is a silent gotcha — always remove stale `.kv` files when migrating to embedded `_KV` strings

## Evaluation notes (flywheel)

- Failure modes observed: Kivy auto-load convention not accounted for during T059 redesign; old `.kv` file left in source dir
- Graders run and results (PASS/FAIL): visual screenshot review — PASS (identified conflict)
- Prompt variant (if applicable): null
- Next experiment: confirm no other `.kv` files exist in source that could be auto-loaded by Kivy
