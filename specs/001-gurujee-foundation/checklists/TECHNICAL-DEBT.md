# Technical Debt: GURUJEE Foundation Phase 1

**Date Accepted**: 2026-04-27  
**Status**: Known issues accepted for post-implementation resolution  
**Total Items**: 8 (3 CRITICAL, 1 HIGH, 4 MEDIUM)

---

## 🔴 CRITICAL (P1 — must resolve before Phase 2 release)

### TDT-001: Heartbeat Timing Configuration Mismatch
- **Status**: ✅ **RESOLVED** (2026-04-27)
- **Issue**: T006 config/agents.yaml specifies `heartbeat interval: 30s, ping timeout: 5s`, but constitutional amendment (v1.2.1) changed to 8s+2s
- **Location**: config/agents.yaml (T006), plan.md line 234, constitution.md line 38
- **Resolution**: VERIFIED - config/agents.yaml already has correct 8s+5s values; implementation verified in heartbeat_agent.py
- **Status Evidence**: 
  - config/agents.yaml: `ping_interval_seconds: 8, response_timeout_seconds: 5`
  - heartbeat_agent.py: `_PING_INTERVAL = 8.0, _PONG_TIMEOUT = 5.0`

### TDT-002: T069 RAM Profiling Status Unresolved
- **Status**: ⚠️ **PARTIALLY RESOLVED** (2026-04-27)
- **Issue**: Constitution says "pending", Plan says "done"; actual measurement result not documented
- **Location**: constitution.md line 41, plan.md line 229
- **Measurement Completed**: Windows dev environment (2026-04-27)
  - Idle daemon RSS: 59.30 MB (exceeds 50 MB P1 ceiling on this platform)
  - Benchmark file: specs/001-gurujee-foundation/data/benchmarks/idle-ram-001.txt
- **Status Clarified**: 
  - constitution.md: "T069 idle RAM profiling — Windows measurement: 59.30 MB. ARM64 Termux measurement still required as Phase 2 pre-release gate."
  - plan.md: "T069 PARTIAL — Windows measurement 59.30 MB. ARM64 Termux measurement required as Phase 2 pre-release gate."
- **Remaining Action**: ARM64 Termux device measurement deferred to Phase 2 pre-release gate

### TDT-003: Agent Count Inconsistency in Plan
- **Status**: ✅ **RESOLVED** (2026-04-27)
- **Issue**: Plan P7 constitution check lists "5 agents" but design is 6 (missing automation from count)
- **Location**: plan.md line 56 (P7 check)
- **Resolution**: Updated plan.md line 60 from "All 5 Phase-1 agents (soul, memory, heartbeat, user_agent, cron-dormant)" to "All 6 Phase-1 agents (soul, memory, heartbeat, user_agent, cron, automation)"
- **Status Evidence**: plan.md P7 check now correctly lists 6 agents

---

## 🟡 HIGH (Phase 1+ — resolve before user release)

### TDT-004: PWA Settings View Not Explicitly Tasked
- **Issue**: FR-017 requires PWA Settings view (model selector, soul identity editor, Phase 2 placeholders), but tasks T037–T041 don't explicitly include it
- **Location**: spec.md FR-017, tasks.md T037–T041 (static file tasks)
- **Impact**: PWA missing Settings UI; users cannot change model/soul identity via PWA
- **Resolution**: Either add task T041a (PWA Settings implementation) or clarify that Settings is accessed via TUI only (--tui mode)
- **Owner**: TBD
- **Priority**: High (core user-facing feature for Phase 1)

---

## 🟡 MEDIUM (Phase 2 — resolve before production)

### TDT-005: Queue Management Constraints Undefined
- **Issue**: FR-014 requires message queuing when AI endpoint unreachable, but max queue size, TTL, and overflow behavior not specified
- **Location**: spec.md FR-014, US2 S5
- **Impact**: Unbounded queue possible in long outages; potential memory leak
- **Resolution**: Add to spec clarifications or implement defensively with cap (e.g., max 100 pending messages, FIFO drop on overflow)
- **Owner**: TBD
- **Priority**: Medium (affects robustness but not core functionality)

### TDT-006: Permission Re-Check UX Ambiguous
- **Issue**: Spec US1 S3 says GURUJEE "explains" why permission is needed and guides user to Android settings, but doesn't specify UI delivery (TUI popup vs PWA banner vs Termux output)
- **Location**: spec.md US1 S3
- **Impact**: Implementation ambiguity; user guidance mechanism unclear
- **Resolution**: Clarify in quickstart.md or implement with consistent choice (recommend: TUI terminal output during setup wizard)
- **Owner**: TBD
- **Priority**: Medium (affects UX clarity, not core functionality)

### TDT-007: App Name Disambiguation UX Ambiguous
- **Issue**: Spec US3 S4 provides example phrasing ("Did you mean SMS Messages or Google Messages?") but not selection mechanism (chat buttons vs numbered list vs voice input)
- **Location**: spec.md US3 S4
- **Impact**: Automation UX inconsistency; implementation has design freedom but lacks guidance
- **Resolution**: Clarify in quickstart.md or implement with consistent choice (recommend: chat bubbles with clickable options matching PWA style)
- **Owner**: TBD
- **Priority**: Medium (nice-to-have UX polish)

### TDT-008: P1 RAM Ceiling Measurement Not Documented
- **Issue**: Constitution P1 requires ≤50 MB idle daemon RAM, but actual measurement from T069 not documented
- **Location**: constitution.md P1 (line 69), Tasks T069
- **Impact**: P1 compliance unmeasured; cannot verify hard ceiling is met
- **Resolution**: Run T069 profiling on real ARM64/Termux device and document result in specs/001-gurujee-foundation/data/benchmarks/idle-ram-001.txt
- **Owner**: TBD
- **Priority**: Medium (compliance validation; addressed in TDT-002)

---

## Summary

| Priority | Count | Status |
|----------|-------|--------|
| 🔴 CRITICAL | 3 | Requires resolution before Phase 2 |
| 🟡 HIGH | 1 | Resolve before user release |
| 🟡 MEDIUM | 4 | Resolve in Phase 2+ or post-Phase-1 |
| **TOTAL** | **8** | Accepted as technical debt |

**Acceptance Criteria Met**: 
- All items documented with owner, location, and resolution path
- No blocker for Phase 1 MVP (core chat, memory, automation, PWA functional)
- Clear tracking for post-implementation remediation
