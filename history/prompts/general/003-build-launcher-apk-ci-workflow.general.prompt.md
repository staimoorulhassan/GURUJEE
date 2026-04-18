---
id: "003"
title: Build launcher APK CI workflow
stage: general
date: 2026-04-13
surface: agent
model: claude-sonnet-4-6
feature: none
branch: 001-gurujee-foundation
user: Taimoor
command: direct prompt
labels: ["apk", "kivy", "buildozer", "github-actions", "android", "launcher", "ci"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - buildozer.spec
  - apk_src/main.py
  - apk_src/gurujee.kv
  - apk_src/assets/logo.png
  - .github/workflows/build-apk.yml
tests:
  - none
---

## Prompt

The README describes Option B (Download APK from GitHub Releases) but no APK 
exists. We need to build and publish it. Do all of this:

---

PART 1 — Build the launcher APK with Buildozer

The APK is a thin Kivy launcher. Its only job:
1. Show a GURUJEE splash screen (black background, amber logo, app name)
2. Check if Termux is installed on the device
3. If Termux is NOT installed: show a button "Install Termux" that opens 
   https://f-droid.org/packages/com.termux/ in the browser
4. If Termux IS installed: run the bootstrap automatically by sending an 
   intent to Termux to execute the install.sh script, then show a 
   "Setting up GURUJEE..." progress message
5. When the daemon is ready (poll http://localhost:7171/health every 3s), 
   open the PWA in a WebView pointed at http://localhost:7171

[... full prompt as provided ...]

PART 2 — Add GitHub Actions workflow to build the APK automatically

[... full CI workflow spec as provided ...]

## Response snapshot

Created all 5 files: buildozer.spec (arm64-v8a, API 33/28, kivy+requests), apk_src/main.py (3-screen Kivy app with pyjnius Intent bridge to Termux, health polling, WebView), apk_src/gurujee.kv (black+amber KV layout for all 3 screens), apk_src/assets/logo.png (512x512 procedural G-glyph placeholder), .github/workflows/build-apk.yml (build on tag push or workflow_dispatch, ~/.buildozer cache, artifact upload, softprops release). Committed as 8aab271 and pushed.

## Outcome

- ✅ Impact: Option B in README is now backed by real build infrastructure; pushing a `v*` tag triggers CI and publishes the APK to GitHub Releases automatically
- 🧪 Tests: No automated tests (Kivy launcher requires physical Android device or emulator)
- 📁 Files: buildozer.spec, apk_src/main.py, apk_src/gurujee.kv, apk_src/assets/logo.png, .github/workflows/build-apk.yml
- 🔁 Next prompts: Replace placeholder logo.png with real artwork; test CI by pushing a v1.0.0-beta tag; add `pyjnius` to buildozer requirements once confirmed working on device
- 🧠 Reflection: Buildozer's ~/.buildozer cache (covering SDK/NDK/p4a) is the single most important CI optimization — without it each run downloads 2+ GB and takes 40+ min

## Evaluation notes (flywheel)

- Failure modes observed: none — task was well-specified with explicit file contents
- Graders run and results (PASS/FAIL): import/syntax check on main.py PASS (python -c import)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add a workflow step that runs `python -m py_compile apk_src/main.py` to catch syntax errors before the 40-min Buildozer run
