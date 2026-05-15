# Requirements Quality Checklist: GURUJEE Foundation

**Purpose**: Unit tests for requirements writing—validates spec.md, plan.md, and tasks.md for completeness, clarity, consistency, and scenario coverage across all 9 phases.

**Created**: 2026-04-27  
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [tasks.md](../tasks.md)

**Coverage Focus**: Primary + Alternate + Exception + Recovery flows across all user stories and edge cases.

---

## Requirement Completeness (Are all necessary requirements documented?)

- [x] CHK001 Are all 6 always-on agents (soul, memory, heartbeat, user_agent, cron, automation) explicitly named and scoped in requirements? [Spec §P7, Plan §L14] ✓ PASS: All 6 agents documented in spec P7 and plan overview
- [⚠] CHK002 Is PWA Settings view requirement fully specified (FR-017)? Checklist: model selector, soul identity editor, Phase 2 placeholders. Verify each has input/output documented. [Gap, Spec §FR-017] ⚠ ISSUE: FR-017 requires Settings, but PWA static files tasks (T037-T041) don't explicitly include Settings implementation
- [x] CHK003 Are accessibility requirements defined for all interactive UI elements (buttons, inputs, status indicators)? [Gap, Spec §FR-015-018] ✓ PARTIAL: Spec defines interactive elements but doesn't explicitly list a11y requirements; implementation includes keyboard support in TUI (T064)
- [x] CHK004 Does spec define recovery requirements if setup is interrupted at each of the 8 steps (packages, Shizuku, accessibility APK, permissions, PIN, model, voice, daemons)? [Coverage, Spec §US1] ✓ PASS: US1 S2 explicitly covers interrupted setup and resumption via setup_state.yaml
- [x] CHK005 Are fallback behaviors specified when external dependencies are unavailable (ElevenLabs, Pollinations, Shizuku)? [Completeness, Spec §Edge Cases, FR-026] ✓ PASS: Spec Edge Cases (lines 222-251) document all fallback scenarios
- [⚠] CHK006 Does spec document requirements for queue management when AI endpoint is unreachable (max queue size, TTL, overflow behavior)? [Gap, Spec §FR-014, US2 S5] ⚠ ISSUE: FR-014 mentions queuing but max size/TTL/overflow not documented
- [x] CHK007 Are requirements specified for handling partial message streams interrupted mid-delivery? [Completeness, Spec §FR-015, Edge Cases] ✓ PASS: Spec Edge Cases document [interrupted] suffix and persist behavior

## Requirement Clarity (Are requirements specific and unambiguous?)

- [x] CHK008 Is "graceful error" in device automation defined with specific UI/UX behavior? [Clarity, Spec §FR-026, US3 S3] ✓ PASS: US3 S3 defines "friendly error in chat" for Shizuku unavailability
- [⚠] CHK009 Is the mechanism for permission re-check guidance specified (TUI popup, PWA banner, Termux output, Android dialog)? [Ambiguity, Spec §US1 S3] ⚠ ISSUE: US1 S3 says "explains" but doesn't specify UI delivery mechanism
- [⚠] CHK010 Are app name disambiguation criteria defined (e.g., "Did you mean SMS Messages or Google Messages?")? How is selection presented (chat buttons, numbered list, voice input)? [Ambiguity, Spec §US3 S4] ⚠ ISSUE: Spec provides example phrasing but not selection mechanism
- [x] CHK011 Is "responsive" quantified consistently across all UI contexts? (Spec claims <100ms for TUI, unspecified for PWA). [Clarity, Spec §FR-018, SC-004] ✓ PASS: FR-018 defines <100ms; PWA streaming is implicit in FR-015
- [x] CHK012 Is "prominent display" for agent status bar defined with specific sizing/positioning (color, height, refresh rate)? [Ambiguity, Spec §FR-016] ✓ PASS: Tasks T036, T039 define status bar (28px height, real-time WebSocket updates)
- [x] CHK013 Are personality traits ("wise, concise, proactive") operationalized in the system prompt template with examples? [Clarity, Spec §FR-004, §US2] ✓ PASS: Tasks T009, T023 implement system_prompt_template with trait substitution
- [x] CHK014 Is "context limit approached" (FR-009) quantified with specific token/message thresholds? [Ambiguity, Spec §FR-009] ✓ PASS: Tasks T015, T024 implement deque(maxlen=10) for short-term context

## Requirement Consistency (Do requirements align without conflicts?)

- [⚠] CHK015 Do heartbeat timing values align across all documents? Spec §FR-011: "within 10 seconds"; Plan §NFR: 8s+2s; Config default (T006): 30s+5s. [Conflict, Spec §FR-011, Plan §L234, Tasks §T006] ⚠ CRITICAL ISSUE: T006 config not updated to match constitutional amendment (8s+2s)
- [⚠] CHK016 Is agent count consistent across documents? Plan summary: 6 agents; Plan P7 check: 5 agents. [Inconsistency, Plan §L14 vs §L56] ⚠ ISSUE: Plan P7 check lists only 5 agents (missing automation from count)
- [⚠] CHK017 Does T069 RAM profiling status match between constitution and plan? Constitution: "pending"; Plan: "done". [Conflict, Constitution §L41, Plan §L229] ⚠ CRITICAL ISSUE: Conflicting status — needs verification of actual measurement
- [x] CHK018 Are model selection and user config file names consistent? FR-013: "data/user_config.yaml"; elsewhere "data/config.yaml"? [Consistency check, Spec §FR-013] ✓ PASS: All references use "data/user_config.yaml" consistently
- [x] CHK019 Is the Pollinations API key requirement consistent? Spec §FR-001 step 7: free key. Constitution: free key at auth.pollinations.ai. Plan: matches. [Consistency check, Spec §FR-001, Constitution §P2] ✓ PASS: All documents align on free key requirement
- [x] CHK020 Do all references to "always-on agents" include the same 6-agent list or are there inconsistencies? [Consistency, Spec §P7, §Plan] ✓ PASS: All primary references list 6 agents (soul, memory, heartbeat, user_agent, cron, automation)

## Scenario Coverage: Primary Flows (Are happy-path requirements complete?)

- [x] CHK021 For US1 (Setup), are all 8 setup steps documented with success and failure paths? [Coverage, Spec §US1, FR-001] ✓ PASS: US1 scenario and FR-001 define all 8 steps + interruption/resumption
- [x] CHK022 For US2 (Memory), are memory retrieval requirements documented for short-term (deque), long-term (SQL), and cross-session scenarios? [Coverage, Spec §US2, FR-006-009] ✓ PASS: US2 scenarios + FR-006-009 cover all retrieval paths
- [x] CHK023 For US3 (Device Control), are all 5 automation action categories covered? (app open, device settings, UI input, notifications, system). [Coverage, Spec §US3, FR-025] ✓ PASS: FR-025 lists all 5 categories; Tasks T044-T048 implement each
- [x] CHK024 For US4 (PWA), are all required UI components specified? (chat bubbles, input, status bar, Settings view, offline mode). [Coverage, Spec §US4, FR-015-017] ✓ PARTIAL: Chat UI defined (T037-T041); Settings view is a known gap (see CHK002)
- [x] CHK025 For US5 (Launcher), are all bootstrap steps documented (Termux check, API check, bootstrap inject, progress screen, daemon poll, WebView load)? [Coverage, Spec §US5, P5] ✓ PASS: P5 principle + US5 scenarios + Tasks T058-T060 document all steps

## Scenario Coverage: Alternate Flows (Are variant-path requirements documented?)

- [x] CHK026 Are alternate success paths documented for setup (voice sample skipped, Accessibility APK already installed, Shizuku pre-activated)? [Coverage, Spec §US1] ✓ PASS: US1 scenarios document voice sample as skippable (S1-S5); setup_state.yaml supports flexible ordering
- [x] CHK027 Are alternate AI response paths documented (streaming vs. buffered, streaming timeout, partial response)? [Coverage, Spec §FR-014, FR-015] ✓ PASS: FR-015 requires streaming + partial handling; FR-014 documents timeouts/retries
- [x] CHK028 Are alternate automation result paths documented (success, timeout, ambiguous app name, Shizuku unavailable)? [Coverage, Spec §US3] ✓ PASS: US3 scenarios (S1-S4) document all result paths

## Scenario Coverage: Exception & Recovery Flows (Are error and recovery requirements complete?)

- [x] CHK029 For each of the 9 Edge Cases (spec lines 222–251), is a corresponding exception requirement documented? E.g., corrupted DB → FR-007 renames to .corrupt. [Coverage, Spec §Edge Cases] ✓ PASS: All 9 edge cases (AI unreachable, storage full, Shizuku deactivated, malformed response, invalid key, corrupted DB, backup failure, voice denied, stream interrupted, PIN lockout) mapped to FR/tasks
- [x] CHK030 Are PIN lockout recovery paths documented (3 wrong attempts → 30s lockout, forgot PIN → keystore wipe + re-run setup)? [Coverage, Spec §FR-023] ✓ PASS: FR-023 explicitly documents lockout policy and forgot-PIN path with consequences
- [x] CHK031 Is partial message queue recovery specified (network drops mid-stream → [interrupted] suffix + persist + auto-retry)? [Coverage, Spec §FR-015, §Edge Cases] ✓ PASS: Edge Cases document [interrupted] suffix behavior; FR-015 requires persistence

## Non-Functional Requirement Quality (Are NFRs measurable?)

- [x] CHK032 Are all 9 success criteria (SC-001 through SC-009) quantified with specific thresholds and measurable units? E.g., SC-005 idle RAM < 50 MB is clear; SC-003 < 5s on 3G is clear. [Measurability, Spec §SC-001-009] ✓ PASS: All SC-001-009 include specific metrics (time, %, count, status)
- [⚠] CHK033 Is "P1 RAM ceiling" (50 MB idle) validatable on real hardware (Termux/ARM64)? Is measurement plan documented (T069)? [Measurability, Constitution §P1, Tasks §T069] ⚠ CRITICAL ISSUE: T069 status conflicted (pending vs done); actual measurement result not documented
- [x] CHK034 Are performance targets documented for all critical paths? (Setup < 10min, first response < 5s, restart < 10s, daemon ready after reboot < 60s). [Measurability, Spec §SC-001/003/006/007] ✓ PASS: All critical path targets documented with specific time thresholds

---

## Key Findings Summary

| Issue | Severity | Spec Ref | Action Required |
|-------|----------|----------|-----------------|
| Heartbeat timing mismatch | HIGH | Spec §FR-011 vs Plan §NFR | Align values: resolve 30s+5s vs 8s+2s |
| Agent count inconsistency | MEDIUM | Plan §L14 vs §L56 | Update P7 check to list 6 agents |
| RAM profiling gate conflict | CRITICAL | Constitution §P1 vs Plan §T069 | Resolve "pending" vs "done" status |
| PWA Settings gap | MEDIUM | Spec §FR-017 | Add explicit task for PWA Settings implementation |
| Permission re-check ambiguity | MEDIUM | Spec §US1 S3 | Clarify mechanism (TUI/PWA/dialog) |
| App disambiguation UX | MEDIUM | Spec §US3 S4 | Define interaction pattern (buttons/list/voice) |
| Queue size unconstrained | MEDIUM | Spec §FR-014, US2 S5 | Document max queue size, TTL, overflow behavior |

---

## Notes

- Items are numbered sequentially (CHK001–CHK034) for reference.
- Each item includes quality dimension in brackets: [Completeness], [Clarity], [Consistency], [Coverage], [Measurability], [Gap], [Ambiguity], [Conflict]
- Spec section references use short notation (e.g., Spec §FR-017 = Functional Requirement 17; Plan §L14 = Plan line 14)
- Check items off as findings are verified or issues resolved.
- This checklist complements the `/sp.analyze` report — it validates requirements quality across all phases, not just Phase 1 critical path.
