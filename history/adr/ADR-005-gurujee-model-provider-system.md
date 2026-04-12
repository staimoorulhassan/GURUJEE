# ADR-005: Multi-Provider Model System — OpenClaw-Equivalent Architecture

- **Status:** Accepted
- **Date:** 2026-04-12
- **Feature:** 002-gurujee-comms (applicable from Phase 2 onward; backport to Phase 1 config)
- **Amendment trigger:** P2 single-endpoint restriction is incompatible with user need to
  use Claude, local Ollama models, OpenRouter, Groq, and other providers.

## Context

Constitution P2 (v1.1.1) hard-codes a single inference endpoint: `gen.pollinations.ai/v1`.
This was correct for Phase 1 (free default, no key required, ARM64-compatible). Phase 2 adds
voice calling (ElevenLabs TTS + Whisper STT) and the user needs to be able to:

1. Use Claude for better reasoning quality (Anthropic API, OpenCode OAuth, or Bedrock)
2. Run local models on a connected PC via Ollama (privacy, offline)
3. Use DeepSeek/Qwen via Groq for fast cheap inference on Android
4. Keep Pollinations as the zero-key default when no provider is configured

The OpenClaw project (docs.openclaw.ai/providers) has documented a clean provider
catalogue format with two-stage failover that maps well onto GURUJEE's needs.

---

## Decision

Adopt an OpenClaw-equivalent multi-provider architecture for all AI inference in GURUJEE:

**Provider format**: `provider/model-id` (e.g., `"anthropic/claude-opus-4-6"`,
`"ollama/llama3.3"`, `"openrouter/deepseek/deepseek-r1"`).

**Provider tiers** (defined in `config/models.yaml`):
- **Tier 1 — Built-in**: Pollinations, OpenAI, Anthropic, Google, OpenCode, Z.AI,
  Vercel AI Gateway, Kilo Gateway. No `models.providers` config needed — set auth key
  in keystore and pick a model.
- **Tier 2 — Custom**: Ollama, vLLM, SGLang, LiteLLM, OpenRouter, DeepSeek, Groq,
  Mistral, NVIDIA, Moonshot, Together, Perplexity, Hugging Face, and more. Defined by
  `base_url` + `api_compat` in `models.yaml`.

**Auth storage**: All API keys stored in `data/gurujee.keystore` (AES-256-GCM, per P4).
Never in `config/models.yaml` or environment variables. Resolution priority per provider:
1. `GURUJEE_LIVE_{PROVIDER}_KEY` (session override)
2. `{PROVIDER}_API_KEYS` (comma-separated rotation list)
3. `{PROVIDER}_API_KEY_1`, `_2`, ... (numbered list)
4. `{PROVIDER}_API_KEY` (single key)

**Two-stage failover**:
- Stage 1 — Auth profile rotation within the current provider. Exponential cooldown:
  1 min → 5 min → 25 min → 1 hr on rate limits. Billing disable: 5 hr → 10 → 20 → 24 hr.
  Rotate only on: 429, rate_limit, quota, resource_exhausted, timeout.
  Fail immediately on: invalid_request, format_error, content_policy.
- Stage 2 — Advance to next model in `model_fallbacks` list. Only triggers when all
  Stage 1 profiles are exhausted or cooling down.

**Pollinations remains the default**: zero-key, `api_key_required: false`. If no other
provider is configured, GURUJEE works out of the box with no setup.

**Allowlist updated**: Static `_ALLOWED_HOSTS` replaced by dynamic allowlist derived
from all `base_url` values in `config/models.yaml` + `config/security.yaml` anchors.
User-added providers are permitted once they appear in the catalogue.

**Per-agent model routing**: `agent_model_routing` section in `models.yaml` allows
directing different agents to different providers (e.g., soul → expensive reasoning model,
heartbeat → cheap fast model).

**Constitution P2 amendment**: Amended to v1.2.0 (MINOR — P2 materially expanded from
single-endpoint to provider catalogue system).

---

## Consequences

### Positive

- Users can upgrade to Claude, Gemini, DeepSeek with zero code changes — just add
  a key to the keystore via the Settings UI
- Pollinations zero-key default preserved — GURUJEE still works for new users with
  zero configuration
- Failover across providers means degraded one provider does not break the assistant
- Per-agent routing enables cost optimization (cheap model for heartbeat, powerful model
  for soul conversations)
- Ollama support enables fully offline operation on a local network (Android + PC)
- OpenRouter gives access to 100+ models through a single API key

### Negative

- `config/models.yaml` grows from 12 lines to ~300+ lines. Adds configuration complexity.
- `ai/client.py` is more complex — provider resolution, auth rotation, failover state
- Tests must mock multiple layers (provider config, keystore, HTTP) for failover scenarios
- Anthropic SDK (`anthropic` package) is a new dependency (~15 MB on ARM64 Termux)
- Constitution P2 is now harder to enforce — "permitted providers" is open-ended

### Risks

- ARM64 compatibility must be verified for each new package added (P6 rule)
- Auth rotation state is in-memory only — a daemon restart resets cooldown timers

---

## Alternatives Considered

### Option A — Keep single endpoint, add model aliases (minimal change)

Keep `gen.pollinations.ai` as the only endpoint. Map "claude" → Pollinations' Claude
proxy (if available). User cannot use direct Anthropic/OpenAI APIs.

**Why rejected**: Pollinations does not proxy all providers. Users specifically requested
Claude Opus 4.6 and local Ollama models. This blocks Phase 2 voice quality improvements
that need better reasoning models.

### Option B — Hard-code 3–5 known providers (LiteLLM style)

Hard-code OpenAI, Anthropic, Google, and Pollinations. No plugin catalogue.

**Why rejected**: Every new provider requires code changes. OpenRouter, Groq, local
providers (Ollama, vLLM) would not be supported. Over-engineering in the wrong direction.

---

## References

- Feature Spec: `specs/002-gurujee-comms/spec.md`
- ADR-003: Split-Process Daemon + PWA Architecture
- ADR-004: AutomationAgent Always-On Lifecycle
- Constitution P2: `.specify/memory/constitution.md` (amended to v1.2.0)
- Provider catalogue: `config/models.yaml`
- Implementation: `gurujee/ai/client.py`
- Tests: `tests/test_model_client.py`
- Reference: OpenClaw provider documentation pattern (docs.openclaw.ai/providers)
