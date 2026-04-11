"""Shared pytest fixtures for GURUJEE test suite."""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from gurujee.agents.base_agent import Message, MessageBus, MessageType


# ------------------------------------------------------------------ #
# Message bus fixture                                                   #
# ------------------------------------------------------------------ #

class MockMessageBus(MessageBus):
    """MessageBus that records all sent messages for assertion."""

    def __init__(self) -> None:
        super().__init__()
        self.sent_messages: list[Message] = []

    async def send(self, msg: Message) -> None:
        self.sent_messages.append(msg)
        await super().send(msg)

    def messages_of_type(self, msg_type: MessageType) -> list[Message]:
        return [m for m in self.sent_messages if m.type == msg_type]


@pytest.fixture
def mock_bus() -> MockMessageBus:
    return MockMessageBus()


# ------------------------------------------------------------------ #
# Temporary data / config directories                                   #
# ------------------------------------------------------------------ #

REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temp directory that mirrors the runtime data/config layout."""
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    data_dir.mkdir()
    config_dir.mkdir()

    # Copy config templates
    for name in ("models.yaml", "agents.yaml", "voice.yaml"):
        src = REPO_ROOT / "config" / name
        if src.exists():
            shutil.copy2(src, config_dir / name)

    # Set env vars so ConfigLoader resolves to temp dirs
    import os
    os.environ["GURUJEE_DATA_DIR"] = str(data_dir)
    os.environ["GURUJEE_CONFIG_DIR"] = str(config_dir)

    yield tmp_path

    # Cleanup env
    os.environ.pop("GURUJEE_DATA_DIR", None)
    os.environ.pop("GURUJEE_CONFIG_DIR", None)


# ------------------------------------------------------------------ #
# Soul identity fixture                                                 #
# ------------------------------------------------------------------ #

@pytest.fixture
def fake_soul_yaml(tmp_path: Path) -> Path:
    """Copy agents/soul_identity.yaml template to a temp path."""
    src = REPO_ROOT / "agents" / "soul_identity.yaml"
    dest = tmp_path / "soul_identity.yaml"
    if src.exists():
        shutil.copy2(src, dest)
    else:
        dest.write_text(
            "name: GURUJEE\ntagline: Test companion\nuser_name: null\n"
            "personality_traits: [wise]\nlanguage_style: formal\n"
            "system_prompt_template: 'You are {name}. User: {user_name}. Date: {date}.'\n"
            "voice_id: null\ncreated_at: '2026-04-11T00:00:00Z'\nversion: 1\n",
            encoding="utf-8",
        )
    return dest


# ------------------------------------------------------------------ #
# User config fixture                                                   #
# ------------------------------------------------------------------ #

@pytest.fixture
def fake_user_config(tmp_path: Path) -> Path:
    """Write a minimal data/user_config.yaml to a temp path."""
    cfg_path = tmp_path / "user_config.yaml"
    cfg_path.write_text(
        "active_model: nova-fast\nactive_voice_id: null\ntui_theme: default\n",
        encoding="utf-8",
    )
    return cfg_path


# ------------------------------------------------------------------ #
# Keystore fixture                                                      #
# ------------------------------------------------------------------ #

TEST_PIN = "1234"


@pytest.fixture
def fake_keystore(tmp_path: Path):
    """Unlocked Keystore backed by tmp_path with PIN '1234'."""
    from gurujee.keystore.keystore import Keystore

    ks_path = tmp_path / "test.keystore"
    salt_path = tmp_path / ".device_salt"
    import os
    salt_path.write_bytes(os.urandom(16))

    ks = Keystore(ks_path, pin=TEST_PIN)

    # Patch _get_salt to use the written file
    import types

    def _patched_get_salt(self: Keystore) -> bytes:
        return salt_path.read_bytes()

    ks._get_salt = types.MethodType(_patched_get_salt, ks)  # type: ignore[method-assign]
    ks.unlock()
    return ks


# ------------------------------------------------------------------ #
# OpenAI streaming mock                                                 #
# ------------------------------------------------------------------ #

def _make_sse_body(tokens: list[str]) -> bytes:
    """Build a minimal SSE body that the openai SDK can parse."""
    lines: list[str] = []
    for i, token in enumerate(tokens):
        chunk = (
            '{"id":"c1","object":"chat.completion.chunk","choices":[{"index":0,"delta":'
            f'{{"content":{token!r}}},"finish_reason":null}}]}}'
        )
        lines.append(f"data: {chunk}\n\n")
    lines.append("data: [DONE]\n\n")
    return "".join(lines).encode("utf-8")


@pytest.fixture
def fake_openai_stream(monkeypatch):
    """Patch AsyncOpenAI so stream_chat yields three tokens: 'Hello', ' ', 'world'."""
    tokens = ["Hello", " ", "world"]

    async def _mock_stream_chat(self, messages, model=None):  # noqa: ANN001
        for token in tokens:
            yield token

    from gurujee.ai import client as ai_client_mod
    monkeypatch.setattr(ai_client_mod.AIClient, "stream_chat", _mock_stream_chat)
    return tokens
