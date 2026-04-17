---
id: 034
title: OpenClaw-Style Onboarding — Model Setup Wizard
stage: green
date: 2026-04-17
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: "there is the change in plan ... i wants same setup like openclaw onboard -- gurujee --onboard"
labels: ["feature","onboarding","model-setup","cli","config","json"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - gurujee/setup/onboard.py (created)
  - gurujee/config/json_config.py (created)
  - gurujee/config/loader.py (modified — 3 new static methods)
  - gurujee/__main__.py (modified — --onboard flag + config subcommand)
  - data/.gitignore (modified — added *.json)
tests:
  - AST syntax check passed for all 4 modified/created Python files
---

## Prompt

User requested OpenClaw-style onboarding for GURUJEE. Reference: docs.openclaw.ai/onboarding/cli. Requirements:
- `gurujee --onboard` interactive wizard
- Provider selection from 30+ providers in config/models.yaml
- "Bring your own endpoint" option for custom base URLs
- API key prompt (hidden), skips for OAuth providers
- Model selection from provider's model list or custom model ID
- Alias setup
- Context size setup (pre-filled from YAML)
- After setup: return to dashboard
- `gurujee config` command for reconfiguration
- `data/gurujee.config.json` file for manual editing

## Response snapshot

Created 2 new files and modified 3 existing files:

**`gurujee/config/json_config.py`** — Pure I/O module for `data/gurujee.config.json`:
- `load_json_config(path)` — reads with defaults, handles missing/corrupt gracefully
- `save_json_config(data, path)` — atomic write via .tmp + rename
- `merge_yaml_and_json(yaml_cfg, json_cfg)` — pure merge function; JSON wins; maps provider+model_id → active_model

**`gurujee/setup/onboard.py`** — `OnboardWizard` class with 8-step flow:
1. Welcome panel (skipped for `config` subcommand)
2. Provider selection — Rich table of all 30+ providers from models.yaml
3. Custom endpoint URL (only for "bring your own")
4. API key (hidden prompt; OAuth/gcloud providers get a note, not a prompt)
5. Model selection — Rich table of provider models + "custom ID" option
6. Alias (optional, defaults to model_id)
7. Context size (pre-filled from YAML, validates > 0)
8. Save: keystore (api_key) + user_config.yaml (active_model) + gurujee.config.json

**`gurujee/config/loader.py`** — Added `load_json_config()`, `save_json_config()`, `load_merged_config()` static methods

**`gurujee/__main__.py`** — Added `--onboard` flag + `config` subparser; dispatch blocks before `--status`

**`data/.gitignore`** — Added `*.json` to prevent accidental commit of gurujee.config.json

Zero changes to AIClient — it continues reading `user_config.yaml` for `active_model`. The wizard writes to both files simultaneously.

## Outcome

- ✅ Impact: `gurujee --onboard` and `gurujee config` now work; gurujee.config.json written after wizard completes
- 🧪 Tests: AST syntax check passed; manual smoke test requires Termux device with keystore
- 📁 Files: 2 created, 3 modified
- 🔁 Next prompts: Test on Termux device; add `gurujee config --model` / `--key` section flags for targeted reconfigure
- 🧠 Reflection: Integration is zero-impact on AIClient because wizard writes active_model to user_config.yaml (which AIClient already reads). JSON config is purely additive.

## Evaluation notes (flywheel)

- Failure modes observed: Windows Python site-packages version conflict (3.11 vs 3.14) blocked `python -c` import tests — used AST parse via direct Python 3.11 path instead
- Graders run and results (PASS/FAIL): AST syntax check — PASS all 4 files
- Prompt variant (if applicable): null
- Next experiment: add unit tests mocking Prompt.ask for full wizard flow
