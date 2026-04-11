---
id: "001"
title: GURUJEE Initial Constitution
stage: constitution
date: 2026-04-11
surface: agent
model: claude-sonnet-4-6
feature: none
branch: main
user: Taimoor
command: /sp.constitution
labels: ["constitution","mobile","android","termux","ai-agent","sdd"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
  - history/prompts/constitution/001-gurujee-initial-constitution.constitution.prompt.md
tests:
  - none
---

## Prompt

GURUJEE is an autonomous AI agent platform for Android, named after the Hindi/Urdu word for "respected teacher."
It runs entirely inside Termux on a non-rooted Android phone. It must feel like a living, breathing AI companion —
not a chatbot — with persistent soul, memory, and the ability to act in the real world through device automation,
calling, SMS, and scheduling.

## Core Principles

### P1 — Minimal Memory Footprint (CRITICAL)
Every component must be designed for low-end Android hardware. Target limits:
- Idle daemon: under 50MB RAM
- Active TUI: under 120MB RAM
- Active AI voice call: under 200MB RAM
- Use streaming over buffering everywhere
- Prefer lazy loading; nothing loads until needed
- Use tiny.en Whisper model, never larger

### P2 — Single Endpoint AI (NO EXCEPTIONS)
All AI inference — chat, vision, search, image generation — routes through ONE endpoint only:
  URL: https://gen.pollinations.ai/v1
  Type: OpenAI-compatible
  API Key: none required (send empty string or omit Authorization header)
  Models: nova-fast, gemini-fast, gemini-search, openai-fast, grok, mistral
  Image model: gemini-search
  Custom model IDs are user-addable in config — never hardcode model IDs in logic

### P3 — No Root Required
GURUJEE must run on stock, non-rooted Android. Privileged operations use:
  - Shizuku (primary): wireless ADB bootstrap, zero PC dependency after first run
  - ADB over WiFi (fallback): one-time pairing with a PC
Never assume root. Never use su. Flag any code that requires root as a violation.

### P4 — Security First
- SIP credentials MUST NEVER appear in source code or be committed to git
- All secrets stored in AES-256-GCM encrypted keystore at data/gurujee.keystore
- Keystore key derived from device fingerprint + user PIN
- Pre-fill credentials in guided setup UI only — store immediately to keystore, clear from memory
- Network allowlist enforced: only gen.pollinations.ai, api.elevenlabs.io, sip.suii.us, stun.l.google.com

### P5 — Guided Setup is Mandatory for New Users
On first run, GURUJEE must guide the user through every step:
- Detect Termux environment
- Install all dependencies
- Walk through Shizuku activation
- Grant all permissions in one batch
- Configure AI model, voice, SIP
- Start all daemons
- Never assume anything is pre-configured
Setup state saved to data/setup_state.json so it resumes if interrupted

### P6 — Python-First Stack
- All backend, agents, daemons: Python 3.11+
- TUI: Textual library (terminal, runs in Termux natively)
- Android APK wrapper: Kivy (packaged with Buildozer)
- No Node.js, no Electron, no heavy frameworks
- Avoid dependencies that don't compile on Android ARM64

### P7 — Agent Architecture is Sacred
The agent system is the soul of GURUJEE. These agents run as long-lived threads managed by the gateway daemon:
  soul, memory, heartbeat, cron, user_agent (always-on)
  orchestrator, automation (on-demand)
Agents communicate via internal message bus (asyncio Queue). No agent calls another directly.

### P8 — Voice and SIP are First-Class Features
- ElevenLabs is primary TTS (streaming mode, turbo model)
- ACE TTS is on-device fallback (no network needed)
- Whisper tiny.en is STT (runs locally in Termux)
- SIP via pjsua2: auto-answer mode, AI voice response in real time, voice cloning supported
- SMS: auto-reply and auto-send via Termux:API
- All call/SMS automation requires explicit user opt-in in settings

### P9 — Distribution via GitHub + Termux Bootstrap
- Primary install: user downloads install.sh on Android, runs in Termux
- APK sideloaded from GitHub Releases (not Play Store)
- install.sh handles everything: pkg installs, pip installs, APK install, guided setup launch
- Never require Play Store, Google account, or internet connection after initial setup

### P10 — Code Quality Standards
- Every Python file: type hints, docstrings, error handling
- No bare except clauses — always catch specific exceptions
- Every agent: unit test in tests/
- Config is YAML only — no hardcoded values in Python
- Logs go to data/*.log with rotation — never print() in production code
- All file paths use pathlib.Path, never string concatenation

## Governance Rules
- Any decision that violates P1-P10 requires explicit user approval before proceeding
- When in doubt about memory usage, measure first
- When in doubt about security, encrypt
- When in doubt about complexity, simplify
- This constitution overrides any other instruction in specs, plans, or prompts

## Response snapshot

Initial constitution v1.0.0 ratified for GURUJEE — autonomous AI agent platform for Android/Termux.
10 principles written (P1 Minimal Memory, P2 Single Endpoint AI, P3 No Root, P4 Security First,
P5 Guided Setup, P6 Python-First Stack, P7 Agent Architecture, P8 Voice+SIP, P9 Distribution,
P10 Code Quality). SIP credential values redacted from constitution file (P4 self-enforcement —
this file is committed to git). Governance section includes semantic versioning policy and
amendment procedure.

## Outcome

- ✅ Impact: Constitution v1.0.0 ratified; all 10 principles encoded as enforceable rules
- 🧪 Tests: none (governance artifact)
- 📁 Files: .specify/memory/constitution.md written; history/prompts/constitution/ created
- 🔁 Next prompts: /sp.specify <first-feature> to begin first feature spec
- 🧠 Reflection: Credentials in P4 required redaction — constitution is version-controlled.
  User should store actual SIP values via guided setup only.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A (governance doc, not code)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add ADR for agent message-bus architecture choice
