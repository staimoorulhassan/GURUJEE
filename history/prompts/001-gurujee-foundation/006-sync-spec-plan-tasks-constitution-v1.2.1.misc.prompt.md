---
id: 006
title: Sync Spec Plan Tasks Constitution v1.2.1
stage: misc
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: /sp.analyze (remediation pass)
labels: ["constitution-sync","fix","allowlist","heartbeat","pollinations","C1","C2","C3","C4","C5","I1","I2","I3"]
links:
  spec: specs/001-gurujee-foundation/spec.md
  ticket: null
  adr: history/adr/ADR-005.md
  pr: null
files:
  - specs/001-gurujee-foundation/spec.md
  - specs/001-gurujee-foundation/plan.md
  - specs/001-gurujee-foundation/tasks.md
  - gurujee/agents/heartbeat_agent.py
  - gurujee/ai/client.py
  - config/security.yaml
  - config/models.yaml
  - .specify/memory/constitution.md
  - gurujee/setup/wizard.py
  - README.md
tests:
  - tests/test_heartbeat_agent.py (43 passed)
  - tests/test_ai_client.py (passed)
  - tests/test_keystore.py (passed)
---

## Prompt

/sp.analyze with explicit remediation instructions: fix 5 CRITICAL + 2 HIGH + 3 MEDIUM issues
found in the previous analysis pass. Includes: C1-C5 (constitution P2/P4 v1.2.0 drift),
I1-I5 (heartbeat 30s/10s contradiction, stale P3 evidence, US numbering swap, plan stale
references), A3 (SMS Phase contradiction), U2 (interrupted stream spec), U1 (T069 RAM
profiling), STOP HOOK ERROR, and Pollinations API key (Parts 1-10).

## Response snapshot

All 10 files modified, committed as d77e4f4. 43/43 relevant tests pass. 1 pre-existing
failure in test_build_apk_workflow.py (CI artifact path assertion) — unrelated to changes.

Key changes executed:
- C1+C4: spec FR-012/FR-013 updated to provider/model-id format; tasks T005 rewritten for full catalogue
- C2+C3: spec FR-022 updated to dynamic allowlist; tasks T067 updated; client.py _build_allowlist() now reads config/security.yaml
- C5: config/security.yaml created (4 anchors + pin_policy + keystore policy); T075 added to tasks.md
- I1: heartbeat PING_INTERVAL 8s, PONG_TIMEOUT 2s (10s worst-case satisfies SC-007)
- I2: plan.md P3 row corrected for Phase 1 automation scope
- I3: tasks.md Phase 5 = US4 (PWA), Phase 6 = US3 (Device Control) — matches spec.md
- I4/I5: plan.md P2 row + security architecture updated for ADR-005 and dynamic allowlist
- A3: FR-025 one-shot SMS scoped; Assumptions contradiction resolved
- U2: T033 interrupted-stream path specified
- Pollinations: models.yaml api_key_required=true; wizard.py pollinations_key step added; README updated
- Constitution: v1.2.1, P2 Pollinations auth updated

STOP HOOK ERROR: No hooks found in .claude/settings.local.json or ~/.claude/settings.json.
The encodings error is a Python 3.14 env issue (no stdlib path). Python 3.11 at
AppData/Programs/Python/Python311 works correctly. Hook location unknown — likely a plugin.

U1 (T069): data/benchmarks/idle-ram-001.txt shows "PENDING" — Windows dev estimate
35–45 MB. Authoritative ARM64/Termux measurement deferred to on-device test.

## Outcome

- ✅ Impact: All 5 CRITICAL constitution-drift issues resolved before implementation proceeds.
- 🧪 Tests: 43 passed (heartbeat, ai_client, keystore, soul, memory). 1 pre-existing fail (CI artifact path).
- 📁 Files: 10 files modified + committed (d77e4f4).
- 🔁 Next prompts: /sp.specify for FR-015 (PWA Settings Pollinations key UI); verify T069 on Android/Termux.
- 🧠 Reflection: Constitution amendments must cascade immediately to spec/plan/tasks. The SYNC IMPACT REPORT in constitution.md was correct but never acted on — pattern to fix: always run /sp.analyze after any constitution amendment.

## Evaluation notes (flywheel)

- Failure modes observed: Python 3.14 missing stdlib encodings (PYTHONHOME not set) — unblocked by switching to Python 3.11
- Graders run and results (PASS/FAIL): pytest 43/43 PASS (relevant tests)
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): Add Pollinations key field to PWA Settings panel (index.html + app.js) for in-UI key management
