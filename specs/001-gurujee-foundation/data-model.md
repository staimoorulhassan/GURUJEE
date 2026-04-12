# Data Model: GURUJEE Foundation

**Branch**: `001-gurujee-foundation` | **Date**: 2026-04-11

All persistent state lives under the `data/` directory (gitignored). Config lives under
`agents/` and `config/` (version-controlled templates; instances gitignored).

---

## 1. MemoryRecord — `data/memory.db` (SQLite, table: `memories`)

Long-term storage for facts, preferences, and significant conversation moments.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK AUTOINCREMENT | Surrogate key |
| `content` | TEXT | NOT NULL | Plain-text memory content |
| `tags` | TEXT | NOT NULL DEFAULT '' | Comma-separated tag tokens for retrieval |
| `category` | TEXT | NOT NULL | One of: `person`, `place`, `preference`, `fact`, `task` |
| `importance` | REAL | NOT NULL DEFAULT 0.5 | Score 0.0–1.0; explicit "remember" → 1.0 |
| `created_at` | TEXT | NOT NULL | ISO-8601 UTC timestamp |
| `source` | TEXT | NOT NULL DEFAULT 'conversation' | `conversation` or `explicit` |

**Indices**: `CREATE INDEX idx_tags ON memories(tags)` for LIKE queries.
**WAL mode**: enabled on every connection open.
**Retrieval query** (ADR-002 hybrid):
```sql
SELECT * FROM memories
WHERE tags LIKE '%' || ? || '%'
ORDER BY (importance * 2 + 1.0 / (julianday('now') - julianday(created_at) + 1)) DESC
LIMIT 5;
```

**Backup**: weekly `shutil.copy2(memory.db, backups/memory_YYYYMMDD.db)`. Failures logged,
never blocking.

---

## 2. ConversationTurn — in-RAM (short-term context buffer)

Short-term memory; NOT persisted between sessions (session end → summarise → long-term).

| Field | Type | Description |
|-------|------|-------------|
| `role` | str | `"user"` or `"assistant"` |
| `content` | str | Message text |
| `timestamp` | datetime | UTC |

**Container**: `collections.deque(maxlen=10)` inside `MemoryAgent`.
**Serialised** to `data/session_context.yaml` on graceful shutdown for session continuity.
Re-loaded on next startup.

---

## 3. Soul — `data/soul_identity.yaml` (ruamel.yaml, user-editable)

**Template source**: `agents/soul_identity.yaml` (version-controlled).
**Runtime copy**: `data/soul_identity.yaml` (gitignored) — initialised by wizard step 8.
`SoulAgent` reads the runtime copy; the template is never modified at runtime.

GURUJEE's persistent identity. Loaded by `SoulAgent` on startup; injected into every
AI system prompt.

```yaml
name: "GURUJEE"
tagline: "Your wise, ever-present AI companion."
personality_traits:
  - wise
  - concise
  - proactive
  - warm
language_style: "formal-yet-approachable"   # instructs response tone
system_prompt_template: |
  You are {name} — {tagline}
  Traits: {traits_joined}.
  Today is {date}. The user's name is {user_name}.
  Recent context will follow.
  Always be concise. Proactively surface relevant memories.
voice_id: null      # populated by guided setup; stored reference key in keystore
created_at: "2026-04-11T00:00:00Z"
version: 1
```

**Validation rules**:
- `name` MUST be non-empty string, max 32 chars.
- `personality_traits` MUST be a non-empty list of strings.
- `system_prompt_template` MUST contain `{name}` placeholder.
- `voice_id` is null until voice sample step completes; null = TTS not yet configured.

---

## 4. SetupState — `data/setup_state.yaml` (PyYAML, machine-written)

Tracks guided setup progress for resumption after interruption.

```yaml
version: 1
started_at: "2026-04-11T10:00:00Z"
completed_at: null       # set when all required steps complete
steps:
  packages:
    completed: false
    skipped: false
    completed_at: null
  shizuku:
    completed: false
    skipped: false
    completed_at: null
  accessibility_apk:
    completed: false
    skipped: false
    completed_at: null
    apk_sha256: null     # populated with verified checksum after install
  permissions:
    completed: false
    skipped: false
    completed_at: null
    granted: []          # list of granted permission names
    denied: []
  keystore_pin:
    completed: false
    skipped: false       # cannot be skipped
    completed_at: null
    pin_set: false       # set to true after keystore is created
  ai_model:
    completed: false
    skipped: false
    completed_at: null
    selected_model: null
  voice_sample:
    completed: false
    skipped: false       # user may skip
    completed_at: null
    consent_given: false
  daemons:
    completed: false
    skipped: false
    completed_at: null
```

**Required steps** (cannot be skipped): `packages`, `shizuku`, `permissions`, `keystore_pin`,
`ai_model`, `daemons`.
**Optional steps** (skippable): `accessibility_apk`, `voice_sample`.

---

## 5. AgentState — in-RAM (runtime only, not persisted)

Live state of each agent process tracked by `GatewayDaemon`.

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Agent identifier (`soul`, `memory`, etc.) |
| `status` | AgentStatus | Enum: STARTING / RUNNING / STOPPED / ERROR |
| `task` | asyncio.Task | The running coroutine handle |
| `restart_count` | int | Times restarted this session |
| `last_restart` | datetime \| None | UTC timestamp of last restart |
| `last_error` | str \| None | Last exception message if status=ERROR |
| `inbox` | asyncio.Queue | Agent's message inbox |

**Displayed in**: TUI Agent Status screen, updated via Textual reactive attributes.

---

## 6. Message — message bus payload (asyncio.Queue)

All inter-agent communication passes through typed Message objects.

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | UUID4 |
| `from_agent` | str | Sender agent name or `"tui"` / `"gateway"` |
| `to_agent` | str | Recipient agent name or `"broadcast"` |
| `type` | MessageType | Enum (see contracts) |
| `payload` | dict | Type-specific payload (see contracts) |
| `timestamp` | datetime | UTC creation time |
| `reply_to` | str \| None | ID of message this is a reply to |
| `ttl` | int | Max hops before discard; default 10 |

---

## 7. UserConfig — `data/user_config.yaml` (PyYAML, machine-written)

User-specific runtime preferences written by the setup wizard and Settings screen.

```yaml
active_model: "nova-fast"    # selected from config/models.yaml available[]
active_voice_id: null        # ElevenLabs voice ID (stored in keystore; referenced here for display)
tui_theme: "default"         # reserved for Phase 2 theme switching
```

**Written by**: `ConfigLoader.save_user_config()` / `init_user_config()`.
**Read by**: `AIClient._active_model()`, `SettingsScreen`, `SetupWizard._step_ai_model()`.
**Defaults** (when file absent or key missing): `active_model: nova-fast`, `active_voice_id: null`,
`tui_theme: default`.

---

## 8. CronJob — `data/cron_jobs.yaml` (PyYAML, dormant Phase 1)

Defined in Phase 1 but holds zero entries until Phase 2 registers jobs.

```yaml
version: 1
jobs: []   # empty in Phase 1
# Each Phase 2 entry will be:
# - id: string
#   description: string
#   cron_expr: string        # raw cron or LLM-parsed from natural language
#   action_type: string      # "chat_command" | "sms_send" | "reminder"
#   action_payload: {}
#   active: true
#   created_at: ISO-8601
#   last_run: null
#   next_run: null
```

---

## 8. KeystoreEntry — `data/gurujee.keystore` (encrypted blob)

Encrypted with AES-256-GCM; never inspectable without the derived key.

Decrypted structure (in-memory only):
```json
{
  "voice_id": "<elevenlabs_voice_id_or_null>",
  "elevenlabs_api_key": "<key_or_null>",
  "sip_domain": null,
  "sip_user": null,
  "sip_caller_id": null
}
```

SIP fields are null in Phase 1; populated in Phase 2 guided config.

**On-disk format**: `nonce (12 bytes) || ciphertext || tag (16 bytes)` — raw binary.
The keystore module NEVER writes plaintext to disk.

---

## 9. AutomationLog — `data/memory.db` (SQLite, table: `automation_log`)

Append-only log of every automation command executed by `AutomationAgent`. Used for
audit, debugging, and surfacing automation history in the PWA.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK AUTOINCREMENT | Surrogate key |
| `command_type` | TEXT | NOT NULL | One of: `open_app`, `device_setting`, `ui_input`, `screenshot`, `notification` |
| `input_text` | TEXT | NOT NULL | Original natural-language command from user |
| `action_json` | TEXT | NOT NULL | JSON: resolved action params (package, coordinates, value, etc.) |
| `status` | TEXT | NOT NULL | One of: `success`, `failed`, `timeout`, `denied` |
| `error_message` | TEXT | NULL | Shell error output if status ≠ success |
| `duration_ms` | INTEGER | NULL | Execution time in milliseconds |
| `created_at` | TEXT | NOT NULL | ISO-8601 UTC timestamp |

**Indices**: `CREATE INDEX idx_automation_created ON automation_log(created_at DESC)`.
**Retention**: Last 500 entries kept; older entries pruned by `AutomationAgent` on startup.
**Writer**: `AutomationAgent` exclusively (single-writer WAL pattern, R-008).

---

## 10. NotificationCache — `data/memory.db` (SQLite, table: `notification_cache`)

Rolling cache of recent Android notifications fetched via `termux-notification-list`.
Used by the AI to answer "what are my latest notifications?" and by TTS read-aloud.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK AUTOINCREMENT | Surrogate key |
| `notif_id` | TEXT | NOT NULL | Android notification ID (string) |
| `app_package` | TEXT | NOT NULL | Source app package name |
| `app_name` | TEXT | NOT NULL | Human-readable app name |
| `title` | TEXT | NULL | Notification title |
| `content` | TEXT | NULL | Notification body text |
| `is_read` | INTEGER | NOT NULL DEFAULT 0 | 0=unread, 1=read/dismissed |
| `fetched_at` | TEXT | NOT NULL | ISO-8601 UTC timestamp when cached |

**Indices**: `CREATE INDEX idx_notif_fetched ON notification_cache(fetched_at DESC)`.
**Retention**: Last 100 entries; pruned on each fetch cycle.
**Writer**: `AutomationAgent.notifications` action on poll / on-demand fetch.
**Exposed via**: `GET /notifications` FastAPI endpoint.

---

## Entity Relationships

```
GatewayDaemon
  ├── manages 1..* AgentState
  └── owns message bus (asyncio.Queue per agent)

SoulAgent
  └── reads 1 Soul (soul_identity.yaml)

MemoryAgent
  ├── owns deque of ConversationTurn (short-term)
  ├── owns SQLite connection → MemoryRecord (long-term)
  └── reads/writes CronJob YAML (Phase 2)

HeartbeatAgent
  └── monitors/restarts AgentState entries

UserAgent
  └── reads user profile from soul_identity.yaml (user_name field)

CronAgent (dormant)
  └── reads CronJob YAML (empty in Phase 1)

AutomationAgent (on-demand)
  ├── dispatches via automation/tool_router.py → automation/actions/*.py
  ├── executes via automation/executor.py (ShizukuExecutor subprocess)
  ├── writes AutomationLog (data/memory.db, automation_log table)
  └── writes NotificationCache (data/memory.db, notification_cache table)

FastAPI Server (not an agent — asyncio task in GatewayDaemon)
  ├── POST /chat → SoulAgent via MessageBus → SSE stream to PWA
  ├── GET  /agents → GatewayDaemon agent status snapshot
  ├── POST /automate → AutomationAgent via MessageBus
  ├── GET  /notifications → NotificationCache (latest 20)
  ├── GET  /health → GatewayDaemon ready flag
  └── WebSocket /ws → GatewayDaemon broadcast bus (real-time push)

Keystore (not an agent — a module)
  └── read by SoulAgent (voice_id), GatewayDaemon (Phase 2 SIP)

SetupWizard (not an agent — a Rich CLI / PWA-guided)
  └── writes SetupState
  └── writes Keystore entries
  └── writes soul_identity.yaml initial values
```
