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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from urllib.parse import urlparse

import yaml

import httpx
from openai import AsyncOpenAI

from gurujee.config.loader import ConfigLoader

logger = logging.getLogger(__name__)

# Fallback security anchors used when config/security.yaml cannot be loaded.
# Authoritative list lives in config/security.yaml (network_allowlist.security_anchors).
_SECURITY_ANCHOR_HOSTS = frozenset({
    "gen.pollinations.ai",  # always permit Pollinations default even if models.yaml missing
    "api.elevenlabs.io",
    "sip.suii.us",          # Phase 2 SIP calling
    "stun.l.google.com",    # Phase 2 SIP STUN
    "api.deepgram.com",     # Phase 2 optional cloud STT
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
        """
        Return whether this profile is currently available for requests.
        
        Checks that the current monotonic time is greater than or equal to both the rate-limit cooling deadline and the billing-disabled deadline.
        
        Returns:
            `true` if the current monotonic time is greater than or equal to both `_cooling_until` and `_billing_disabled_until`, `false` otherwise.
        """
        now = time.monotonic()
        return now >= self._cooling_until and now >= self._billing_disabled_until

    def apply_rate_limit(self) -> None:
        """
        Apply a progressive rate-limit cooldown to the profile.
        
        Sets the profile's cooling deadline (self._cooling_until) to the current monotonic time plus a delay chosen from [60, 300, 1500, 3600] seconds based on the current rate-limit count, then increments self._rate_limit_count.
        """
        steps = [60, 300, 1500, 3600]  # 1 min → 5 → 25 → 60
        secs = steps[min(self._rate_limit_count, len(steps) - 1)]
        self._cooling_until = time.monotonic() + secs
        self._rate_limit_count += 1
        logger.info("Profile rate-limited — cooldown %ds", secs)

    def apply_billing_disable(self) -> None:
        """
        Apply a billing-disable cooldown to the profile.
        
        Sets the profile's billing-disabled deadline to the current monotonic time plus a cooldown interval selected from 5 hours, 10 hours, 20 hours, or 24 hours depending on how many billing disables have already been applied. Also increments the internal billing-disable counter and emits a warning log indicating the cooldown duration (in seconds).
        """
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
        """
        Initialize the AIClient.
        
        Parameters:
            models_config_path (Path): Filesystem path to the models configuration (e.g., models.yaml) that defines providers and model routing.
            user_config_path (Path): Filesystem path to the user configuration (stores settings such as active_model).
            keystore (Any): Optional keystore used to resolve provider API keys; may be None.
        """
        self._models_config_path = Path(models_config_path)
        self._user_config_path = Path(user_config_path)
        self._keystore = keystore
        self._pending_queue: deque[dict[str, Any]] = deque()
        # Legacy cached client (used when _stream is patched in tests)
        self._client: Optional[AsyncOpenAI] = None
        # In-memory auth profile cooldown states: provider_key -> state
        self._profile_states: dict[str, _ProfileState] = {}
        # Hosts temporarily permitted for this session via allow_once policy.
        self._session_allowed_hosts: set[str] = set()
        self._cached_allowlist: Optional[frozenset[str]] = None

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Yield response tokens as they arrive.
        
        Accepts either a "provider/model-id" string or a legacy bare model name. Retries up to 3 times on network connect/timeout errors; if any tokens have already been yielded the stream will not be retried.
        
        Parameters:
            messages (list[dict[str, str]]): Conversation messages, each typically containing 'role' and 'content'.
            model (Optional[str]): Provider-scoped model identifier (e.g., "provider/model-id") or a legacy model name.
            tools (Optional[list]): Optional tool specifications to enable tool-aware completions.
        
        Returns:
            AsyncGenerator[str, None]: An async stream of tokens. Tokens are returned as strings; tool call events may appear as special token strings.
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
        """
        Resolve the model identifier to use for the given agent from models.yaml.
        
        Parameters:
            agent_name (str): Agent key used to look up an entry in `agent_model_routing`.
        
        Returns:
            str: The model string routed for the agent (e.g., "provider/model-id"). If no routing entry exists, returns `default["primary"]` from the models config when available, otherwise `"pollinations/nova-fast"`.
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
        """
        Return a catalog of configured model providers and the configured default routing.
        
        The returned dictionary contains:
        - "builtin": mapping of builtin provider key -> {
            "label": provider display label,
            "api_compat": compatibility mode (e.g., "openai" or "anthropic"),
            "api_key_required": whether an API key is required (bool),
            "models": list of model IDs (strings)
          }
        - "custom": same structure as "builtin" for custom providers
        - "default": the raw `default` value from the models configuration (used for default model routing)
        """
        cfg = ConfigLoader.load_yaml(self._models_config_path)

        def _summarise(section: str) -> dict[str, Any]:
            """
            Build a summary mapping of providers from the given configuration section.
            
            Parameters:
            	section (str): Key in the loaded models configuration whose providers should be summarized (e.g., "builtin_providers" or "custom_providers").
            
            Returns:
            	dict[str, Any]: Mapping from provider name to a summary dict with keys:
            		- `label` (str): Human-readable label for the provider (falls back to the provider name).
            		- `api_compat` (str): API compatibility mode, e.g. "openai" or "anthropic".
            		- `api_key_required` (bool): Whether an API key is required for this provider.
            		- `models` (list[str]): List of model IDs exposed by the provider.
            """
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
        """
        Stream queued chat requests in FIFO order, yielding each streamed token paired with its original request payload.
        
        Each queued item is streamed via stream_chat; if streaming of an item completes successfully the item is removed from the queue. If a connection, timeout, or HTTP status error occurs while processing an item, iteration stops and the remaining queue is left intact.
        
        Returns:
            tuple[dict[str, Any], str]: Tuples of (original_request_payload, token) where `original_request_payload` is the queued dict and `token` is a single streamed text token.
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
        """
        Enqueue a chat request for later retry after a failure.
        
        Parameters:
            messages (list[dict[str, str]]): Sequence of message objects representing the conversation; each message is a mapping of string keys (commonly 'role' and 'content') to string values.
            model (Optional[str]): Optional model identifier to use when retrying (e.g., "provider/model-id" or a legacy model name).
        """
        self._pending_queue.append({"messages": messages, "model": model})

    # ------------------------------------------------------------------ #
    # Internals — provider resolution                                       #
    # ------------------------------------------------------------------ #

    def _resolve_provider(
        self, model_str: str
    ) -> tuple[str, str, dict[str, Any]]:
        """
        Resolve provider, model id, and provider configuration from a model string.
        
        Accepts either the ADR-005 form "provider/model-id" or a legacy bare model name.
        In the ADR-005 form the provider is looked up in the models config; for a bare
        model name a legacy provider configuration is returned (using endpoint.base_url).
        
        Parameters:
            model_str (str): Model identifier in either "provider/model-id" form or a bare model name.
        
        Returns:
            tuple: (provider, model_id, provider_cfg)
                provider (str): Resolved provider key (e.g., "pollinations").
                model_id (str): The model identifier (the part after the slash, or the bare name for legacy).
                provider_cfg (dict[str, Any]): Provider configuration dictionary resolved from the models config or legacy endpoint.
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
        """
        Resolve the named provider's configuration from the models config.
        
        Searches `builtin_providers` then `custom_providers` in `cfg` for `provider` and returns a copy of that provider's configuration. If the provider is not found, logs a warning and returns the legacy provider configuration obtained from `_get_legacy_provider_config(cfg)`.
        
        Parameters:
            cfg (dict[str, Any]): Parsed models configuration dictionary.
            provider (str): Provider key to look up (e.g., "pollinations" or custom provider name).
        
        Returns:
            dict[str, Any]: Provider configuration dictionary.
        """
        for section in ("builtin_providers", "custom_providers"):
            if provider in cfg.get(section, {}):
                return dict(cfg[section][provider])
        logger.warning(
            "AIClient: unknown provider '%s' — falling back to pollinations", provider
        )
        return self._get_legacy_provider_config(cfg)

    def _get_legacy_provider_config(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve a legacy provider configuration from a parsed models config for backward compatibility.
        
        If the top-level `endpoint.base_url` is present, returns an OpenAI-compatible config using that base URL and with `api_key_required` set to False. Otherwise, prefer the builtin `pollinations` provider entry if available; if not, return a sensible default pointing to Pollinations' public endpoint.
        
        Parameters:
            cfg (dict[str, Any]): Parsed models configuration (e.g., contents of models.yaml).
        
        Returns:
            dict[str, Any]: Provider configuration with keys:
                - `base_url` (str): The provider base URL.
                - `api_key_required` (bool): Whether an API key is required.
                - `api_compat` (str): Compatibility mode, typically `"openai"`.
        """
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
        """
        Resolve the API key for a provider from the injected keystore without reading environment variables.
        
        Parameters:
            provider_cfg (dict[str, Any]): Provider configuration; may include "api_key_required" (bool) and "auth_env" (str) specifying the keystore key name.
        
        Returns:
            str: The API key from the keystore if present and required, otherwise an empty string.
        """
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
        """
        Selects the active model identifier using user configuration with models.yaml fallbacks.
        
        Returns:
            The chosen model identifier as a string. Preference order: the user's `active_model` from user config, `default["primary"]` from models config (if present), the top-level `default` value from models config, and finally `"nova-fast"` as a fallback.
        """
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
        """Build the dynamic allowlist from config/security.yaml anchors + all provider base_urls.

        Sources (merged):
        1. Security anchors from config/security.yaml (network_allowlist.security_anchors).
        2. base_url hostnames from all builtin_providers + custom_providers in models.yaml.
        3. Hardcoded _SECURITY_ANCHOR_HOSTS fallback if security.yaml is unreadable.
        """
        if self._cached_allowlist is not None:
            # Check if session hosts were added since cache was built.
            if self._session_allowed_hosts.issubset(self._cached_allowlist):
                return self._cached_allowlist

        hosts: set[str] = set(_SECURITY_ANCHOR_HOSTS)

        # Load security anchors and user-approved hosts from config/security.yaml.
        _sec_log_file: Optional[str] = None
        try:
            security_cfg_path = self._models_config_path.parent / "security.yaml"
            if security_cfg_path.exists():
                sec_cfg = ConfigLoader.load_yaml(security_cfg_path)
                net = sec_cfg.get("network_allowlist", {})
                anchors = (
                    net.get("security_anchors", [])
                    or sec_cfg.get("anchor_hosts", [])  # legacy key
                )
                for entry in anchors:
                    host = entry.get("host", "") if isinstance(entry, dict) else str(entry)
                    if host:
                        hosts.add(host)
                for h in net.get("user_approved_hosts", []):
                    if isinstance(h, str) and h:
                        hosts.add(h)
                _sec_log_file = net.get("log_file")
        except (FileNotFoundError, OSError, yaml.YAMLError, ValueError, KeyError) as exc:
            logger.warning("AIClient: could not load security.yaml anchors: %s", exc)

        # Hosts permitted for this session via allow_once policy.
        hosts.update(self._session_allowed_hosts)

        # Load provider base_urls from models.yaml
        try:
            cfg = ConfigLoader.load_yaml(self._models_config_path)
            for section in ("builtin_providers", "custom_providers"):
                for _name, prov in cfg.get(section, {}).items():
                    base_url = prov.get("base_url", "")
                    if base_url:
                        host = urlparse(base_url).hostname or ""
                        if host:
                            hosts.add(host)
        except (FileNotFoundError, OSError, yaml.YAMLError, ValueError, KeyError) as exc:
            logger.warning("AIClient: could not load models.yaml providers: %s", exc)

        allowlist = frozenset(hosts)
        logger.debug("AIClient: allowlist built (%d hosts): %s", len(allowlist), sorted(allowlist))

        # Log the built allowlist to security.log if configured.
        if _sec_log_file:
            self._append_security_log(
                _sec_log_file,
                f"ALLOWLIST_BUILT hosts={sorted(allowlist)}",
            )

        self._cached_allowlist = allowlist
        return allowlist

    def _check_allowlist(self, url: str) -> None:
        """Enforce the network allowlist, respecting the configured unknown_host_policy.

        Raises:
            AllowlistViolation: If the host is not permitted by policy.
        """
        host = urlparse(url).hostname or ""
        allowed = self._build_allowlist()
        if host in allowed:
            return

        # Load policy settings from security.yaml.
        policy = "block"
        log_blocked = False
        sec_log_file: Optional[str] = None
        try:
            sec_path = self._models_config_path.parent / "security.yaml"
            if sec_path.exists():
                sec_cfg = ConfigLoader.load_yaml(sec_path)
                net = sec_cfg.get("network_allowlist", {})
                policy = net.get("unknown_host_policy", "block")
                log_blocked = bool(net.get("log_blocked_requests", False))
                sec_log_file = net.get("log_file")
        except (FileNotFoundError, OSError, yaml.YAMLError, ValueError, KeyError) as exc:
            logger.warning("AIClient: could not load security.yaml policy: %s", exc)

        if policy == "allow_once":
            self._session_allowed_hosts.add(host)
            logger.info("AIClient: allow_once — temporarily permitting host=%s for this session", host)
            if log_blocked and sec_log_file:
                self._append_security_log(
                    sec_log_file,
                    f"ALLOW_ONCE host={host} url={url}",
                )
            return

        logger.warning(
            "AIClient: allowlist violation host=%s url=%s policy=%s",
            host, url, policy,
        )
        if log_blocked and sec_log_file:
            self._append_security_log(
                sec_log_file,
                f"BLOCKED host={host} url={url} policy={policy}",
            )

        # policy == "block" or "prompt_user" (daemon cannot prompt interactively; fail closed)
        raise AllowlistViolation(
            f"Host '{host}' is not in the GURUJEE network allowlist. "
            f"Allowed: {sorted(allowed)}"
        )

    def _append_security_log(self, log_file: str, message: str) -> None:
        """Append a timestamped entry to the security log file."""
        try:
            path = Path(log_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with path.open("a", encoding="utf-8") as fh:
                fh.write(f"{ts} {message}\n")
        except OSError as exc:
            logger.warning("AIClient: could not write to security log %s: %s", log_file, exc)

    # ------------------------------------------------------------------ #
    # Internals — legacy client cache (used when _stream is mocked)         #
    # ------------------------------------------------------------------ #

    def _get_client(self) -> AsyncOpenAI:
        """
        Get or create a cached AsyncOpenAI client using the legacy `endpoint.base_url` from the models config.
        
        If no client is cached, loads the models config, extracts `endpoint.base_url` (defaults to https://gen.pollinations.ai/v1), enforces the outbound allowlist for that URL, constructs an AsyncOpenAI client with an empty API key, caches it, and returns it.
        
        Returns:
            AsyncOpenAI: The cached AsyncOpenAI client instance.
        """
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
        """
        Stream tokens and tool-call markers from an OpenAI-compatible streaming chat endpoint.
        
        Yields text chunks produced by the model as they arrive. When the model emits a tool call, the function yields a special marker token with a JSON payload describing the tool invocation.
        
        Parameters:
            tools (Optional[list]): Optional list of tool descriptors to pass through to the backend; when provided, `tool_choice` is set to `"auto"`.
        
        Returns:
            token (str): Sequential text tokens from the streaming response. Tool calls are emitted as strings formatted as:
            `__tool_call__:{"name": "<function name>", "arguments": "<arguments JSON>"}`.
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
        """
        Stream tokens from an Anthropic-compatible model using the anthropic SDK.
        
        provider_cfg may include a "_resolved_api_key" key with the API key to use; if absent or empty the client is created without a key.
        
        Parameters:
            provider_cfg (dict[str, Any]): Provider configuration dictionary; may contain `_resolved_api_key`.
            messages (list[dict[str, str]]): Conversation messages where each message has at least a `role` and `content`.
            model (str): Anthropic model identifier to request.
            tools (Optional[list]): Optional tools metadata (not used by this backend).
        
        Returns:
            AsyncGenerator[str, None]: An async generator yielding streamed text chunks from the model.
        
        Raises:
            ImportError: If the `anthropic` package is not installed (install with `pip install anthropic>=0.40.0`).
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
