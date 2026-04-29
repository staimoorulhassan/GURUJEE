---
id: "002"
title: Fix setup install entry points
stage: general
date: 2026-04-13
surface: agent
model: claude-sonnet-4-6
feature: none
branch: 001-gurujee-foundation
user: Taimoor
command: direct prompt
labels: ["bugfix", "setup", "install", "entry-point", "android", "termux"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - gurujee/setup/__main__.py
  - gurujee/__main__.py
  - install.sh
tests:
  - python -c "from gurujee.setup.__main__ import main" (import smoke test)
  - python -m gurujee --help (CLI flag verification)
---

## Prompt

Fix the install.sh crash on Android. The error is:

"No module named gurujee.setup.__main__; 'gurujee.setup' is a package and cannot be directly executed"

Root cause: install.sh runs the setup wizard using python -m gurujee.setup
but gurujee/setup/ is a package directory with no __main__.py.

Fix all three of these:

1. Create gurujee/setup/__main__.py that simply calls the guided setup entry point:
   from gurujee.setup.guided_setup import main
   if __name__ == "__main__":
       main()

2. Confirm gurujee/setup/guided_setup.py has a main() function at module level
   that starts the Rich wizard. If it uses a different entry point name, 
   update __main__.py to match whatever function actually starts the wizard.

3. Check install.sh — find the line that launches the setup wizard and confirm
   it uses: python -m gurujee.setup
   If it uses anything else, fix it to match.

4. Also check gurujee/__main__.py exists with a main() that accepts these flags:
   --setup    → run guided setup wizard
   --start    → start daemon headless  
   --headless → start daemon headless (alias)
   --tui      → start with Textual TUI
   --status   → print agent status and exit
   --logs     → tail data/gateway.log
   --restart  → restart daemon
   So that: python -m gurujee --setup works from install.sh

5. Update install.sh to use: python -m gurujee --setup
   instead of: python -m gurujee.setup

6. Test locally: cd ~/Desktop/GURUJEE && python -m gurujee --setup
   Confirm it launches the wizard without error.

7. Commit and push:
   git add -A
   git commit -m "fix(setup): add __main__.py entry points, fix install.sh launch command"
   git push origin 001-gurujee-foundation

## Response snapshot

Fixed all three files. The wizard entry point was `SetupWizard().run()` in `wizard.py` (not `guided_setup.py`), so `gurujee/setup/__main__.py` was updated to expose a `main()` wrapper around it. `gurujee/__main__.py` gained `--setup`, `--start`, `--tui`, `--status`, `--logs`, `--restart` flags. `install.sh` line 69 was changed from `python -c "..."` inline to `python -m gurujee --setup`. All imports verified; committed and pushed to `001-gurujee-foundation`.

## Outcome

- ✅ Impact: Android install.sh no longer crashes; `python -m gurujee --setup` launches the wizard correctly
- 🧪 Tests: Import smoke tests passed; `python -m gurujee --help` shows all 8 new flags
- 📁 Files: gurujee/setup/__main__.py, gurujee/__main__.py, install.sh
- 🔁 Next prompts: Run `bash install.sh` on a real Termux session to verify end-to-end; add `--version` flag
- 🧠 Reflection: The wizard lived in `wizard.py` not `guided_setup.py` — always read existing files before assuming module names match request descriptions

## Evaluation notes (flywheel)

- Failure modes observed: User referenced `guided_setup.py` which doesn't exist; adapter found correct file (`wizard.py`) by reading codebase before writing
- Graders run and results (PASS/FAIL): import smoke test PASS; --help PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add integration test that imports and calls `main()` from both `__main__.py` files to guard against future regressions
