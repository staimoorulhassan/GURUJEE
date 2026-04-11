# GURUJEE

An autonomous AI companion that runs entirely on your Android phone via Termux — no root required.

GURUJEE has a persistent identity, remembers everything you tell it, handles phone calls and SMS in your voice, runs scheduled tasks, automates your device, and stays on 24/7 — all from a terminal.

---

## Features

| Feature | Status |
|---------|--------|
| Soul Agent — named identity, personality, persists across reboots | Phase 1 |
| Memory Agent — short-term (RAM) + long-term (SQLite) memory | Phase 1 |
| Heartbeat Agent — liveness monitoring, auto-restart on failure | Phase 1 |
| Setup Wizard — 8-step guided setup via Rich CLI | Phase 1 |
| TUI — Textual chat interface with Agent Status and Settings screens | Phase 1 |
| Keystore — AES-256-GCM encrypted credentials, PIN lockout | Phase 1 |
| Voice calls — answer/make calls in your cloned voice via ElevenLabs + SIP | Phase 2 |
| SMS automation — auto-reply and send SMS on your behalf | Phase 2 |
| Shizuku device automation — tap, swipe, open apps without root | Phase 2 |
| Cron Agent — scheduled tasks in natural language | Phase 2 |
| Skills system — plug-and-play Python capability modules | Phase 3 |
| Plugin system — new agent types, UI panels, integrations | Phase 3 |

---

## Requirements

- Android 10+, non-rooted
- [Termux](https://f-droid.org/en/packages/com.termux/) (F-Droid) 0.118+
- [Termux:Boot](https://f-droid.org/en/packages/com.termux.boot/) (F-Droid) for auto-start on reboot
- ~200 MB free storage

> Install Termux from **F-Droid only** — the Play Store version is outdated and breaks `pkg`.

---

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/staimoorulhassan/GURUJEE/main/install.sh | bash
```

Or download and run manually:

```bash
# In Termux
curl -O https://raw.githubusercontent.com/staimoorulhassan/GURUJEE/main/install.sh
bash install.sh
```

To install to a custom path:

```bash
GURUJEE_INSTALL_DIR=$HOME/myapp bash install.sh
```

---

## Setup

On first run, the guided wizard walks through 8 steps:

```bash
python -m gurujee.setup
```

| Step | Name | Required |
|------|------|----------|
| 1 | `packages` — install system deps | Yes |
| 2 | `shizuku` — Shizuku service activation | Yes |
| 3 | `accessibility_apk` — download + SHA-256 verify + install | Optional |
| 4 | `permissions` — grant Android permissions | Yes |
| 5 | `keystore_pin` — choose 4–8 digit PIN (never stored) | Yes |
| 6 | `ai_model` — select AI model | Yes |
| 7 | `voice_sample` — record + clone voice via ElevenLabs | Optional |
| 8 | `daemons` — copy soul template, start daemon, write boot script | Yes |

Setup state is saved after each step and resumes automatically if interrupted.

---

## Usage

```bash
# Launch TUI (chat interface)
python -m gurujee

# Headless daemon (auto-started by Termux:Boot after setup)
python -m gurujee --headless

# Re-run setup wizard
python -m gurujee --reset
```

Every start prompts for your PIN. After 3 wrong attempts a 30-second lockout applies (exponential backoff on further failures). A "Forgot PIN?" option wipes the keystore and re-runs setup.

---

## AI Model

GURUJEE uses [Pollinations.ai](https://pollinations.ai) by default — free, no API key required.

```yaml
# config/models.yaml
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

The active model can be changed in the Settings screen or during setup step 6.

---

## Project Layout

```
gurujee/                   Python package
├── agents/                Soul, Memory, Heartbeat, User, Cron
├── daemon/                GatewayDaemon — asyncio supervisor
├── tui/                   Textual app — Chat, AgentStatus, Settings
├── setup/                 Rich guided setup wizard
├── keystore/              AES-256-GCM encrypted credential store
├── memory/                SQLite long-term + deque short-term
├── ai/                    AsyncOpenAI wrapper (Pollinations endpoint)
└── config/                YAML loaders

config/                    Version-controlled config templates
agents/                    Soul identity template
data/                      Runtime data (gitignored)
tests/                     pytest suite (51 tests)
install.sh                 Termux bootstrap script
```

---

## Development

```bash
# Clone
git clone https://github.com/staimoorulhassan/GURUJEE.git
cd GURUJEE

# Install dependencies (Python 3.11+)
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Coverage
pytest tests/ --cov=gurujee --cov-report=term-missing
```

Target: 70% coverage on all agent modules. TUI and daemon require a display/runtime and are not covered by the unit test suite.

---

## Security

- All credentials are encrypted locally with AES-256-GCM (PBKDF2-HMAC-SHA256, 480k iterations)
- The PIN is never stored — it is the sole input to key derivation
- Network calls go only to: `gen.pollinations.ai` (AI), `api.elevenlabs.io` (voice), and your configured SIP domain
- An outbound network allowlist blocks all other hosts at the client level

---

## Architecture

| Decision | Choice | Reason |
|----------|--------|--------|
| Single process | GatewayDaemon + TUI in one asyncio loop | Saves ~25 MB RAM on low-end devices |
| Memory retrieval | Recency (last 10 turns) + keyword/tag search | Hybrid ADR-002 |
| Skill sandboxing | subprocess isolation | Security ADR-001 |
| AI endpoint | Pollinations.ai | Free, no API key, proxies major models |

Full architecture decisions: [`history/adr/`](history/adr/)

---

## License

MIT
