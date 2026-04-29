---
id: "023"
title: Fix jnius Cython3 long Builtin Error
stage: red
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: build.log paste
labels: ["cython", "jnius", "pyjnius", "python-for-android", "buildozer", "ci", "apk-build"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .github/workflows/build-apk.yml
tests:
  - none
---

## Prompt

"C:\Users\Taimoor\Documents\build-log\build.log"

(User pasted build log path from failed v1.0.8 CI run)

## Response snapshot

Diagnosed the failure from the 3.8MB build log. Root cause: `jnius/jnius_utils.pxi:323:37: undeclared name not builtin: long` — Cython 3.0 removed `long` as a Python-level builtin in .pyx/.pxi files; pyjnius still uses it. Fix: pin `cython<3.0` in the CI install step. Committed, pushed, and tagged v1.0.9 to trigger the next CI run.

## Outcome

- ✅ Impact: CI workflow fixed — `cython<3.0` pin prevents Cython 3.x from breaking pyjnius compilation in the p4a recipe
- 🧪 Tests: CI build v1.0.9 triggered (result pending)
- 📁 Files: `.github/workflows/build-apk.yml` (1 line changed)
- 🔁 Next prompts: Paste next build.log if CI fails again; check for missing assets (icon.png, presplash.png) if it gets past jnius
- 🧠 Reflection: Cython 3.0 was a major breaking change for the p4a ecosystem — pinning `<3.0` is the standard fix until all recipes are updated

## Evaluation notes (flywheel)

- Failure modes observed: none — log path was unambiguous, error message was clear
- Graders run and results (PASS/FAIL): PASS — stage correctly identified as red (debugging build failure), routing to 001-gurujee-foundation correct
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): If v1.0.9 fails at a different stage, record which recipe fails next to build a pattern of p4a recipe compatibility issues
