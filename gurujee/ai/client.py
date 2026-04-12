"""AsyncOpenAI wrapper with multi-provider support, auth rotation, and two-stage failover.

Provider format: "provider/model-id" (e.g. "anthropic/claude-opus-4-6", "ollama/llama3.3").
Falls back to legacy bare-model-name format (uses endpoint.base_url from models.yaml).
See ADR-005 and config/models.yaml for the full provider catalogue.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from urllib.parse import urlparse

import httpx
from openai import AsyncOpenAI

from gurujee.config.loader import ConfigLoader

logger = logging.getLogger(__name__)

# Security anchors — always permitted regardless of provider config.
_SECURITY_ANCHOR_HOSTS = frozenset({
    "gen.pollinations.ai",
    "api.elevenlabs.io",
    "sip.suii.us",       # Phase 2 SIP calling
    "stun.l.google.com", # Phase 2 SIP STUN
    "api.deepgram.com",  # Phase 2 optional cloud STT
})

# Backward-compat alias (existing tests do `from gurujee.ai.client import _ALLOWED_HOSTS`
# indirectly via AllowlistViolation message; kept so grep never misleads).
_ALLOWED_HOSTS = _SECURITY_ANCHOR_HOSTS


@dataclass
class _ProfileState:
    """Tracks per-profile rate-limit and billing-disable cooldowns (in-memory)."""

    key: str
    _cooling_until: float = 0.0          # monotonic epoch
    _billing_disabled_until: float = 0.0  # monotonic epoch
    _rate_limit_count: int = 0
    _billing_count: int = 0

    def is_available(self) -> bool:
        now = time.monotonic()
        return now >= self._cooling_until and now >= self._billing_disabled_until

    def apply_rate_limit(self) -> None:
        steps = [60, 300, 1500, 3600]  # 1 min → 5 → 25 → 60
        secs = steps[min(self._rate_limit_count, len(steps) - 1)]
        self._cooling_until = time.monotonic() + secs
        self._rate_limit_count += 1
        logger.info("Profile rate-limited — cooldown %ds", secs)

    def apply_billing_disable(self) -> None:
        steps = [18000, 36000, 72000, 86400]  # 5 hr → 10 → 20 → 24
        secs = steps[min(self._billing_count, len(steps) - 1)]
        self._billing_disabled_until = time.monotonic() + secs
        self._billing_count += 1
        logger.warning("Profile billing-disabled — cooldown %ds", secs)


class AllowlistViolation(Exception):
    """Raised when an outbound host is not in the GURUJEE network allowlist."""


class AIClient:
    """Multi-provider AI client.

    Supports the "provider/model-id" format from ADR-005. Legacy bare-model
    names (e.g. "nova-fast") still resolve via the old endpoint.base_url config
    field for full backward compatibility with Phase 1 tests.
    """

    def __init__(
        self,
        models_config_path: Path,
        user_config_path: Path,
        keystore: Any = None,  # Optional[Keystore] — avoids circular import
    ) -> None:
        self._models_config_path = Path(models_config_path)
        self._user_config_path = Path(user_config_path)
        self._keystore = keystore
        self._pending_queue: deque[dict[str, Any]] = deque()
        # Legacy cached client (used when _stream is patched in tests)
        self._client: Optional[AsyncOpenAI] = None
        # In-memory auth profile cooldown states: provider_key -> state
        self._profile_states: dict[str, _ProfileState] = {}

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        """Yield response tokens as they arrive.

        Accepts either "provider/model-id" or a legacy bare model name.
        Retries up to 3 times on ConnectError / TimeoutException (no mid-stream
        retry — already-delivered tokens cannot be re-sent safely).
        """
        resolved_model = model or self._active_model()
        provider, model_id, provider_cfg = self._resolve_provider(resolved_model)
        api_compat = provider_cfg.get("api_compat", "openai")
        base_url: str = provider_cfg.get("base_url", "https://gen.pollinations.ai/v1")
        self._check_allowlist(base_url)

        api_key = self._get_api_key_for_provider(provider_cfg)
        openai_client = AsyncOpenAI(base_url=base_url, api_key=api_key or "")
        last_exc: Optional[Exception] = None

        for attempt in range(3):
            tokens_yielded = 0
            try:
                if api_compat == "anthropic":
                    provider_cfg_with_key = dict(provider_cfg, _resolved_api_key=api_key)
                    stream_gen = self._anthropic_stream(
                        provider_cfg_with_key, messages, model_id, tools
                    )
                else:
                    # openai / openai-responses — call _stream so tests can patch it
                    stream_gen = self._stream(openai_client, messages, model_id, tools)
                async for token in stream_gen:
                    tokens_yielded += 1
                    yield token
                return
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if tokens_yielded > 0:
                    # Already sent tokens — cannot safely restart the stream.
                    raise
                last_exc = exc
                logger.warning(
                    "AIClient: stream attempt %d/3 failed (%s), retrying...",
                    attempt + 1,
                    exc,
                )
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt * 2)  # 2s, 4s

        assert last_exc is not None
        raise last_exc

    def get_model_for_agent(self, agent_name: str) -> str:
        """Return the model string configured for *agent_name* in models.yaml.

        Falls back to the default primary model if no routing entry exists.
        """
        cfg = ConfigLoader.load_yaml(self._models_config_path)
        routing = cfg.get("agent_model_routing", {})
        if agent_name in routing:
            return str(routing[agent_name])
        default = cfg.get("default", {})
        if isinstance(default, dict):
            return str(default.get("primary", "pollinations/nova-fast"))
        return str(default) if default else "pollinations/nova-fast"

    def list_provider_catalog(self) -> dict[str, Any]:
        """Return all configured providers (used by GET /api/models/providers)."""
        cfg = ConfigLoader.load_yaml(self._models_config_path)

        def _summarise(section: str) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for name, prov in cfg.get(section, {}).items():
                models_raw = prov.get("models", [])
                model_ids = [
                    m.get("id") if isinstance(m, dict) else m
                    for m in models_raw
                ]
                result[name] = {
                    "label": prov.get("label", name),
                    "api_compat": prov.get("api_compat", "openai"),
                    "api_key_required": prov.get("api_key_required", True),
                    "models": model_ids,
                }
            return result

        return {
            "builtin": _summarise("builtin_providers"),
            "custom": _summarise("custom_providers"),
            "default": cfg.get("default", {}),
        }

    async def retry_pending(self) -> AsyncGenerator[tuple[dict[str, Any], str], None]:
        """Re-send queued messages one at a time.

        Yields (original_request_payload, token) pairs.
        Removes each message from the queue on success.
        """
        while self._pending_queue:
            item = self._pending_queue[0]
            try:
                async for token in self.stream_chat(item["messages"], item.get("model")):
                    yield item, token
                self._pending_queue.popleft()
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
                break  # network still down — leave in queue

    def enqueue_pending(
        self, messages: list[dict[str, str]], model: Optional[str] = None
    ) -> None:
        """Add a failed request to the retry queue."""
        self._pending_queue.append({"messages": messages, "model": model})

    # ------------------------------------------------------------------ #
    # Internals — provider resolution                                       #
    # ------------------------------------------------------------------ #

    def _resolve_provider(
        self, model_str: str
    ) -> tuple[str, str, dict[str, Any]]:
        """Parse model string and return (provider, model_id, provider_cfg).

        Handles:
        - "provider/model-id"  → new ADR-005 format
        - "bare-model-name"    → legacy; resolves via endpoint.base_url
        """
        cfg = ConfigLoader.load_yaml(self._models_config_path)
        if "/" in model_str:
            provider, model_id = model_str.split("/", 1)
            provider_cfg = self._get_provider_config(cfg, provider)
            return provider, model_id, provider_cfg
        # Legacy bare-name — use old endpoint.base_url config
        provider_cfg = self._get_legacy_provider_config(cfg)
        return "pollinations", model_str, provider_cfg

    def _get_provider_config(
        self, cfg: dict[str, Any], provider: str
    ) -> dict[str, Any]:
        """Look up a provider from builtin_providers or custom_providers."""
        for section in ("builtin_providers", "custom_providers"):
            if provider in cfg.get(section, {}):
                return dict(cfg[section][provider])
        logger.warning(
            "AIClient: unknown provider '%s' — falling back to pollinations", provider
        )
        return self._get_legacy_provider_config(cfg)

    def _get_legacy_provider_config(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """Handle old-style endpoint.base_url config (Phase 1 backward compat)."""
        endpoint = cfg.get("endpoint", {})
        if endpoint and "base_url" in endpoint:
            return {
                "base_url": endpoint["base_url"],
                "api_key_required": False,
                "api_compat": "openai",
            }
        # Prefer pollinations built-in if present
        pollinations = cfg.get("builtin_providers", {}).get("pollinations", {})
        if pollinations:
            return dict(pollinations)
        return {
            "base_url": "https://gen.pollinations.ai/v1",
            "api_key_required": False,
            "api_compat": "openai",
        }

    def _get_api_key_for_provider(self, provider_cfg: dict[str, Any]) -> str:
        """Resolve API key from keystore. Never reads os.environ directly."""
        if not provider_cfg.get("api_key_required", True):
            return ""
        if self._keystore is None:
            return ""
        auth_env = provider_cfg.get("auth_env", "")
        if auth_env and hasattr(self._keystore, "get"):
            try:
                key = self._keystore.get(auth_env)
                if key:
                    return str(key)
            except Exception:
                pass
        return ""

    # ------------------------------------------------------------------ #
    # Internals — model resolution                                          #
    # ------------------------------------------------------------------ #

    def _active_model(self) -> str:
        user_cfg = ConfigLoader.load_user_config(self._user_config_path)
        model_from_user = user_cfg.get("active_model")
        if model_from_user:
            return str(model_from_user)
        models_cfg = ConfigLoader.load_yaml(self._models_config_path)
        default = models_cfg.get("default", {})
        if isinstance(default, dict):
            return str(default.get("primary", "nova-fast"))
        return str(default) if default else "nova-fast"

    # ------------------------------------------------------------------ #
    # Internals — allowlist                                                 #
    # ------------------------------------------------------------------ #

    def _build_allowlist(self) -> frozenset[str]:
        """Build the dynamic allowlist: security anchors + all provider base_urls."""
        hosts: set[str] = set(_SECURITY_ANCHOR_HOSTS)
        try:
            cfg = ConfigLoader.load_yaml(self._models_config_path)
            for section in ("builtin_providers", "custom_providers"):
                for _name, prov in cfg.get(section, {}).items():
                    base_url = prov.get("base_url", "")
                    if base_url:
                        host = urlparse(base_url).hostname or ""
                        if host:
                            hosts.add(host)
        except Exception:
            pass
        return frozenset(hosts)

    def _check_allowlist(self, url: str) -> None:
        """Raise AllowlistViolation if *url*'s host is not in the allowlist."""
        host = urlparse(url).hostname or ""
        allowed = self._build_allowlist()
        if host not in allowed:
            raise AllowlistViolation(
                f"Host '{host}' is not in the GURUJEE network allowlist. "
                f"Allowed: {sorted(allowed)}"
            )

    # ------------------------------------------------------------------ #
    # Internals — legacy client cache (used when _stream is mocked)         #
    # ------------------------------------------------------------------ #

    def _get_client(self) -> AsyncOpenAI:
        """Return a cached AsyncOpenAI client built from legacy config format."""
        if self._client is None:
            models_cfg = ConfigLoader.load_yaml(self._models_config_path)
            endpoint = models_cfg.get("endpoint", {})
            base_url: str = endpoint.get("base_url", "https://gen.pollinations.ai/v1")
            self._check_allowlist(base_url)
            self._client = AsyncOpenAI(base_url=base_url, api_key="")
        return self._client

    # ------------------------------------------------------------------ #
    # Internals — streaming backends                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    async def _stream(
        client: AsyncOpenAI,
        messages: list[dict[str, str]],
        model: str,
        tools: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from an OpenAI-compatible endpoint.

        Signature is stable — existing tests mock this method at instance level
        via patch.object(client, "_stream", ...).
        """
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,  # type: ignore[arg-type]
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue
            if delta.content:
                yield delta.content
            # Surface tool_calls as a special token so callers can detect them
            if getattr(delta, "tool_calls", None):
                import json as _json
                for tc in delta.tool_calls:
                    fn = getattr(tc, "function", None)
                    if fn:
                        yield (
                            f"__tool_call__:{_json.dumps({'name': fn.name or '', 'arguments': fn.arguments or '{}'})}"
                        )

    @staticmethod
    async def _anthropic_stream(
        provider_cfg: dict[str, Any],
        messages: list[dict[str, str]],
        model: str,
        tools: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the Anthropic SDK.

        Requires ``pip install anthropic>=0.40.0``.
        *provider_cfg* may contain ``_resolved_api_key`` injected by stream_chat.
        """
        try:
            import anthropic  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "anthropic package required for Anthropic provider. "
                "Install: pip install anthropic>=0.40.0"
            ) from exc

        api_key = provider_cfg.get("_resolved_api_key", "")
        aclient = anthropic.AsyncAnthropic(api_key=api_key)

        # Anthropic separates the system prompt from the messages list
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        user_messages = [m for m in messages if m.get("role") != "system"]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": user_messages,
            "max_tokens": 4096,
        }
        if system_parts:
            kwargs["system"] = "\n".join(system_parts)

        async with aclient.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
