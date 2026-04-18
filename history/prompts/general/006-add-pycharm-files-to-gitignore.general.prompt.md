---
id: "006"
title: Add PyCharm Files to .gitignore
stage: general
date: 2026-04-15
surface: agent
model: claude-sonnet-4-6
feature: none
branch: 001-gurujee-foundation
user: Taimoor
command: PyCharm
labels: ["gitignore","tooling","pycharm","ide"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .gitignore
tests:
  - null
---

## Prompt

PyCharm

## Response snapshot

Identified that opening the project in PyCharm generated legacy root-level project files (`GURUJEE.iml`, `GURUJEE.ipr`, `GURUJEE.iws`) not covered by the existing `.gitignore` (which only excluded `.idea/`). Added `*.iml`, `*.ipr`, `*.iws` patterns to `.gitignore` so these files are no longer tracked by git.

## Outcome

- ✅ Impact: PyCharm legacy project files are now ignored by git; they will no longer appear as untracked files in `git status`.
- 🧪 Tests: none — trivial config change
- 📁 Files: .gitignore
- 🔁 Next prompts: none anticipated
- 🧠 Reflection: The `.idea/` exclusion covered the modern PyCharm format but missed the legacy directory-based format. The `*.iml`/`*.ipr`/`*.iws` glob patterns also cover IntelliJ IDEA and Android Studio legacy files.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
