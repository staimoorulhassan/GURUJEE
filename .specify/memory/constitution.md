<!--
SYNC IMPACT REPORT
==================
Version change  : 1.1.1 → 1.2.0
Bump rationale  : MINOR — P2 materially amended: single-endpoint restriction replaced
                  by multi-provider catalogue system (ADR-005). New providers, auth
                  rotation, and two-stage failover constitute a scope expansion.
Added sections  : none
Removed sections: none
Modified        :
  P2 — "Single Endpoint AI" renamed to "Provider Catalogue AI".
       Pollinations retained as zero-key default. Multi-provider format
       "provider/model-id" added. Auth from keystore only. Dynamic allowlist
       from provider base_url fields. Two-stage failover documented.
       See ADR-005 for full decision record.
  P4 — Allowlist note updated: dynamic (from provider catalogue) instead of
       hardcoded 4-host list.
Templates       :
  .specify/templates/plan-template.md   ✅ no changes required
  .specify/templates/spec-template.md   ✅ no changes required
  .specify/templates/tasks-template.md  ✅ no changes required
Deferred TODOs  : T069 idle RAM profiling still unpaid — measure actual RSS before Phase 3.

--- Previous (1.1.1 → 1.2.1) ---
Version change  : 1.2.0 → 1.2.1
Bump rationale  : PATCH — factual correction: Pollinations now requires a free API key.
                  P2 default updated from "zero-key" to "free key at auth.pollinations.ai".
Modified        :
  P2 — Default provider note updated: Auth now requires POLLINATIONS_API_KEY in keystore.
       Bearer token header MUST be sent. Get free key at https://auth.pollinations.ai.
Cascade         :
  config/models.yaml — pollinations api_key_required: true, auth_env added.
  spec.md FR-012/FR-013 — provider catalogue format documented.
  spec.md FR-022 — dynamic allowlist (security.yaml + models.yaml).
  spec.md FR-025 — SMS scoped to one-shot Phase 1.
  plan.md — P2/P3 checks updated, heartbeat NFR corrected (8s), security diagram updated.
  tasks.md — T005/T033/T067 updated, T075 added, US3/US4 labels corrected.
  heartbeat_agent.py — PING_INTERVAL 30s → 8s, PONG_TIMEOUT 5s → 2s.
  config/security.yaml — anchor hosts + pin_policy + keystore policy added.
  gurujee/ai/client.py — _build_allowlist() reads from config/security.yaml.
Deferred TODOs  : T069 idle RAM profiling pending on-device Android/Termux measurement.
                  wizard.py and PWA settings panel need Pollinations key entry UI.

--- Previous (1.1.0 → 1.1.1) ---
Version change  : 1.0.0 → 1.1.0
Bump rationale  : MINOR — three principles materially amended (P5, P6, P9).
Modified        :
  P5 — Guided Setup expanded to APK-first zero-touch flow for non-technical users.
  P6 — PWA added as Phase 1 permitted UI layer. TUI demoted to developer/admin tool.
  P9 — Distribution path changed to Launcher APK as canonical non-technical path.
Deferred TODOs  : ADR-003 revised (split-process). plan.md updated. data-model.md extended.
⚠️  SECURITY FLAG: P4 originally contained live SIP credentials
    (domain, username, caller_id). Those values have been REDACTED
    from this file because constitution.md is committed to git, which
    would violate P4's own rule. Store actual values in the guided
    setup flow → data/gurujee.keystore only.
⚠️  P6 SECURITY ADDITION: FastAPI MUST bind to 127.0.0.1 only — never 0.0.0.0.
-->

# GURUJEE Constitution

GURUJEE is an autonomous AI agent platform for Android — named after the Hindi/Urdu word for
"respected teacher." It runs entirely inside Termux on a non-rooted Android phone and is
designed to feel like a living, breathing AI companion with persistent memory and the ability
to act in the real world through device automation, calling, SMS, and scheduling.

## Core Principles

### P1 — Minimal Memory Footprint (CRITICAL)

Every component MUST be designed for low-end Android hardware.

Hard limits (enforced; not advisory):

| State              | RAM ceiling |
|--------------------|-------------|
| Idle daemon        | 50 MB       |
| Active TUI         | 120 MB      |
| Active AI voice    | 200 MB      |

Rules:
- Streaming MUST be used in place of buffering everywhere data flows.
- Lazy loading is mandatory — nothing loads until needed.
- STT MUST use `whisper tiny.en`; larger Whisper variants are prohibited.
- Any component that exceeds its ceiling MUST be profiled and optimised before merge.

### P2 — Provider Catalogue AI (AMENDED v1.2.0)

All AI inference MUST use the provider catalogue defined in `config/models.yaml`.
Pollinations is the zero-key default — GURUJEE MUST work out of the box with no configuration.

**Model format**: `provider/model-id` (e.g. `"anthropic/claude-opus-4-6"`, `"ollama/llama3.3"`).

**Provider tiers** (see `config/models.yaml` for full catalogue):
- **Tier 1 — Built-in**: pollinations, openai, anthropic, google, opencode, zai,
  vercel-ai-gateway, kilocode. No `models.providers` config needed — set key in keystore.
- **Tier 2 — Custom**: ollama, openrouter, deepseek, groq, mistral, and 20+ more.
  Defined by `base_url` + `api_compat` in `models.yaml`.

**Default** (free provider, API key required):
```
pollinations/nova-fast  →  https://gen.pollinations.ai/v1  (OpenAI-compatible)
Auth: POLLINATIONS_API_KEY stored in keystore (free key at https://auth.pollinations.ai).
The Authorization: Bearer <key> header MUST be sent for all Pollinations requests.
```

**Rules:**
- Model IDs MUST NOT be hardcoded in logic; they MUST come from user config or `agent_model_routing`.
- All API keys MUST be stored in `data/gurujee.keystore` (AES-256-GCM). NEVER in config files or env vars.
- Key resolution priority (highest first): `GURUJEE_LIVE_{PROVIDER}_KEY` → `{PROVIDER}_API_KEYS`
  (comma list) → `{PROVIDER}_API_KEY_1/_2` → `{PROVIDER}_API_KEY`. All read from keystore.
- Outbound hosts are dynamically allowlisted from all `base_url` fields in `config/models.yaml`
  plus the security anchors in `config/security.yaml`.
- Two-stage failover: Stage 1 = auth profile rotation within provider (exponential cooldown);
  Stage 2 = advance to next model in `model_fallbacks` list (only when all Stage 1 profiles
  are exhausted).
- New providers may be added to `models.yaml` without governance approval (P2 no longer
  restricts to a single endpoint). Removal of Pollinations as default requires governance approval.
- See ADR-005 for full decision record and alternatives considered.

### P3 — No Root Required

GURUJEE MUST run on stock, non-rooted Android.

Privileged operations MUST use one of:
- **Shizuku** (primary) — wireless ADB bootstrap, zero PC dependency after first run.
- **ADB over WiFi** (fallback) — one-time PC pairing only.

Rules:
- `su` and root-only syscalls are prohibited.
- Any code path that requires root MUST be flagged as a P3 violation and blocked from merge.

### P4 — Security First

Rules:
- SIP credentials (domain, username, caller ID) MUST NEVER appear in source code or be
  committed to git. Actual values live in `data/gurujee.keystore` only.
- All secrets MUST be stored in an AES-256-GCM encrypted keystore at `data/gurujee.keystore`.
- The keystore encryption key MUST be derived from device fingerprint + user PIN; no static keys.
- The guided setup UI MAY pre-fill credentials temporarily — they MUST be written to the
  keystore and cleared from memory before the setup step completes.
- Outbound network MUST be allowlisted. The permitted host list is dynamic: it is derived
  from all `base_url` fields in `config/models.yaml` plus the security anchors in
  `config/security.yaml` (`api.elevenlabs.io`, `sip.suii.us`, `stun.l.google.com`,
  `api.deepgram.com`). See `gurujee/ai/client.py::_build_allowlist()`.
- Any connection to a host not in `models.yaml` or `security.yaml` requires explicit user
  approval + governance sign-off.

### P5 — Zero-Touch Setup for Non-Technical Users (AMENDED 1.1.0)

GURUJEE MUST be installable and operational by a non-technical user with a single tap.
The entry point is the **GURUJEE Launcher APK** — a thin Kivy shell that handles everything.

**Launcher APK bootstrap sequence** (executed automatically, no user CLI required):

1. Check if Termux is installed → if not, sideload it from bundled assets silently
2. Check if Termux:API is installed → install silently
3. Open Termux and inject the bootstrap script automatically (`am start` with `--es cmd` extra)
4. Show a friendly progress screen in the APK while bootstrap runs in the background
5. Poll `localhost:7171/health` until the daemon is ready (max 3 min, with progress feedback)
6. When daemon is ready, load the PWA chat UI in an in-app WebView
7. User sees a chat interface — never a terminal, never a command prompt

**Daemon bootstrap script** (runs inside Termux, triggered by APK):

1. Install required packages (`pkg install`)
2. Activate Shizuku
3. Install GURUJEE Accessibility Service APK from GitHub Releases (SHA-256 verified)
4. Grant all required Android permissions in one batch
5. Set keystore PIN (guided via PWA UI once daemon is up, not terminal)
6. Configure AI model
7. Voice sample recording (optional, consent-gated)
8. Start all daemons + FastAPI server on `localhost:7171`

Rules:
- Setup MUST never assume anything is pre-configured.
- Setup state MUST be persisted to `data/setup_state.yaml` so it resumes if interrupted.
- A feature is NOT shippable if it breaks or bypasses the guided setup flow.
- The terminal (TUI) MUST NOT be required at any point in the non-technical user flow.
- All user-facing setup prompts (PIN entry, consent gates, model selection) MUST be
  presented in the PWA UI once the daemon reaches its minimal-ready state, NOT in the
  terminal.

### P6 — Python-First Stack (AMENDED 1.1.0)

Permitted technologies:

| Layer              | Technology                                            | Phase |
|--------------------|-------------------------------------------------------|-------|
| Backend / agents   | Python 3.11+                                          | All   |
| REST / WS server   | FastAPI + uvicorn on `localhost:7171`                 | 1+    |
| Primary user UI    | PWA (HTML/CSS/JS, served by daemon, loaded in WebView)| 1+    |
| TUI                | Textual — developer/admin tool only (`--tui` flag)    | 1+    |
| Launcher APK       | Kivy (thin shell: WebView + bootstrap orchestration)  | 1+    |
| Full Android APK   | Kivy packaged with Buildozer (wraps PWA in native shell)| 2+  |
| Device automation  | Shizuku shell (`am`, `input`, `settings`, `dumpsys`)  | 1+    |

Rules:
- Node.js, Electron, and heavy JVM/native frameworks are prohibited.
- Dependencies MUST compile on Android ARM64 in Termux without root.
- Any new dependency MUST be verified for ARM64 compatibility before it is added.
- The PWA MUST work fully offline after first load (service worker cache).
- The TUI is a dev/admin tool — it MUST NOT be the primary user-facing interface.
- FastAPI server MUST bind to `127.0.0.1` only — never `0.0.0.0` (security requirement).

### P7 — Agent Architecture is Sacred

The agent system is the soul of GURUJEE. Agents run as long-lived threads managed by the
gateway daemon and communicate exclusively via the internal async message bus (asyncio Queue).

**Always-on agents** (MUST restart automatically on failure):

| Agent        | Responsibility                                    |
|--------------|---------------------------------------------------|
| `soul`       | Identity, personality, system prompt injection    |
| `memory`     | SQLite persistence, context injection             |
| `heartbeat`  | Watchdog — auto-restarts dead services            |
| `cron`       | Scheduler for reminders and automations           |
| `user_agent` | User profile, contacts, preferences               |
| `automation` | Android UI/device control via Shizuku             |

> `automation` reclassified always-on in v1.1.1 (ADR-004). PWA chat UI requires instant
> response to automation commands; cold-start delay (~2–3s) is unacceptable. RAM overhead
> (~3–5 MB idle) verified within the P1 50 MB ceiling. Measure RSS before Phase 3.

**On-demand agents**:

| Agent          | Responsibility                                  |
|----------------|-------------------------------------------------|
| `orchestrator` | Spawns sub-agents for parallel tasks            |

Rules:
- No agent MAY call another agent directly. All inter-agent communication MUST go through the
  message bus.
- Adding a new always-on agent requires governance approval (it affects idle RAM budget).

### P8 — Voice and SIP are First-Class Features

| Capability       | Technology                                 | Fallback              |
|------------------|--------------------------------------------|-----------------------|
| TTS              | ElevenLabs streaming (turbo model)         | ACE TTS (on-device)   |
| STT              | Whisper tiny.en (local, Termux)            | none                  |
| SIP calls        | pjsua2 — auto-answer + AI voice response   | none                  |
| SMS              | Termux:API auto-reply / auto-send          | none                  |

Rules:
- ElevenLabs MUST be called in streaming mode; buffered mode is prohibited (P1 violation).
- All call and SMS automation MUST require explicit user opt-in in settings before activating.
- Voice cloning is supported but MUST be gated behind a prominent consent prompt.

### P9 — Distribution via GitHub + Launcher APK (AMENDED 1.1.0)

GURUJEE MUST be installable on a fresh Android device by a non-technical user
with a single APK tap — no terminal, no Play Store, no PC required.

**Canonical install path (non-technical user):**
1. User downloads `GURUJEE.apk` from GitHub Releases and sideloads it.
2. The Launcher APK handles everything: Termux install, bootstrap, daemon start, PWA load.
3. User sees a chat interface. Setup is complete.

**Canonical install path (developer/power user):**
1. Clone the repo or download `install.sh`.
2. Run `install.sh` in Termux — idempotent, handles all deps.
3. Launch with `python -m gurujee` (TUI mode) or `python -m gurujee --headless` (daemon only).

**Distribution rules:**
- The Launcher APK is distributed from GitHub Releases only — not the Play Store.
- `install.sh` MUST remain idempotent and fully functional as the developer path.
- The Launcher APK MUST bundle Termux F-Droid build assets (no Play Store dependency).
- After initial setup, no internet connection should be required for core local features.
- The APK MUST display the SHA-256 of all sideloaded packages before installing them.

### P10 — Code Quality Standards

Rules:
- Every Python file MUST have type hints, docstrings, and explicit error handling.
- Bare `except` clauses are prohibited; always catch specific exception types.
- Every agent MUST have a corresponding unit test under `tests/`.
- Configuration is YAML only; no hardcoded values in Python source.
- Logs go to `data/*.log` with rotation; `print()` in production code is prohibited.
- All file paths MUST use `pathlib.Path`; string concatenation for paths is prohibited.

## Governance

- This constitution supersedes all other instructions in specs, plans, tasks, or prompts.
- Any action that violates P1–P10 MUST NOT proceed without explicit user approval.
- Decision heuristics (apply in order):
  1. **Memory doubt** → measure first, then decide.
  2. **Security doubt** → encrypt / redact, then proceed.
  3. **Complexity doubt** → simplify; justify complexity before adding it.
- Amendments follow semantic versioning:
  - **MAJOR**: principle removed, renamed, or made backward-incompatible.
  - **MINOR**: new principle added or an existing one materially expanded.
  - **PATCH**: clarifications, wording, typo fixes.
- All amendments MUST update `Last Amended` and increment `Version` accordingly.
- PRs that touch architecture or cross-cutting concerns MUST include a Constitution Check
  confirming no P1–P10 violations, or explicitly documenting approved exceptions.

**Version**: 1.2.1 | **Ratified**: 2026-04-11 | **Last Amended**: 2026-04-14
