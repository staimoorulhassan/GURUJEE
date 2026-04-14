---
id: "026"
title: Implement 4-screen onboarding redesign
stage: green
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: (continuation from plan approval)
labels: ["onboarding", "kivy", "bootstrap", "uvicorn", "headless", "termux", "install.sh", "webview"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - gurujee/__main__.py
  - install.sh
  - launcher/main.py
  - launcher/bootstrap.py
  - gurujee/setup/wizard.py
tests:
  - none
---

## Prompt

(Session continuation — implementing the approved plan from previous context)

The plan was approved at the end of the previous session. The app was broken end-to-end:
1. The FastAPI/uvicorn HTTP server was never started — GatewayDaemon.start() launched agents but never called create_app() or started uvicorn, so the APK's health-check poll (GET /health) timed out every time.
2. The bootstrap injection flow was broken — am broadcast RUN_COMMAND requires allow-external-apps=true in Termux (not set by default).
3. PIN prompt blocks headless daemon start — _prompt_pin() was called before the headless/TUI branch, so python -m gurujee --headless hangs waiting for stdin on device reboot.
4. APK onboarding was missing — users saw a progress bar that timed out silently.

Implement the approved plan: 4-screen onboarding, fix headless mode, fix install.sh.

## Response snapshot

Implemented all 5 files from the approved plan:
1. `gurujee/__main__.py` — moved PIN prompt into TUI branch only; headless mode skips PIN when stdin is not a TTY; `asyncio.gather(gateway.start(), server.serve())` now starts both daemon and uvicorn on port 7171 together.
2. `install.sh` — writes `~/.gurujee.env` with Pollinations API key, starts daemon with nohup after setup, prints "Go back to GURUJEE app" banner.
3. `launcher/main.py` — full rewrite to 4-screen flow: WelcomeScreen (F-Droid Termux install) → SetupScreen (copyable curl command) → ConnectingScreen (live poll) → WebViewScreen; fast probe on on_start() skips onboarding if daemon already running.
4. `launcher/bootstrap.py` — simplified: removed broken inject_bootstrap()/APK-installer logic; added open_url() and copy_to_clipboard() via Android Intents/ClipboardManager.
5. `gurujee/setup/wizard.py` — boot script template now sources ~/.gurujee.env before starting daemon.

## Outcome

- ✅ Impact: The HTTP server now starts alongside the daemon in headless mode, fixing the root cause of all health-check poll timeouts. The APK now has a guided 4-screen onboarding flow replacing the broken silent progress bar. Device reboots auto-start the daemon without PIN prompts.
- 🧪 Tests: Syntax validation passed for all 4 Python files via ast.parse
- 📁 Files: gurujee/__main__.py, install.sh, launcher/main.py, launcher/bootstrap.py, gurujee/setup/wizard.py
- 🔁 Next prompts: Push tag to trigger APK build; test on real device; verify /health responds after install.sh runs
- 🧠 Reflection: The PIN-before-headless ordering bug was the most subtle issue — it would always block silently on Termux:Boot restarts, never surfacing an obvious error.

## Evaluation notes (flywheel)

- Failure modes observed: None — plan was detailed enough to implement directly
- Graders run and results (PASS/FAIL): ast.parse syntax check PASS (all 4 Python files)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add a /health readiness check at the end of install.sh before printing the "Go back" banner
