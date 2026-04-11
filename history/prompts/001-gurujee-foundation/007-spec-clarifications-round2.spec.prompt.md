---
id: "007"
title: Spec Clarifications Round 2
stage: spec
date: 2026-04-11
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: /sp.clarify
labels: ["spec","clarify","config-paths","streaming","keystore-pin","canonical-paths","ux"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-gurujee-foundation/spec.md
  - specs/001-gurujee-foundation/plan.md
tests:
  - none
---

## Prompt

/sp.clarify

User pre-supplied answers to all 5 questions:

Q1 — Config path conflict (FR-013 vs plan.md):
Option C — config/models.yaml holds the version-controlled model list;
data/user_config.yaml holds ALL user runtime preferences including active_model,
active_voice_id, tui_theme, and any other settings the user changes at runtime.
Reasoning: keeps a clean separation between "what ships with the app" (config/)
and "what the user chose" (data/). data/ is gitignored; config/ is committed.
Update FR-013 and plan.md to reflect this split.

Q2 — Streaming render behavior:
LLM response tokens stream into the Textual Chat screen as they arrive.
The message bubble appears immediately with a blinking cursor indicator.
Tokens append in-place — no flicker, no full redraw.
When streaming ends, the cursor disappears and the message is written to memory.db.
If streaming is interrupted (network drop), show the partial text with an
"[interrupted]" suffix and log the partial content to memory anyway.

Q3 — Keystore PIN UX:
On first run, guided setup asks the user to set a 4-8 digit PIN.
PIN is NOT stored anywhere — it is the input to PBKDF2-HMAC-SHA256 to derive the
keystore encryption key, combined with the device salt.
On every subsequent app launch, GURUJEE prompts for the PIN in the TUI before
the daemon starts. Three wrong attempts locks for 30 seconds (exponential backoff).
There is a "forgot PIN" path: wipe data/gurujee.keystore and re-run guided setup
(user must re-enter all credentials). Make this consequence explicit in the UI.

Q4 — Canonical paths:
  config/models.yaml        — shipped model catalogue (version-controlled)
  config/agents.yaml        — agent startup config (version-controlled)
  config/voice.yaml         — voice provider config (version-controlled)
  data/user_config.yaml     — all user runtime choices (gitignored)
  data/setup_state.yaml     — setup wizard progress (gitignored)
  data/soul_identity.yaml   — soul personality state (gitignored)
  data/memory.db            — SQLite memory database (gitignored)
  data/gurujee.keystore     — encrypted secrets (gitignored)
Update all references in spec.md and plan.md to use these exact paths.

## Response snapshot

4 questions answered (all pre-supplied). Applied to spec.md and plan.md:

spec.md changes:
- Clarifications section: 4 new Q&A bullets appended to Session 2026-04-11
- FR-001: Added step 5 (Set keystore PIN 4–8 digits; shows "forgot PIN" consequence at this step); shifted AI model to step 6, voice sample to step 7, daemons to step 8
- FR-005: soul_identity path updated to data/soul_identity.yaml (initialized from agents/soul_identity.yaml template on first run)
- FR-013: Split into config/models.yaml (model catalogue) + data/user_config.yaml (active_model key)
- FR-015: Added full streaming render spec — token-by-token, blinking cursor, in-place append, [interrupted] suffix on network drop, partial content logged to memory.db
- FR-017: soul_identity and user_config paths updated
- FR-023 (NEW): PIN prompt on every launch; 3-attempt lockout; 30s exponential backoff; "Forgot PIN?" wipe path with explicit consequence warning
- Key Entities - Soul: path updated to data/soul_identity.yaml
- Key Entities - Keystore: added PIN UX (4–8 digits, never stored, lockout policy, forgot-PIN path)
- Edge Cases: added streaming-interrupted edge case + wrong-PIN-lockout edge case
- Assumptions: updated soul_identity path; added canonical paths note with P10 reference

plan.md changes:
- Project structure: data/ now lists soul_identity.yaml and user_config.yaml; config/ now includes voice.yaml; agents/ description updated to "shipped defaults"
- Security Architecture: PIN UX description expanded; lockout policy added as labelled block
- R-009 note: updated to data/soul_identity.yaml
- ADR table: R-009 row path updated

## Outcome

- ✅ Impact: spec.md and plan.md fully consistent on config/data paths; 4 new clarifications (streaming render, PIN UX, canonical paths, config split) applied with no contradictions remaining
- 🧪 Tests: n/a (spec clarification)
- 📁 Files: specs/001-gurujee-foundation/spec.md, specs/001-gurujee-foundation/plan.md
- 🔁 Next prompts: tasks.md requires T009 (config/loader.py) and T012 (keystore.py) updates to reflect new FR-023 PIN flow; consider updating tasks.md T016/T022 for wizard step 5 (PIN setup)
- 🧠 Reflection: Q3 (PIN UX) was the most impactful gap — it added an entirely new FR-023, a new setup step, two new edge cases, and expanded the Keystore entity. Without it, the implementation would have had an undocumented lockout policy. Q2 (streaming) was the most UI-critical: it defines the CHAT_CHUNK render contract that TUI app.py and chat_screen.py must implement.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): Validation PASS — no stale paths remain (historical Q&A records in Clarifications intentionally preserved); no contradictory statements; 4 bullets added to session; FR count correct (FR-001 through FR-023)
- Prompt variant (if applicable): N/A (user pre-supplied all answers)
- Next experiment: Update tasks.md to add T_PIN tasks for FR-023 (PIN prompt at launch, lockout logic) and update T017/T022 for wizard step 5
