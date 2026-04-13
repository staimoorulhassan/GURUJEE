# GURUJEE 🤖

> *Your autonomous AI companion on Android — no root, no PC, no limits.*

GURUJEE is a personal AI agent platform that runs entirely on your Android phone inside Termux. It answers your calls in your voice, replies to SMS automatically, controls your phone by command, remembers everything you tell it, and runs scheduled tasks while you sleep — all powered by AI, all local-first.

Think of it as **OpenClaw for Android**.

---

## What GURUJEE Can Do

| Capability | Description |
|---|---|
| 💬 **AI Chat** | Talk to GURUJEE via a WhatsApp-style app on your phone |
| 🧠 **Persistent Memory** | It remembers what you told it last week |
| 📞 **Auto-Answer Calls** | Answers calls in your cloned voice using AI |
| 📱 **Phone Automation** | Open apps, send messages, control settings by voice or text |
| 💌 **SMS Auto-Reply** | Replies to approved contacts automatically |
| ⏰ **Smart Scheduling** | "Remind me every Monday at 9am" — it just works |
| 🎭 **Soul & Identity** | Persistent personality that evolves with you |
| 🔌 **40+ AI Providers** | Anthropic, OpenAI, Gemini, Ollama, Groq, and more |
| 🔒 **Private by Default** | All data on your phone, all secrets encrypted |

---

## Requirements

- Android 9+ (API 28+)
- 2GB RAM minimum (3GB+ recommended)
- Termux installed from [F-Droid](https://f-droid.org/packages/com.termux/) — **not Play Store**
- Termux:API installed from [F-Droid](https://f-droid.org/packages/com.termux.api/)
- Internet connection for first setup
- [Shizuku](https://shizuku.rikka.app/) for device automation (optional but recommended)

> **Important:** Install Termux from F-Droid only. The Play Store version is outdated and will break the install.

---

## Installation

### Option A — One-tap Install (Recommended)

1. Open Termux on your Android phone
2. Run this single command:

```bash
curl -sL https://raw.githubusercontent.com/staimoorulhassan/GURUJEE/main/install.sh | bash
```

3. Follow the guided setup — it handles everything automatically
4. When done, tap the **GURUJEE** shortcut on your homescreen

---

### Option B — Download APK (Easiest for non-technical users)

> **APK is building automatically via GitHub Actions.**
> Check [Releases](https://github.com/staimoorulhassan/GURUJEE/releases) in ~20 minutes.
> For immediate install, use Option A (Termux command above).

1. Go to [GitHub Releases](https://github.com/staimoorulhassan/GURUJEE/releases/latest)
2. Download `gurujee-1.0.0-debug.apk`
3. On your Android phone:
   - Go to **Settings → Security → Install Unknown Apps**
   - Allow your browser or file manager to install APKs
4. Open the downloaded APK and tap **Install**
5. Open **GURUJEE** from your app drawer
6. The app will check for Termux and set everything up automatically
7. Wait 3–5 minutes for first-time setup to complete

> **Note:** You need Termux installed from F-Droid for GURUJEE to work.
> If it's not installed, GURUJEE will show a button to install it first.
> Get Termux here: https://f-droid.org/packages/com.termux/

---

## First-Time Setup Walkthrough

When you first run GURUJEE, the guided setup wizard walks you through every step. You cannot break anything — just follow the prompts.

### Step 1 — Environment Check
GURUJEE checks that Termux and Termux:API are installed correctly. If anything is missing, it installs it automatically.

### Step 2 — Install Dependencies
All Python packages and system tools are installed in the background. This takes 2–5 minutes on first run depending on your internet speed. You will see a progress bar.

```
Installing dependencies...
  ✓ python 3.11
  ✓ fastapi, uvicorn
  ✓ textual (TUI)
  ✓ elevenlabs
  ✓ faster-whisper
  ✓ cryptography
  ✓ pjsua2 (SIP)
  ✓ termux-api
```

### Step 3 — Shizuku Setup (Device Automation)
Shizuku gives GURUJEE the ability to control your phone without root. The setup walks you through enabling it:

1. Go to **Settings → Developer Options → Wireless Debugging**
2. Tap **Pair device with pairing code**
3. Enter the code shown in GURUJEE setup
4. Done — Shizuku is now active

> If you skip this step, GURUJEE still works for chat, calls, and SMS — just not for device automation (opening apps, tapping screen, etc.).

### Step 4 — Permissions
GURUJEE requests all required permissions in one batch via Shizuku:
- Phone (make/receive calls)
- SMS (read/send messages)  
- Contacts (look up names)
- Microphone (voice input and calls)
- Notifications (read and act on them)

### Step 5 — Set Your PIN
GURUJEE uses a PIN to encrypt all your secrets (API keys, SIP password, voice clone). This PIN is never stored — it is used to derive your encryption key. 

Choose a 4–8 digit PIN you will remember. If you forget it, you must re-run setup (credentials will need to be re-entered).

### Step 6 — AI Model Setup
Choose your primary AI provider. The default is **Pollinations AI** — free, no API key needed, works immediately.

```
Select your AI model:
  → Pollinations (Free, no key needed)     ← default
    Anthropic Claude (API key required)
    OpenAI GPT (API key required)
    Google Gemini (API key required)
    Ollama (local, no internet needed)
    + 35 more providers
```

To add an API key for a paid provider, enter it here — it is stored encrypted in the keystore and never written to any config file.

### Step 7 — Voice Setup
GURUJEE speaks using ElevenLabs text-to-speech. Enter your ElevenLabs API key (free tier available at elevenlabs.io) or skip to use the built-in offline voice.

**Voice Cloning (optional):** Record a 30-second voice sample so GURUJEE answers your calls sounding like you. You will be shown a consent screen explaining exactly how the recording is used and that you can delete it at any time.

### Step 8 — SIP / Calling Setup
If you want GURUJEE to make and receive real phone calls, configure your SIP account. GURUJEE comes pre-configured for `sip.suii.us` — just confirm or change the settings.

### Step 9 — Launch
GURUJEE starts all background services and loads the chat interface. From this point, it starts automatically every time your phone boots.

---

## Daily Use

### The Chat Interface
Open the GURUJEE app on your homescreen. You will see a chat interface — type or speak to GURUJEE just like messaging a person.

**Examples of what you can say:**

```
"Open WhatsApp"
"Send a message to Ali saying I'll be late"
"Set an alarm for 7am tomorrow"
"Turn on WiFi"
"What did I tell you about my doctor's appointment?"
"Call my wife"
"Remind me every Friday evening to water the plants"
"Take a screenshot"
"What is the weather today?"
"Turn off the flashlight"
```

GURUJEE understands natural language — you do not need to learn commands.

---

### Voice Input
Tap the microphone button in the chat to speak instead of type. GURUJEE transcribes your voice using Whisper (runs locally on your phone — nothing sent to the cloud).

---

### Auto-Answer Calls
By default, auto-answer is **OFF**. To enable:

1. Open GURUJEE chat
2. Say: *"Enable auto-answer for calls"*
3. Or go to **Settings → Calls → Auto-Answer**

When enabled, GURUJEE answers incoming calls after 2 rings. It greets the caller, listens using Whisper, thinks using AI, and responds using your cloned voice — all in real time.

**To take over a call:** Tap **"Take Over"** in the GURUJEE notification while the call is active.

---

### SMS Auto-Reply
By default, auto-reply is **OFF**. To enable for specific contacts:

```
"Add Mum to my auto-reply list"
"Enable SMS auto-reply for 03XXXXXXXXX"
```

GURUJEE will reply to those contacts automatically using context from your memory. You can review all auto-sent replies in **Settings → SMS → Reply Log**.

---

### Scheduled Tasks (Cron)
Tell GURUJEE in plain English:

```
"Every morning at 8am, remind me to take my medicine"
"Every Monday, send Ali a message asking for the weekly report"
"Every day at 9pm, read me my notifications from today"
"Cancel my medicine reminder"
"Show me all my scheduled tasks"
```

GURUJEE converts natural language into scheduled jobs. You can also use raw cron expressions if you prefer:

```
"Schedule cron 0 8 * * * to remind me to drink water"
```

---

### Device Automation
GURUJEE can control your phone like a human would:

```
"Open YouTube and search for cooking videos"
"Go to Settings and turn on Do Not Disturb"
"Take a screenshot and send it to Bilal"
"Read my latest WhatsApp messages"
"Set brightness to 50%"
"Connect to WiFi named MyHome"
```

> Device automation requires Shizuku to be set up. If GURUJEE says it cannot perform an action, check **Settings → Device Access → Shizuku Status**.

---

## AI Model Management

### Switch Your Primary Model
In the chat:
```
"Switch to Anthropic Claude"
"Use Gemini for my messages"
"Switch back to Pollinations"
```

Or go to **Settings → AI Models → Primary Model**.

### Add a New Provider
Go to **Settings → AI Models → Add Provider**:

| Field | Example |
|---|---|
| Provider name | `My Groq` |
| Base URL | `https://api.groq.com/openai/v1` |
| API Key | `gsk_...` |
| Model ID | `llama-3.3-70b-versatile` |

Tap **Test Connection** before saving.

### Use a Local Ollama Model
If you run Ollama on a PC on the same WiFi network:
```
"Add Ollama provider at 192.168.1.50:11434"
"Use ollama/llama3.3 as my model"
```

### Set Fallback Models
If your primary model fails or hits rate limits, GURUJEE automatically tries fallbacks:

**Settings → AI Models → Fallback Chain**

Recommended setup:
```
Primary:    pollinations/nova-fast     (free, always available)
Fallback 1: openai/gpt-4o-mini        (cheap, fast)
Fallback 2: pollinations/gemini-fast  (free backup)
```

### Supported Providers (40+)

| Category | Providers |
|---|---|
| **Free / No Key** | Pollinations (nova-fast, gemini-fast, gemini-search, openai-fast, grok, mistral) |
| **Cloud Premium** | Anthropic (Claude), OpenAI (GPT), Google (Gemini), xAI (Grok), Mistral |
| **Fast Inference** | Groq, Together AI, DeepSeek, Perplexity |
| **Multi-Model Gateways** | OpenRouter, LiteLLM, Vercel AI Gateway, Kilo Gateway, Cloudflare AI |
| **Local / Self-Hosted** | Ollama, vLLM, SGLang, LM Studio, ComfyUI |
| **OAuth (Free)** | GitHub Copilot, OpenCode, Google Gemini CLI |
| **China Providers** | Alibaba (Qwen), Volcengine (Doubao), Moonshot (Kimi), MiniMax, Qianfan |
| **Privacy-Focused** | Venice AI, Chutes |
| **Specialized** | NVIDIA NIM, Amazon Bedrock, Hugging Face, fal.ai, Runway, StepFun |

---

## Settings Reference

Open **Settings** from the GURUJEE app bottom navigation.

### AI Models
- **Primary Model** — your default model for all conversations
- **Fallback Chain** — models tried if primary fails (in order)
- **Per-Agent Routing** — set different models for different internal agents
- **Usage Stats** — tokens used, estimated cost per provider today
- **Add Provider** — connect any OpenAI-compatible endpoint

### Calls
- **Auto-Answer** — on/off toggle
- **Auto-Answer Rings** — how many rings before answering (default: 2)
- **AI Voice Mode** — answer with AI voice / just record / silent
- **Voice Clone** — manage your cloned voice or re-record
- **SIP Status** — registration status, reconnect button

### SMS
- **Auto-Reply** — on/off toggle
- **Approved Contacts** — list of contacts with auto-reply enabled
- **Reply Log** — all auto-sent messages
- **Polling Interval** — how often to check for new SMS (default: 30s)

### Scheduled Tasks
- **All Jobs** — view, enable/disable, delete any scheduled task
- **Missed Job Policy** — what happens to jobs that fired while phone was off

### Device Access
- **Shizuku Status** — check if Shizuku is active, re-activate if needed
- **Permission Audit** — which permissions GURUJEE has and which are missing
- **Automation Log** — history of all device actions taken

### Memory
- **Conversation History** — browse, search, delete memories
- **Memory Stats** — how many facts stored, database size
- **Export Memory** — export all memories to a text file
- **Clear Memory** — wipe short-term or all long-term memory

### Security
- **Change PIN** — update your keystore PIN
- **API Keys** — view which providers have keys configured (values hidden)
- **Network Allowlist** — which domains GURUJEE can connect to
- **Security Log** — all keystore access events

### Soul & Identity
- **GURUJEE's Name** — change what it calls itself
- **Personality Traits** — adjust how GURUJEE communicates
- **Soul Journal** — read GURUJEE's self-narrative (it writes this itself)
- **Reset Soul** — restore default personality

---

## Developer / Admin Mode (TUI)

For advanced users, GURUJEE has a terminal interface:

```bash
# In Termux
python -m gurujee --tui
```

The TUI shows live agent status, message bus traffic, raw logs, and direct agent commands. Normal users never need this.

**Keyboard shortcuts in TUI:**

| Key | Action |
|---|---|
| `Tab` | Switch between panels |
| `c` | Open chat panel |
| `a` | Open agents panel |
| `s` | Open settings panel |
| `l` | View logs |
| `q` | Quit TUI (daemon keeps running) |
| `Ctrl+C` | Stop everything |

---

## Troubleshooting

### GURUJEE is not responding in chat
1. Check daemon is running: open Termux and run `python -m gurujee --status`
2. If not running: `python -m gurujee --start`
3. Check logs: `python -m gurujee --logs`

### Auto-answer is not working
1. Go to **Settings → Calls → SIP Status**
2. If status shows "Not Registered" — tap **Reconnect**
3. Check your SIP credentials in **Settings → Security → API Keys**
4. Make sure microphone permission is granted

### Device automation says "Shizuku not available"
1. Go to **Settings → Device Access → Shizuku Status**
2. Tap **Re-activate Shizuku**
3. Follow the wireless debugging pairing steps again
4. Note: Shizuku must be re-activated after every phone reboot on some devices

### SMS auto-reply is not sending
1. Confirm Termux:API is installed (from F-Droid)
2. Run in Termux: `termux-sms-send -n +923001234567 test` — if this fails, reinstall Termux:API
3. Make sure SMS permission is granted to Termux:API

### GURUJEE forgot my memories after update
Your memories are in `data/memory.db` — this file is never deleted by updates. If memories are missing:
```bash
ls ~/GURUJEE/data/memory.db   # check if file exists
python -m gurujee --memory-stats   # check memory count
```

### "Wrong PIN" on startup
- You have 3 attempts before a 30-second lockout
- If you have forgotten your PIN: run `python -m gurujee --reset-keystore`
- **Warning:** This deletes all stored credentials. You will need to re-enter API keys and SIP password in setup.

### App crashes on startup
```bash
# In Termux, check the error:
python -m gurujee --headless 2>&1 | head -50

# Common fix — reinstall dependencies:
cd ~/GURUJEE && pip install -r requirements.txt --break-system-packages
```

### Out of memory errors
GURUJEE targets under 120MB RAM active. If your phone is low on RAM:
1. **Settings → AI Models** → switch to `pollinations/nova-fast` (lightest)
2. **Settings → Memory** → reduce short-term context window to 5 (default 10)
3. Close other background apps

---

## Updating GURUJEE

```bash
# In Termux:
cd ~/GURUJEE
git pull origin main
pip install -r requirements.txt --break-system-packages
python -m gurujee --restart
```

Your memories, settings, and credentials are preserved across updates.

---

## Data & Privacy

| Data | Where it lives | Leaves your phone? |
|---|---|---|
| Conversations & memories | `data/memory.db` (SQLite) | Never |
| API keys & SIP password | `data/gurujee.keystore` (AES-256-GCM) | Never |
| Voice clone sample | Deleted after upload | Sent once to ElevenLabs |
| AI chat messages | Sent to your chosen AI provider | Yes (to provider only) |
| Call audio | Processed locally by Whisper | Never |
| SMS content | Sent to AI for reply generation | Yes (to provider only) |
| Soul identity | `data/soul_identity.yaml` | Never |

**Network connections GURUJEE makes:**
- `gen.pollinations.ai` — AI inference (default provider)
- `api.elevenlabs.io` — voice synthesis (if configured)
- `sip.suii.us` — SIP calling (if configured)
- Your chosen AI provider's API endpoint

No analytics. No telemetry. No ads. No accounts required.

---

## Project Structure (for developers)

```
gurujee/
├── agents/          # Soul, Memory, Heartbeat, Cron, UserAgent, Orchestrator, Automation
├── ai/              # ModelClient — 40+ provider support, failover, key rotation
├── voice/           # TTS (ElevenLabs + piper), STT (Whisper), SIP (pjsua2), voice clone
├── skills/          # Pluggable skill modules (web search, calculator, contacts, etc.)
├── plugins/         # Third-party plugin loader
├── server/          # FastAPI daemon — REST API + WebSocket + PWA static files
├── ui/              # Textual TUI (developer/admin only)
├── setup/           # Guided setup wizard, Shizuku bridge, permissions
├── daemon/          # Gateway daemon (asyncio event loop, all agents as Tasks)
├── keystore/        # AES-256-GCM secret storage
├── config/          # models.yaml, agents.yaml, voice.yaml, security.yaml
├── data/            # Runtime data (gitignored): memory.db, keystore, logs, user_config
└── tests/           # pytest — 120+ tests, 70%+ coverage
```

---

## Phases

| Phase | Status | Contents |
|---|---|---|
| **Phase 1 — Foundation** | ✅ Complete | Chat UI, soul/memory agents, device automation, PWA, auto-start, 40+ AI providers |
| **Phase 2 — Comms** | 🔄 In Progress | SIP calling, voice clone, SMS auto-reply, cron scheduler |
| **Phase 3 — Orchestration** | 📋 Planned | Sub-agents, advanced skills, plugin marketplace |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The project follows spec-driven development using [spec-kit-plus](https://github.com/panaversity/spec-kit-plus). All features start with `/sp.constitution` → `/sp.specify` → `/sp.plan` → `/sp.tasks` → `/sp.implement`.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Credits

Built by **Taimoor** using [spec-kit-plus](https://github.com/panaversity/spec-kit-plus) and Claude Code.

Inspired by [OpenClaw](https://openclaw.ai) — the original personal AI agent platform.

Powered by [Pollinations AI](https://pollinations.ai) (free default), [ElevenLabs](https://elevenlabs.io) (voice), and [Shizuku](https://shizuku.rikka.app) (device access).

---

*GURUJEE — Respected teacher. Always learning. Always present.*
