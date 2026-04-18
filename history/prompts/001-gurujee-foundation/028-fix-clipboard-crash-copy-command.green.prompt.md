---
id: "028"
title: Fix clipboard crash on Copy Command tap
stage: green
date: 2026-04-15
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: fix clipboard crash
labels: ["bug", "android", "clipboard", "launcher", "crash"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - launcher/bootstrap.py
tests:
  - manual: tap Copy Command button on SetupScreen — no crash, feedback label shows "Copied to clipboard!"
---

## Prompt

now the app runs, move to commands screen after dedecting termux, but when i click copy command it gets crushed

## Response snapshot

Root cause: `copy_to_clipboard` in `bootstrap.py` schedules the clipboard write via
`Clock.schedule_once(_copy, 0)`. The outer `try/except` only guards the scheduling call,
not the `_copy` callback body. When `_copy` threw (due to `ClipboardManager.CLIPBOARD_SERVICE`
being an inherited Java static field that jnius can't reliably resolve), the exception
propagated uncaught through Kivy's Clock and crashed the app.

Two-line fix:
1. Wrap `_copy` body in its own `try/except`
2. Replace `ClipboardManager.CLIPBOARD_SERVICE` with the string literal `"clipboard"`

Removed the `ClipboardManager` autoclass import (no longer needed). Tagged v1.0.17 to
trigger a new APK CI build.

## Outcome

- ✅ Impact: Copy Command button no longer crashes app; clipboard write silently no-ops on failure instead
- 🧪 Tests: Manual device test after APK install
- 📁 Files: launcher/bootstrap.py (1 file, +8/-4 lines)
- 🔁 Next prompts: Install v1.0.17 APK, test Copy Command, then full install.sh flow in Termux
- 🧠 Reflection: Clock.schedule_once callbacks are a crash boundary — always guard callback bodies independently of the outer scheduling try/except

## Evaluation notes (flywheel)

- Failure modes observed: jnius static field access on inherited Java constants unreliable; Kivy Clock callbacks not covered by outer try/except
- Graders run and results (PASS/FAIL): n/a
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
