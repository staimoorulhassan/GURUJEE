---
id: 020
title: APK Build Wire Launcher Workdir
stage: green
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: manual (APK build request)
labels: ["apk","buildozer","launcher","ci","assets","python-3.11"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - .github/workflows/build-apk.yml
  - tests/test_build_apk_workflow.py
  - launcher/assets/icon.png
  - launcher/assets/presplash.png
  - .claude/settings.local.json
  - .python-version
tests:
  - tests/test_build_apk_workflow.py (22 passed)
---

## Prompt

if files have been finalized so start making .apk application

## Response snapshot

Identified 4 blockers preventing CI APK build from succeeding:

1. **Missing launcher/assets/** — buildozer.spec referenced presplash.png and icon.png that didn't exist.
   Created minimal valid PNGs (presplash 1080×1920, icon 512×512) using Python struct/zlib.

2. **CI workflow ran buildozer from repo root** — buildozer.spec is in launcher/, so buildozer
   couldn't find it. Fixed by adding `cd launcher` before `buildozer android debug` in the build step.

3. **All APK paths in workflow pointed to wrong directories** — changed bin/*.apk → launcher/bin/*.apk
   for both the release upload step and the artifact upload step.

4. **Tests enforced incorrect gurujee/*.apk path** — gurujee/ is the Python source module, not a
   build output directory. Updated test assertions to require launcher/bin/*.apk (actual buildozer output).

Commit: 94cffe4 — 7 files, 22 workflow tests passing.
Tag v0.1.0 pushed → GitHub Actions build-apk.yml triggered.
APK will appear as artifact on the v0.1.0 GitHub Release when build completes (~30-40 min).

## Outcome

- ✅ All 22 test_build_apk_workflow.py tests pass
- ✅ Tag v0.1.0 pushed, GitHub Actions triggered
- ✅ launcher/assets/ created with valid PNG files
- 🔁 APK build running on GitHub Actions (~30-40 min to complete)
- 🔁 Next: monitor https://github.com/staimoorulhassan/GURUJEE/actions for build result
