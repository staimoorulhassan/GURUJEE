"""AsyncOpenAI wrapper with tenacity retry, streaming, network allowlist, and pending queue."""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from urllib.parse import urlparse

import httpx
from openai import AsyncOpenAI
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from gurujee.config.loader import ConfigLoader

logger = logging.getLogger(__name__)

_ALLOWED_HOSTS = frozenset({"gen.pollinations.ai", "api.elevenlabs.io"})


class AllowlistViolation(Exception):
    """Raised when an outbound host is not in the network allowlist."""


class AIClient:
    """Streams AI completions via the Pollinations endpoint."""

    def __init__(
        self,
        models_config_path: Path,
        user_config_path: Path,
    ) -> None:
        self._models_config_path = Path(models_config_path)
        self._user_config_path = Path(user_config_path)
        self._pending_queue: deque[dict[str, Any]] = deque()
        self._client: Optional[AsyncOpenAI] = None

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Yield response tokens as they arrive.

        Uses the model from data/user_config.yaml unless *model* is explicitly passed.
        Retries on connection/timeout errors up to 3 times.
        On exhausted retries, raises the last exception (caller adds to pending queue).
        """
        resolved_model = model or self._active_model()
        client = self._get_client()

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
            reraise=True,
        ):
            with attempt:
                async for token in self._stream(client, messages, resolved_model):
                    yield token

    async def retry_pending(self) -> AsyncGenerator[tuple[dict[str, Any], str], None]:
        """Re-send queued messages one at a time.

        Yields (original_request_payload, token) pairs for each recovered message.
        Removes the message from the queue on success.
        """
        while self._pending_queue:
            item = self._pending_queue[0]
            try:
                tokens: list[str] = []
                async for token in self.stream_chat(
                    item["messages"], item.get("model")
                ):
                    tokens.append(token)
                    yield item, token
                self._pending_queue.popleft()
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
                break  # network still down — leave in queue

    def enqueue_pending(self, messages: list[dict[str, str]], model: Optional[str] = None) -> None:
        """Add a failed request to the retry queue."""
        self._pending_queue.append({"messages": messages, "model": model})

    # ------------------------------------------------------------------ #
    # Internals                                                             #
    # ------------------------------------------------------------------ #

    def _active_model(self) -> str:
        user_cfg = ConfigLoader.load_user_config(self._user_config_path)
        model_from_user = user_cfg.get("active_model")
        if model_from_user:
            return str(model_from_user)
        models_cfg = ConfigLoader.load_yaml(self._models_config_path)
        return str(models_cfg.get("default", "nova-fast"))

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            models_cfg = ConfigLoader.load_yaml(self._models_config_path)
            endpoint = models_cfg.get("endpoint", {})
            base_url: str = endpoint.get("base_url", "https://gen.pollinations.ai/v1")
            self._check_allowlist(base_url)
            self._client = AsyncOpenAI(base_url=base_url, api_key="")
        return self._client

    @staticmethod
    def _check_allowlist(url: str) -> None:
        host = urlparse(url).hostname or ""
        if host not in _ALLOWED_HOSTS:
            raise AllowlistViolation(
                f"Host '{host}' is not in the GURUJEE network allowlist. "
                f"Allowed: {sorted(_ALLOWED_HOSTS)}"
            )

    @staticmethod
    async def _stream(
        client: AsyncOpenAI,
        messages: list[dict[str, str]],
        model: str,
    ) -> AsyncGenerator[str, None]:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
