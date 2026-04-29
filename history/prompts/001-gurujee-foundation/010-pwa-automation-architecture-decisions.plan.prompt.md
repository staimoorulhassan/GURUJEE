---
id: 010
title: PWA + Automation Architecture Decisions
stage: plan
date: 2026-04-12
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: architecture decisions → pre /sp.tasks
labels: ["pwa", "automation", "shizuku", "fastapi", "architecture", "non-technical-users", "apk", "split-process"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: history/adr/ADR-003-split-process-daemon-pwa-architecture.md
  pr: null
files:
  - .specify/memory/constitution.md (P5, P6, P9 amended → v1.1.0)
  - specs/001-gurujee-foundation/plan.md (tech stack, structure, ADR table, NFR, risks, constitution check)
  - specs/001-gurujee-foundation/data-model.md (entities 9+10: automation_log, notification_cache)
  - history/adr/ADR-003-split-process-daemon-pwa-architecture.md (new — supersedes v1)
tests:
  - none
---

## Prompt

Answers to all 3 architecture decisions:

Decision 1 — APK framework:
PWA first, then Kivy APK in Phase 2.
Reasoning: Ship fast. A PWA served by the daemon on localhost:7171 opens in Chrome,
works offline, looks like an app, and requires zero Buildozer compile time.
Non-technical users tap a homescreen shortcut — they never know it's a browser.
Once the feature set is stable, wrap it as a real Kivy APK.
Update P6 of the constitution to add PWA as a permitted Phase 1 UI layer.

Decision 2 — Setup experience:
Option B — User installs the GURUJEE APK, the APK handles everything silently.
The GURUJEE launcher APK (thin Kivy shell) must:
1. Check if Termux is installed — if not, download and sideload it from bundled assets
2. Check if Termux:API is installed — install silently
3. Open Termux and run the bootstrap script automatically (via am start with extra)
4. Show a friendly progress screen in the APK while bootstrap runs in background
5. When daemon is ready on localhost:7171, load the PWA chat UI in a WebView
The user taps one APK. They see a loading screen. Then they see the chat. Done.
This IS the non-technical experience. Add this as a new principle amendment to P5 and P9.

Decision 3 — Automation scope for Phase 1:
All of these, in this priority order:
1. Open any app by name ("open WhatsApp") — am start via Shizuku
2. Control device settings — volume, WiFi, Bluetooth, flashlight, brightness
3. Send WhatsApp/SMS messages — input tap + type via Shizuku UI automation
4. Set alarms and reminders — am start + input automation into Clock app
5. Read notifications aloud — termux-notification-list + ElevenLabs TTS

The automation agent receives natural language from the AI, which converts it to
structured tool calls, which the automation agent executes via Shizuku shell commands.

---

Additional architecture decisions to lock in now:

The daemon architecture is now split-process (revise ADR-003):
- DAEMON: Python asyncio (gateway_daemon.py) runs all agents + FastAPI on localhost:7171
- PWA UI: served as static files by the daemon, loaded in APK WebView
- TUI: kept for developer/admin use only, launched with: python -m gurujee --tui
- The Textual TUI is no longer the primary user interface — demote it to dev tool

The FastAPI server on the daemon must expose:
- POST /chat — send message, get streaming response (SSE)
- GET  /agents — agent status (soul, memory, heartbeat, cron, user_agent)
- POST /automate — direct automation command
- GET  /notifications — recent notifications
- WebSocket /ws — real-time push (call events, automation results, agent updates)

The PWA chat UI must:
- Look like WhatsApp / iMessage — chat bubbles, not a terminal
- Voice input button (Web Speech API for STT in browser, or send audio to /transcribe)
- Work fully offline after first load (service worker cache)
- Show agent status as a subtle status bar (not a full panel — that's TUI territory)

Now update the following before running /sp.tasks:
1. Amend constitution P5 and P9 to reflect the APK-first non-technical install flow
2. Revise ADR-003 to split-process (daemon + PWA, TUI as dev tool only)
3. Add FastAPI and WebSocket to the plan tech stack
4. Add automation_agent.py and gurujee/automation/ to the plan
5. Add gurujee/server/ (FastAPI app + WebSocket + static PWA files) to the plan
6. Update data model with: automation_log table, notification_cache table
7. Then run /sp.tasks

## Response snapshot

All 7 updates executed in sequence:
1. Constitution P5 amended — Launcher APK zero-touch bootstrap sequence added; terminal removed from user flow.
2. Constitution P6 amended — PWA + FastAPI/uvicorn added as permitted Phase 1 stack; TUI demoted to dev tool; security rule added (127.0.0.1 only).
3. Constitution P9 amended — Launcher APK is now canonical non-technical install path; developer path (install.sh) retained.
4. Constitution version bumped to 1.1.0, Last Amended 2026-04-12, sync impact report updated.
5. ADR-003 fully superseded — new ADR-003 v2 documents split-layer architecture with full architecture diagram, RAM budget revision, process model table, alternatives considered, and revisit triggers.
6. plan.md updated — summary, tech stack, project structure (server/, automation/, launcher/), ADR table, NFR budget, risks, and constitution check all revised.
7. data-model.md extended — entities 9 (AutomationLog) and 10 (NotificationCache) added with full schemas, indices, retention rules, and entity relationships updated.

## Outcome

- ✅ Impact: All 7 pre-tasks artifacts updated and internally consistent. Architecture is now locked for /sp.tasks: split-layer daemon + FastAPI + PWA; Shizuku automation; Launcher APK; TUI as dev tool. Non-technical user flow is fully specified.
- 🧪 Tests: none (planning/architecture session)
- 📁 Files: constitution.md, plan.md, data-model.md, ADR-003 (new file)
- 🔁 Next prompts: /sp.tasks — generate tasks.md from updated plan + spec
- 🧠 Reflection: The architecture shift from single-process TUI to split-layer PWA is the correct decision. The PWA-first approach lets non-technical users interact via a familiar chat interface while keeping the Python daemon as the intelligence layer. The ADR-003 v2 RAM budget analysis (daemon 38 MB + uvicorn 12 MB = exactly 50 MB) is a critical constraint that must be validated by profiling on real hardware before merge.

## Evaluation notes (flywheel)

- Failure modes observed: None — all 7 updates completed without conflict. Plan structure was well-prepared from prior sessions.
- Graders run and results (PASS/FAIL): Constitution check re-run mentally: P1 borderline (profile required), P2–P10 all PASS.
- Prompt variant (if applicable): User provided highly structured input with explicit decisions and file change list — ideal prompt format for architecture sessions.
- Next experiment (smallest change to try): After /sp.tasks, verify that the automation task list covers all 5 automation priorities (open app, device settings, UI input, alarms, notifications) with explicit Shizuku command examples per task.
