---
id: 027
title: Fix Termux connection, command execution, and wizard robustness
stage: green
date: 2026-04-15
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: (inline chat)
labels: ["termux","android","health","daemon","wizard","bootstrap","fix"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - gurujee/daemon/gateway_daemon.py
 - gurujee/server/routers/health.py
 - launcher/bootstrap.py
 - launcher/main.py
 - launcher/buildozer.spec
 - install.sh
 - gurujee/setup/wizard.py
tests:
 - (existing test suite — no new tests added this session)
---

## Prompt

app functioning is not making connection with termux and not executing commands on termux and not providing self setup commands, and in option a there are many things not supprting andriod termux

## Response snapshot

Root-cause investigation identified four distinct bugs:

1. **GatewayDaemon.ready too strict** — required ALL 5 agents to be RUNNING; any crashed agent kept /health returning {"status":"starting"} forever, so the APK ConnectingScreen always timed out.
2. **open_termux() gave no UX feedback** — user got zero instructions after pressing "Open Termux".
3. **No Termux command-execution path from APK** — bootstrap.py had no run_command_in_termux().
4. **Wizard steps crashed on missing Termux:API** — termux-permission and termux-microphone-record raised FileNotFoundError when Termux:API wasn't installed, aborting setup.

Fixes applied:
- `gateway_daemon.py`: `ready` now returns True when all agents are STARTED (RUNNING | ERROR | STOPPED). Added `healthy` property for "all running" distinction.
- `health.py`: Surfaces crashed agent names as `agent_errors:<names>` warning instead of blocking the "ready" response.
- `bootstrap.py`: Added `run_command_in_termux(cmd)` — tries jnius RUN_COMMAND intent (foreground service), falls back to /system/bin/am subprocess.
- `main.py`: `SetupScreen._on_open_termux` now auto-copies the command and tries RUN_COMMAND intent; if it fails, opens Termux with clipboard fallback and shows "long-press to paste" instructions.
- `buildozer.spec`: Added `com.termux.permission.RUN_COMMAND` to android.permissions.
- `install.sh`: Writes `allow-external-apps = true` to ~/.termux/termux.properties so the RUN_COMMAND intent is honoured.
- `wizard.py`: Both `_step_permissions_inner` and `_step_voice_sample_inner` now check for the binary with `shutil.which()` and skip gracefully with an install hint if Termux:API is absent.

## Outcome

- ✅ Impact: APK can now connect once daemon starts (even if agents crash). "Open Termux" gives users a working paste path or auto-runs setup. Setup wizard no longer aborts on missing Termux:API.
- 🧪 Tests: Existing test suite unchanged; no new tests.
- 📁 Files: 7 files modified
- 🔁 Next prompts: test RUN_COMMAND intent on device; add unit tests for new wizard skip-paths; consider daemon auto-restart for errored agents
- 🧠 Reflection: The health endpoint's "all agents RUNNING" contract was too strict for a resilient daemon — ERROR state should mean "started but degraded", not "not ready".

## Evaluation notes (flywheel)

- Failure modes observed: daemon stuck on "starting" due to agent crashes; wizard hard-crash on missing tools
- Graders run and results (PASS/FAIL): none run this session
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): add a device-side integration test that spins up daemon with a crashing agent and asserts /health returns "ready"
