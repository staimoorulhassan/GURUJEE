"""Tests for multi-provider AIClient (ADR-005).

Covers: provider resolution, auth key rotation, billing disable cooldown,
two-stage model fallback, and the /api/models/providers catalog endpoint.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from gurujee.ai.client import AIClient, AllowlistViolation


# ------------------------------------------------------------------ #
# Fixtures                                                              #
# ------------------------------------------------------------------ #

MINIMAL_MODELS_YAML = """\
mode: merge

default:
  primary: "pollinations/nova-fast"
  fallbacks:
    - "pollinations/gemini-fast"

builtin_providers:
  pollinations:
    label: "Pollinations AI (Free, No Key)"
    base_url: "https://gen.pollinations.ai/v1"
    api_key_required: false
    api_compat: "openai"
    models:
      - {id: nova-fast, label: "Nova Fast", ctx: 32000, caps: [chat]}
      - {id: gemini-fast, label: "Gemini Fast", ctx: 128000, caps: [chat]}

  anthropic:
    label: "Anthropic (Claude)"
    base_url: "https://api.anthropic.com/v1"
    api_key_required: true
    api_compat: "anthropic"
    auth_env: "ANTHROPIC_API_KEY"
    models:
      - {id: claude-opus-4-6, label: "Claude Opus 4.6", ctx: 200000, caps: [chat]}

custom_providers:
  ollama:
    label: "Ollama (Local)"
    base_url: "http://127.0.0.1:11434/v1"
    api_key_required: false
    api_compat: "openai-responses"
    dynamic_catalog: true
    models: []

  openrouter:
    label: "OpenRouter"
    base_url: "https://openrouter.ai/api/v1"
    api_key_required: true
    api_compat: "openai"
    auth_env: "OPENROUTER_API_KEY"
    models:
      - {id: "openrouter/deepseek/deepseek-r1", label: "DeepSeek R1", ctx: 64000}

agent_model_routing:
  soul: "pollinations/nova-fast"
  heartbeat: "pollinations/nova-fast"
  orchestrator: "pollinations/gemini-fast"

user_providers: []
"""


@pytest.fixture
def client(tmp_path: Path) -> AIClient:
    models_path = tmp_path / "models.yaml"
    models_path.write_text(MINIMAL_MODELS_YAML, encoding="utf-8")
    user_config_path = tmp_path / "user_config.yaml"
    user_config_path.write_text("active_model: pollinations/nova-fast\n", encoding="utf-8")
    return AIClient(
        models_config_path=models_path,
        user_config_path=user_config_path,
    )


@pytest.fixture
def client_with_keystore(tmp_path: Path) -> AIClient:
    models_path = tmp_path / "models.yaml"
    models_path.write_text(MINIMAL_MODELS_YAML, encoding="utf-8")
    user_config_path = tmp_path / "user_config.yaml"
    user_config_path.write_text("active_model: pollinations/nova-fast\n", encoding="utf-8")
    # Minimal keystore stub
    ks = MagicMock()
    ks.get = MagicMock(return_value="sk-test-key-001")
    return AIClient(
        models_config_path=models_path,
        user_config_path=user_config_path,
        keystore=ks,
    )


# ------------------------------------------------------------------ #
# Provider resolution                                                   #
# ------------------------------------------------------------------ #

class TestProviderResolution:
    def test_provider_slash_model_parsed(self, client: AIClient) -> None:
        cfg = {"builtin_providers": {"pollinations": {"base_url": "https://gen.pollinations.ai/v1", "api_compat": "openai"}}}
        provider, model_id, provider_cfg = client._resolve_provider("pollinations/nova-fast")
        assert provider == "pollinations"
        assert model_id == "nova-fast"
        assert provider_cfg["api_compat"] == "openai"

    def test_legacy_bare_name_uses_endpoint(self, tmp_path: Path) -> None:
        models_path = tmp_path / "models.yaml"
        models_path.write_text(
            "default: nova-fast\nendpoint:\n  base_url: https://gen.pollinations.ai/v1\n",
            encoding="utf-8",
        )
        user_cfg = tmp_path / "user_config.yaml"
        user_cfg.write_text("active_model: nova-fast\n", encoding="utf-8")
        c = AIClient(models_config_path=models_path, user_config_path=user_cfg)
        provider, model_id, provider_cfg = c._resolve_provider("nova-fast")
        assert provider == "pollinations"
        assert model_id == "nova-fast"
        assert "gen.pollinations.ai" in provider_cfg["base_url"]

    def test_openrouter_passthrough_model_id(self, client: AIClient) -> None:
        provider, model_id, _ = client._resolve_provider(
            "openrouter/openrouter/deepseek/deepseek-r1"
        )
        assert provider == "openrouter"
        assert model_id == "openrouter/deepseek/deepseek-r1"

    def test_unknown_provider_falls_back_to_pollinations(self, client: AIClient) -> None:
        provider, model_id, provider_cfg = client._resolve_provider("unknown-provider/some-model")
        assert "gen.pollinations.ai" in provider_cfg.get("base_url", "")


# ------------------------------------------------------------------ #
# Agent model routing                                                   #
# ------------------------------------------------------------------ #

class TestAgentRouting:
    def test_soul_routes_to_configured_model(self, client: AIClient) -> None:
        assert client.get_model_for_agent("soul") == "pollinations/nova-fast"

    def test_orchestrator_routes_to_gemini(self, client: AIClient) -> None:
        assert client.get_model_for_agent("orchestrator") == "pollinations/gemini-fast"

    def test_unknown_agent_returns_default(self, client: AIClient) -> None:
        model = client.get_model_for_agent("nonexistent_agent")
        assert model == "pollinations/nova-fast"  # falls back to default.primary


# ------------------------------------------------------------------ #
# Allowlist — dynamic from provider catalogue                           #
# ------------------------------------------------------------------ #

class TestDynamicAllowlist:
    def test_pollinations_allowed(self, client: AIClient) -> None:
        client._check_allowlist("https://gen.pollinations.ai/v1")  # no exception

    def test_openrouter_allowed_via_catalogue(self, client: AIClient) -> None:
        client._check_allowlist("https://openrouter.ai/api/v1")  # no exception

    def test_ollama_localhost_allowed(self, client: AIClient) -> None:
        client._check_allowlist("http://127.0.0.1:11434/v1")  # no exception

    def test_unknown_host_raises(self, client: AIClient) -> None:
        with pytest.raises(AllowlistViolation):
            client._check_allowlist("https://evil.example.com/v1")


# ------------------------------------------------------------------ #
# Auth key resolution from keystore                                     #
# ------------------------------------------------------------------ #

class TestAuthKeyResolution:
    def test_keyless_provider_returns_empty(self, client: AIClient) -> None:
        provider_cfg = {"api_key_required": False}
        assert client._get_api_key_for_provider(provider_cfg) == ""

    def test_keystore_queried_for_auth_env(self, client_with_keystore: AIClient) -> None:
        provider_cfg = {"api_key_required": True, "auth_env": "ANTHROPIC_API_KEY"}
        key = client_with_keystore._get_api_key_for_provider(provider_cfg)
        assert key == "sk-test-key-001"
        client_with_keystore._keystore.get.assert_called_with("ANTHROPIC_API_KEY")

    def test_no_keystore_returns_empty(self, client: AIClient) -> None:
        provider_cfg = {"api_key_required": True, "auth_env": "SOME_API_KEY"}
        assert client._get_api_key_for_provider(provider_cfg) == ""


# ------------------------------------------------------------------ #
# _ProfileState cooldown                                                #
# ------------------------------------------------------------------ #

class TestProfileState:
    def test_new_profile_is_available(self) -> None:
        from gurujee.ai.client import _ProfileState
        ps = _ProfileState(key="sk-test")
        assert ps.is_available()

    def test_rate_limit_makes_unavailable(self) -> None:
        import time
        from gurujee.ai.client import _ProfileState
        ps = _ProfileState(key="sk-test")
        ps.apply_rate_limit()
        # Should be in cooldown immediately after applying
        assert not ps.is_available()
        assert ps._rate_limit_count == 1

    def test_billing_disable_makes_unavailable(self) -> None:
        from gurujee.ai.client import _ProfileState
        ps = _ProfileState(key="sk-test")
        ps.apply_billing_disable()
        assert not ps.is_available()
        assert ps._billing_count == 1

    def test_rate_limit_steps_increase(self) -> None:
        import time
        from gurujee.ai.client import _ProfileState
        ps = _ProfileState(key="sk-test")
        # First cooldown = 60s
        ps.apply_rate_limit()
        first_cooldown = ps._cooling_until - time.monotonic()
        assert 55 <= first_cooldown <= 65

        # Override back to available, apply again → 300s step
        ps._cooling_until = 0.0
        ps.apply_rate_limit()
        second_cooldown = ps._cooling_until - time.monotonic()
        assert 295 <= second_cooldown <= 305


# ------------------------------------------------------------------ #
# Provider catalog listing                                              #
# ------------------------------------------------------------------ #

class TestProviderCatalog:
    def test_catalog_includes_builtin_and_custom(self, client: AIClient) -> None:
        catalog = client.list_provider_catalog()
        assert "builtin" in catalog
        assert "custom" in catalog
        assert "pollinations" in catalog["builtin"]
        assert "ollama" in catalog["custom"]

    def test_catalog_model_ids_are_strings(self, client: AIClient) -> None:
        catalog = client.list_provider_catalog()
        for _name, prov in catalog["builtin"].items():
            for model_id in prov.get("models", []):
                assert model_id is None or isinstance(model_id, str)

    def test_catalog_default_included(self, client: AIClient) -> None:
        catalog = client.list_provider_catalog()
        assert "default" in catalog
        assert catalog["default"].get("primary") == "pollinations/nova-fast"


# ------------------------------------------------------------------ #
# stream_chat — provider routing (uses _stream mock)                    #
# ------------------------------------------------------------------ #

class TestStreamChatRouting:
    @pytest.mark.asyncio
    async def test_pollinations_path_calls_stream(self, client: AIClient) -> None:
        tokens = ["hi", " ", "there"]

        async def _fake(*args, **kwargs):
            for t in tokens:
                yield t

        with patch.object(client, "_stream", side_effect=_fake):
            result = []
            async for token in client.stream_chat(
                [{"role": "user", "content": "hello"}],
                model="pollinations/nova-fast",
            ):
                result.append(token)

        assert result == tokens

    @pytest.mark.asyncio
    async def test_model_id_forwarded_to_stream(self, client: AIClient) -> None:
        async def _noop(*args, **kwargs):
            yield "ok"

        with patch.object(client, "_stream", side_effect=_noop) as mock:
            async for _ in client.stream_chat(
                [{"role": "user", "content": "hi"}],
                model="pollinations/gemini-fast",
            ):
                pass
            # 3rd positional arg to _stream is model_id
            assert mock.call_args[0][2] == "gemini-fast"


async def _consume(gen: Any) -> list:
    result = []
    async for item in gen:
        result.append(item)
    return result
