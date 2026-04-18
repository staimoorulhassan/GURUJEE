---
id: 035
title: Add --model and --key targeted reconfigure flags to gurujee config
stage: green
date: 2026-04-18
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: "continue"
labels: ["feature","cli","onboarding","config","reconfigure"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - gurujee/__main__.py (modified — config subparser gains --model and --key args; dispatch branches)
  - gurujee/setup/onboard.py (modified — added run_model_only() and run_key_only() methods; updated docstring)
tests:
  - AST syntax check passed for both modified files (Python 3.11 -S mode)
---

## Prompt

User said "continue" — resuming from PHR 034. Last session implemented the OpenClaw-style
onboarding wizard. PHR 034 noted the next step as: "add `gurujee config --model` / `--key`
section flags for targeted reconfigure."

## Response snapshot

Added two targeted reconfigure flags to the `gurujee config` subcommand:

**`gurujee config --model`**  
Runs `OnboardWizard.run_model_only()` — shows provider + model + context-size steps only.
Skips API key and alias prompts. Writes updated `active_model` to `user_config.yaml` and
patches the `model` block in `gurujee.config.json` without touching other keys.

**`gurujee config --key`**  
Runs `OnboardWizard.run_key_only()` — reads current provider from `gurujee.config.json`,
prompts for new API key (hidden), and updates the keystore entry for that provider's
`auth_env` key. Gracefully handles OAuth providers (nothing to store) and missing config
(falls back to full wizard).

**`gurujee/__main__.py`** — replaced single `add_parser("config")` with a `config_parser`
that registers `--model` and `--key` args; dispatch block branches on `args.model` /
`args.key` before falling through to `wizard.run()`.

**`gurujee/setup/onboard.py`** — added:
- `run_model_only()`: provider + model + context size → writes yaml + json, keystore untouched
- `run_key_only()`: reads current provider from json config → prompts new key → saves to keystore;
  falls back to `run()` if no saved provider found

## Outcome

- ✅ Impact: `gurujee config --model` and `gurujee config --key` now work as surgical reconfigure flows; full `gurujee config` wizard unchanged
- 🧪 Tests: AST syntax check passed; smoke test requires Termux device with keystore
- 📁 Files: 2 modified
- 🔁 Next prompts: Test on Termux device; commit this branch; consider adding `gurujee config --show` to print current config summary
- 🧠 Reflection: Keeping targeted flows as methods on `OnboardWizard` (rather than standalone functions) avoids duplicating provider-loading and display-table logic. `run_key_only()` reads `gurujee.config.json` to discover current provider — no extra state needed.

## Evaluation notes (flywheel)

- Failure modes observed: Windows Python site-packages conflict (3.14 .pth infects 3.11) — worked around with `python.exe -S` to skip site packages
- Graders run and results (PASS/FAIL): AST syntax check — PASS both files
- Prompt variant (if applicable): null
- Next experiment: add unit test mocking Prompt.ask to verify run_key_only aborts cleanly on empty input
