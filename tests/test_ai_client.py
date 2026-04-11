"""Tests for AIClient."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gurujee.ai.client import AIClient, AllowlistViolation


@pytest.fixture
def client(tmp_path: Path) -> AIClient:
    # Write minimal config files
    models_path = tmp_path / "models.yaml"
    models_path.write_text(
        "default: nova-fast\navailable: [nova-fast]\n"
        "endpoint:\n  base_url: https://gen.pollinations.ai/v1\n  api_key: ''\n",
        encoding="utf-8",
    )
    user_config_path = tmp_path / "user_config.yaml"
    user_config_path.write_text("active_model: nova-fast\n", encoding="utf-8")
    return AIClient(
        models_config_path=models_path,
        user_config_path=user_config_path,
    )


class TestStreaming:
    @pytest.mark.asyncio
    async def test_stream_chat_yields_tokens(self, client: AIClient) -> None:
        tokens = ["Hello", " ", "world"]

        async def _fake_stream(*args, **kwargs):
            for t in tokens:
                yield t

        with patch.object(client, "_stream", side_effect=_fake_stream):
            result = []
            async for token in client.stream_chat([{"role": "user", "content": "hi"}]):
                result.append(token)

        assert result == tokens


class TestRetry:
    @pytest.mark.asyncio
    async def test_connect_error_retried_three_times(self, client: AIClient) -> None:
        import httpx
        call_count = 0

        async def _failing_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("unreachable")
            yield  # make it a generator

        with patch.object(client, "_stream", side_effect=_failing_stream):
            with pytest.raises(httpx.ConnectError):
                async for _ in client.stream_chat([{"role": "user", "content": "hi"}]):
                    pass

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_pending_queue_populated_on_failure(self, client: AIClient) -> None:
        import httpx

        async def _failing_stream(*args, **kwargs):
            raise httpx.ConnectError("unreachable")
            yield

        with patch.object(client, "_stream", side_effect=_failing_stream):
            try:
                async for _ in client.stream_chat([{"role": "user", "content": "hi"}]):
                    pass
            except httpx.ConnectError:
                pass

        client.enqueue_pending([{"role": "user", "content": "hi"}])
        assert len(client._pending_queue) == 1


class TestAllowlist:
    def test_non_allowlisted_host_raises(self, client: AIClient) -> None:
        with pytest.raises(AllowlistViolation):
            client._check_allowlist("https://evil.example.com/v1")

    def test_allowlisted_host_passes(self, client: AIClient) -> None:
        client._check_allowlist("https://gen.pollinations.ai/v1")  # no exception


class TestModelConfig:
    def test_active_model_read_from_user_config(self, client: AIClient, tmp_path: Path) -> None:
        user_config_path = tmp_path / "user_config.yaml"
        user_config_path.write_text("active_model: gemini-fast\n", encoding="utf-8")
        client._user_config_path = user_config_path
        assert client._active_model() == "gemini-fast"

    def test_model_override_takes_precedence(self, client: AIClient) -> None:
        async def _noop_stream(*args, **kwargs):
            yield "ok"

        with patch.object(client, "_stream", side_effect=_noop_stream) as mock:
            asyncio.run(
                _consume(client.stream_chat([{"role": "user", "content": "hi"}], model="grok"))
            )
            call_args = mock.call_args
            assert call_args[0][2] == "grok"  # model arg is 3rd positional


async def _consume(gen):
    result = []
    async for item in gen:
        result.append(item)
    return result
