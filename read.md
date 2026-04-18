# Read This First — GURUJEE

GURUJEE is an autonomous AI companion that runs on your Android phone via Termux (no root required). It has a persistent identity, long-term memory, and can handle calls, SMS, and scheduled tasks — entirely from a terminal.

---

## Quickstart

```bash
# 1. Install (in Termux)
curl -fsSL https://raw.githubusercontent.com/staimoorulhassan/GURUJEE/main/install.sh | bash

# 2. Run setup wizard
python -m gurujee.setup

# 3. Launch
python -m gurujee
```

---

## Key Concepts

| Concept | What it means |
|---------|--------------|
| **Soul Agent** | Named identity and personality, persists across reboots |
| **Memory Agent** | Short-term (RAM) + long-term (SQLite) memory |
| **Heartbeat Agent** | Monitors liveness, auto-restarts on failure |
| **Keystore** | AES-256-GCM encrypted credentials, PIN-locked |
| **GatewayDaemon** | Single asyncio supervisor for all agents |

---

## Directory Map

```
gurujee/        Python package (agents, tui, keystore, memory, ai)
config/         YAML config templates
specs/          Feature specs and implementation plans
history/        Prompt History Records and ADRs
tests/          pytest suite
install.sh      Termux bootstrap
```

---

## Development Workflow (SDD)

1. `/sp.specify` — define feature
2. `/sp.plan` — architecture
3. `/sp.tasks` — implementation tasks
4. `/sp.implement` — execute
5. `/sp.git.commit_pr` — commit and PR

---

## Need More?

- Full details: [README.md](README.md)
- Architecture decisions: [history/adr/](history/adr/)
- Project principles: [.specify/memory/constitution.md](.specify/memory/constitution.md)
