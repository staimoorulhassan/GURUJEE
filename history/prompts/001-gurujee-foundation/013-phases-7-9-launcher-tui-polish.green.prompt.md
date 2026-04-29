---
id: "013"
title: Phases 7–9 — Launcher APK, TUI, Polish & Tests
stage: green
date: 2026-04-12
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: continue from where we left
labels: ["implementation", "launcher", "kivy", "tui", "polish", "testing", "coverage", "logging"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: history/adr/ADR-003-split-process-daemon-pwa-architecture.md
  pr: null
files:
 - launcher/main.py (T059 — Kivy GurujeeApp: ProgressScreen + WebViewScreen + bootstrap thread)
 - launcher/buildozer.spec (T060 — android.api=34, minapi=29, arm64-v8a, INTERNET+REQUEST_INSTALL_PACKAGES)
 - gurujee/agents/memory_agent.py (T066 — RotatingFileHandler for data/memory.log)
 - gurujee/agents/automation_agent.py (T066 — RotatingFileHandler for data/automation.log)
 - gurujee/server/app.py (T066+T071 — RotatingFileHandler server.log + global exception handler)
 - gurujee/server/routers/health.py (T072 — shizuku_inactive warning in GET /health)
 - specs/001-gurujee-foundation/quickstart.md (T074 — split-layer developer setup, PWA, APK build, coverage)
 - specs/001-gurujee-foundation/tasks.md (T059–T074 all marked [X] — all 66 tasks complete)
 - tests/test_cron_agent.py (new — 97% coverage on cron_agent.py)
 - tests/test_user_agent.py (new — 97% coverage on user_agent.py)
 - tests/test_tool_router.py (new — 91% coverage on tool_router.py)
 - tests/test_gateway_daemon.py (new — GatewayDaemon properties + shutdown + emit_status)
 - tests/test_executor_and_system.py (new — ShizukuExecutor.is_available, execute, system actions)
 - tests/test_setup_wizard.py (T070 — added TestBootScriptContent with shebang + headless + boot.log checks)
tests:
 - tests/test_cron_agent.py
 - tests/test_user_agent.py
 - tests/test_tool_router.py
 - tests/test_gateway_daemon.py
 - tests/test_executor_and_system.py
 - tests/test_setup_wizard.py (updated)
---

## Prompt

continue from where we left

## Response snapshot

Resumed from PHR-012 (Phases 1–6 complete, T001–T058 done). Implemented remaining phases:

**Phase 7 (T059–T060):**
- `launcher/main.py` — Kivy GurujeeApp with ProgressScreen (ProgressBar + status labels + retry button) and WebViewScreen (jnius native WebView loading http://localhost:7171). Bootstrap thread: check/install Termux → check/install Termux:API → inject bootstrap script → poll daemon ready → switch screen.
- `launcher/buildozer.spec` — android.api=34, minapi=29, arm64-v8a, permissions: INTERNET, REQUEST_INSTALL_PACKAGES, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, QUERY_ALL_PACKAGES. Signing via env vars only.

**Phase 8 (T061–T065):** TUI files already existed from prior session — verified all screens in place (app.py, theme.py, chat_screen.py, agent_status_screen.py, settings_screen.py).

**Phase 9 (T066–T074):**
- T066: Added RotatingFileHandler(5MB×3) to memory_agent.py → memory.log, automation_agent.py → automation.log, server/app.py → server.log + uvicorn loggers.
- T067/T068: Verified — already implemented in ai/client.py (allowlist) and config/loader.py (_resolve env override).
- T070: Added TestBootScriptContent test verifying shebang `#!/data/data/com.termux/files/usr/bin/bash`, `--headless`, `data/boot.log` in boot script.
- T071: Added global exception handler in server/app.py → returns `{"error": ..., "done": true}` JSON on 500.
- T072: Added Shizuku health flag — GET /health returns `{"warnings": ["shizuku_inactive"]}` when rish unavailable.
- T073: Added 5 new test files → 118 tests, **70% coverage** (TOTAL 1965 stmts, 582 missed). All pass.
- T074: Updated quickstart.md with Step 4 (PWA UI), Step 5 (coverage), Step 6 (buildozer APK), expanded layout including server/, automation/, launcher/.

All 66 tasks in tasks.md marked [X] complete.

## Outcome

- ✅ Impact: All 9 phases complete — GURUJEE Foundation feature fully implemented (T001–T074, 66/66 tasks)
- 🧪 Tests: 118 passed, 0 failed, 70% coverage (target met)
- 📁 Files: 6 new/modified implementation files, 5 new test files, quickstart.md + tasks.md updated
- 🔁 Next prompts: /sp.git.commit_pr to commit and raise PR; Phase 2 (calls, SMS, SIP)
- 🧠 Reflection: Coverage jumped from 59% to 70% by adding tests for zero-coverage modules (cron_agent, user_agent) and targeted tests for tool_router, gateway_daemon, executor

## Evaluation notes (flywheel)

- Failure modes observed: sed multi-expression syntax broken on Windows bash — used Python inline script instead
- Graders run and results (PASS/FAIL): pytest 118/118 PASS; coverage 70% PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): run /sp.git.commit_pr to commit all changes
