# ADR-001: Skill Sandboxing Strategy

- **Status:** Accepted
- **Date:** 2026-04-11
- **Feature:** 001-gurujee-foundation (applies to Phase 003 — gurujee-automation)
- **Context:** GURUJEE allows users to install third-party Skills as Python modules that
  run on their phone. The sandboxing strategy must prevent a bad skill from crashing the
  main daemon or accessing the encrypted keystore, while staying compatible with stock
  Android ARM64 inside Termux (no Docker, no seccomp, no root).

## Decision

**Use `multiprocessing` with per-call resource limits (Option 3), with a lightweight
restricted-builtins wrapper for built-in skills (Option 2).**

Specifically:

- **Third-party / user-installed skills** run in a spawned `multiprocessing.Process`.
  Each call spawns a fresh process, communicates results back via a `multiprocessing.Queue`
  or `Pipe`, and is subject to:
  - A configurable wall-clock timeout (default 30 s) enforced by `Process.join(timeout)`.
  - A RAM ceiling via `resource.setrlimit(RLIMIT_AS, ...)` set immediately inside the
    child process before the skill code runs (ARM64-compatible, Termux-safe).
  - The child process never receives a reference to the Keystore object — it receives
    only the serialised input payload.
- **Built-in skills** (web search, calculator, contacts, calendar, file management) run
  in-process via `importlib` with a restricted execution namespace that removes
  `__import__`, `open`, `os`, `subprocess`, and `socket` from the skill's builtins.
  Built-in skills are audited at commit time, so the lighter sandbox is acceptable.
- The **Skill Registry** (`data/skills/registry.yaml`) records each skill's trust level
  (`builtin` | `third-party`), which determines which isolation path is used.

## Consequences

### Positive

- Third-party skill crashes are fully isolated — a segfault or infinite loop in a skill
  cannot affect the gateway daemon or any always-on agent.
- The keystore is structurally unreachable from child processes (never passed across the
  process boundary).
- `multiprocessing` is part of Python's standard library; no additional dependencies.
- `resource.setrlimit` works on ARM64 Linux (Android kernel) inside Termux without root.
- Wall-clock timeout gives the gateway a clean way to kill stuck skills without threads.
- Built-in skills retain low overhead (no process spawn cost for trusted code).

### Negative

- Each third-party skill call incurs a process-spawn overhead (~50–150 ms on low-end ARM64).
  This makes skills unsuitable for tight loops; they are intended for discrete, user-triggered
  actions, so this is acceptable.
- `multiprocessing` uses `fork`-based start on Linux by default. `fork` after `asyncio`
  event loop initialisation can cause subtle bugs. **Mitigation**: use `spawn` start method
  explicitly (`multiprocessing.set_start_method('spawn')`), which is clean but slower.
- `setrlimit(RLIMIT_AS)` limits virtual address space, not RSS. On modern kernels with ASLR
  and mmap, virtual space consumption can exceed RSS. **Mitigation**: set limit generously
  (3× expected RSS) and rely primarily on timeout as the safety valve.
- Restricted builtins for built-in skills can be bypassed by code that reconstructs
  `__builtins__` via `object.__subclasses__()`. Since built-in skills are audited,
  this is acceptable; third-party skills get the stronger subprocess boundary.

## Alternatives Considered

**Option 1 — subprocess isolation (each skill as a separate `python` subprocess via
`subprocess.Popen`)**
- Pros: Maximum isolation; child process has its own Python interpreter and memory space.
- Cons: Higher startup cost than `multiprocessing.spawn` due to full interpreter init per
  call. Requires JSON-over-stdin/stdout serialisation protocol, which is more fragile than
  a `Queue`. Rejected in favour of `multiprocessing` which provides the same isolation
  with a cleaner IPC interface.

**Option 2 — `importlib` with restricted builtins only (for all skills)**
- Pros: Zero process-spawn overhead; skill code runs in-process.
- Cons: Isolation is bypassable. A determined or buggy skill can reconstruct unrestricted
  builtins, call `ctypes`, or exhaust heap memory in the main process. Acceptable only for
  audited built-in skills. Rejected as the sole strategy for third-party skills.

**Option 3 (chosen) — `multiprocessing` with `setrlimit`**
- Selected because it provides genuine crash isolation, keystore inaccessibility, and
  ARM64/Termux compatibility without external dependencies.

## References

- Feature Spec: specs/001-gurujee-core/spec.md (FR-027)
- Implementation Plan: specs/003-gurujee-automation/plan.md (not yet created)
- Related ADRs: ADR-002 (Memory Retrieval Strategy)
- Evaluator Evidence: history/prompts/001-gurujee-core/001-gurujee-core-spec.spec.prompt.md
