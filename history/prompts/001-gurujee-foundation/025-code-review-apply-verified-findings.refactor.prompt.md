---
id: "025"
title: Apply verified code review findings
stage: refactor
date: 2026-04-14
surface: agent
model: claude-sonnet-4-6
feature: 001-gurujee-foundation
branch: 001-gurujee-foundation
user: Taimoor
command: inline code review findings
labels: ["security", "buildozer", "ci", "keystore", "allowlist", "heartbeat", "wizard", "docs", "ruff"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .github/workflows/build-apk.yml
  - config/agents.yaml
  - gurujee/ai/client.py
  - gurujee/agents/heartbeat_agent.py
  - gurujee/keystore/keystore.py
  - gurujee/setup/wizard.py
  - README.md
  - tests/test_install_sh.py
  - specs/001-gurujee-foundation/spec.md
  - specs/001-gurujee-foundation/tasks.md
  - specs/001-gurujee-foundation/plan.md
tests:
  - syntax check (ast.parse) on all modified Python files — PASS
---

## Prompt

Verify each finding against the current code and only fix it if needed.

[14 inline findings across CI, security, agent config, wizard, docs, and tests]

## Response snapshot

Verified all 14 findings against the actual code. All confirmed valid. Applied minimal fixes:

1. **CI idempotency**: Skip cmdline-tools download if already present; always re-create shim symlink.
2. **PBKDF2 iterations**: keystore.py 480k→260k; plan.md diagram and risk register updated.
3. **security.yaml enforcement**: `_build_allowlist()` now reads `user_approved_hosts` and `_session_allowed_hosts`; narrow bare except; log allowlist build to security.log. `_check_allowlist()` reads policy, logs violations, handles `allow_once` (session-only set), fails closed for `block`/`prompt_user`.
4. **HeartbeatAgent**: loads `ping_interval_seconds`/`response_timeout_seconds` from agents.yaml in __init__; falls back to 8s/2s constants. Updated agents.yaml to 8s/2s to match SC-007.
5. **wizard.py Keystore TypeError**: now prompts user for PIN before instantiating Keystore; bare except narrowed to OSError/ValueError/KeystoreError.
6. **README.md**: non-existent UI path removed.
7. **test_install_sh.py**: f-string (F541) and `l` variable (E741) fixed.
8. **spec.md**: Pollinations auth assumption updated.
9. **tasks.md**: Phase 5/6 headers (US3/US4) corrected; Phase 9 range updated to T066–T075 (10 tasks, total 75).
10. **plan.md**: T069 status done; ping interval entry clarified with error path; iterations 480k→260k.

## Outcome

- ✅ Impact: All confirmed review findings fixed; no speculative changes made
- 🧪 Tests: ast.parse syntax check passed on all 5 modified Python files
- 📁 Files: 11 files modified
- 🔁 Next prompts: Run full pytest suite; commit and push; address Termux install failure bug
- 🧠 Reflection: "verify before fixing" caught that heartbeat_agent already used instance attrs correctly — only the agents.yaml loading and reconciliation were missing

## Evaluation notes (flywheel)

- Failure modes observed: none — all findings were real after verification
- Graders run and results (PASS/FAIL): PASS — stage refactor correct, routing to feature
- Prompt variant (if applicable): inline review comment format
- Next experiment (smallest change to try): Add integration test for _check_allowlist() policy branching
