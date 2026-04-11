# GURUJEE Foundation — Developer Quickstart

**Branch**: `001-gurujee-foundation` | **Date**: 2026-04-11
**Audience**: Developer setting up the project for the first time (on Android Termux or
a Linux dev machine for testing).

---

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Android (non-rooted) | 10+ | — |
| Termux (F-Droid) | 0.118+ | `termux-info` |
| Termux:Boot (F-Droid) | any | check installed |
| Python | 3.11+ | `python --version` |
| pip | 23+ | `pip --version` |
| git | any | `git --version` |
| Free storage | ≥ 1 GB | `df -h ~` |

**On a Linux dev machine** (for unit tests only): Python 3.11+, pip, git. No Android
dependencies needed for running tests.

---

## Step 1 — Clone and install (Termux)

```bash
# In Termux
pkg update && pkg upgrade -y
pkg install -y python git

cd ~
git clone https://github.com/<owner>/gurujee.git
cd gurujee

pip install -r requirements.txt
```

`requirements.txt` contents (Phase 1):
```
openai>=1.0.0
textual>=0.47.0
rich>=13.0.0
cryptography>=41.0.0
pyaml>=23.0.0
ruamel.yaml>=0.18.0
tenacity>=8.2.0
elevenlabs>=1.0.0
faster-whisper>=1.0.0
pytest>=7.4.0
pytest-asyncio>=0.23.0
responses>=0.25.0
```

---

## Step 2 — Run guided setup (first time only)

```bash
python -m gurujee.setup
```

The Rich wizard walks through **8 steps** in order:

| Step | Name | Required |
|------|------|----------|
| 1 | `packages` — install system deps | Yes |
| 2 | `shizuku` — Shizuku service activation | Yes |
| 3 | `accessibility_apk` — download + SHA-256 verify + install | Optional |
| 4 | `permissions` — grant Android permissions | Yes |
| 5 | `keystore_pin` — choose 4–8 digit PIN (never stored) | Yes |
| 6 | `ai_model` — select AI model from `config/models.yaml` | Yes |
| 7 | `voice_sample` — record + clone voice via ElevenLabs | Optional |
| 8 | `daemons` — copy soul template, start daemon, write boot script | Yes |

State is saved to `data/setup_state.yaml` after each step. Interrupted setup
resumes at the last incomplete step automatically.

To re-run from the beginning:

```bash
python -m gurujee --reset
```

---

## Step 3 — Launch GURUJEE

```bash
# TUI mode (normal use — prompts for PIN, then opens Textual chat interface)
python -m gurujee

# Headless daemon mode (Termux:Boot auto-start; no TUI; also prompts PIN)
python -m gurujee --headless

# Force re-run setup wizard
python -m gurujee --reset
```

**PIN prompt at launch**: every start asks for the 4–8 digit keystore PIN set
in wizard step 5. After 3 wrong attempts, a 30-second lockout applies (exponential
backoff on further failures). A "Forgot PIN?" option wipes the keystore and
re-runs setup.

The `~/.termux/boot/start-gurujee.sh` created by wizard step 8 handles automatic
startup on phone reboot via Termux:Boot.

---

## Step 4 — Run tests

```bash
cd ~/gurujee
pytest tests/ -v --tb=short
```

Target coverage: 70% on all agent files.

```bash
pytest tests/ --cov=gurujee --cov-report=term-missing
```

---

## Project Layout

```
gurujee/                       # Python package
├── __main__.py                # entry point: python -m gurujee
├── agents/
│   ├── base_agent.py          # BaseAgent ABC + MessageBus
│   ├── soul_agent.py
│   ├── memory_agent.py
│   ├── heartbeat_agent.py
│   ├── user_agent.py
│   └── cron_agent.py          # dormant Phase 1
├── daemon/
│   └── gateway_daemon.py      # GatewayDaemon: supervises agents
├── tui/
│   ├── app.py                 # Textual App entry point
│   ├── screens/
│   │   ├── chat_screen.py
│   │   ├── agent_status_screen.py
│   │   └── settings_screen.py
│   └── theme.py               # colors: bg=#0a0a0a, amber=#f0a500, orange=#ff6b00
├── setup/
│   └── wizard.py              # Rich guided setup
├── keystore/
│   └── keystore.py            # AES-256-GCM keystore
├── memory/
│   ├── short_term.py          # ConversationTurn deque
│   └── long_term.py           # SQLite MemoryRecord
├── ai/
│   └── client.py              # AsyncOpenAI wrapper + tenacity retry
└── config/
    └── loader.py              # PyYAML/ruamel.yaml loaders

agents/                        # runtime config (version-controlled templates)
├── soul_identity.yaml         # GURUJEE identity (ruamel.yaml)

config/                        # version-controlled config templates
├── models.yaml                # AI model catalogue + Pollinations endpoint
├── agents.yaml                # heartbeat intervals, memory limits, log config
└── voice.yaml                 # ElevenLabs provider config (no credentials)

agents/                        # shipped identity templates
└── soul_identity.yaml         # GURUJEE default identity (ruamel.yaml)

data/                          # runtime data — GITIGNORED
├── soul_identity.yaml         # runtime copy of soul template (populated by wizard step 8)
├── user_config.yaml           # {active_model, active_voice_id, tui_theme}
├── setup_state.yaml           # 8-step wizard state
├── memory.db                  # SQLite long-term memories (WAL mode)
├── session_context.yaml       # short-term turns persisted across sessions
├── cron_jobs.yaml             # scheduled tasks (empty Phase 1)
├── gurujee.keystore           # AES-256-GCM encrypted credentials
├── heartbeat.log              # rotating, 5MB × 3
├── boot.log                   # rotating, 5MB × 3
└── backups/                   # weekly memory.db snapshots

tests/
├── conftest.py
├── test_soul_agent.py
├── test_memory_agent.py
├── test_heartbeat_agent.py
├── test_user_agent.py
├── test_cron_agent.py
├── test_keystore.py
├── test_ai_client.py
└── test_setup_wizard.py

install.sh                     # Termux bootstrap (downloads and runs setup)
requirements.txt
pyproject.toml
.gitignore                     # excludes data/, *.keystore, *.log
```

---

## Key Config Files

### `config/models.yaml`
```yaml
default: nova-fast
available:
  - nova-fast
  - gemini-fast
  - gemini-search
  - openai-fast
  - grok
  - mistral
endpoint:
  base_url: "https://gen.pollinations.ai/v1"
  api_key: ""
```

### `data/user_config.yaml` *(runtime, gitignored)*
```yaml
active_model: nova-fast          # written by wizard step 6; updated in Settings
active_voice_id: null            # display reference for the voice clone voice ID
tui_theme: default               # reserved Phase 2
```
Defaults applied by `ConfigLoader.load_user_config()` when key is absent.

### `config/agents.yaml`
```yaml
heartbeat:
  ping_interval_seconds: 30
  response_timeout_seconds: 5
  max_restart_attempts: 10
memory:
  short_term_max_turns: 10
  long_term_max_results: 5
  backup_interval_days: 7
logging:
  max_bytes: 5242880   # 5 MB
  backup_count: 3
```

---

## Logging

All logs go to `data/*.log` with `RotatingFileHandler(maxBytes=5MB, backupCount=3)`.
Never use `print()` in production code.

```python
import logging
logger = logging.getLogger(__name__)
```

---

## Environment Variables (optional overrides)

| Variable | Default | Purpose |
|----------|---------|---------|
| `GURUJEE_DATA_DIR` | `./data` | Override data directory |
| `GURUJEE_CONFIG_DIR` | `./config` | Override config directory |
| `GURUJEE_LOG_LEVEL` | `INFO` | Set logging level |
| `GURUJEE_HEADLESS` | `0` | Set `1` to skip TUI |

---

## Common Issues

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: textual` | `pip install textual>=0.47.0` |
| `cryptography` install fails | `pkg install python-cryptography` (Termux) |
| `faster-whisper` install fails | `pip install ctranslate2 faster-whisper` — if still fails, skip for now (Phase 2) |
| Keystore `invalid_pin` on boot | PIN mismatch; re-run `python -m gurujee.setup --step keystore` |
| TUI renders incorrectly | Ensure `$TERM=xterm-256color`; try `export TERM=xterm-256color` |
| Agents not auto-starting on reboot | Confirm Termux:Boot is installed from F-Droid; check `~/.termux/boot/` |
