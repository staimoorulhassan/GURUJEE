"""Tests for UserAgent — serves user profile data."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from tests.conftest import MockMessageBus


class TestUserAgentInit:
    def test_returns_none_when_no_soul_file(self, tmp_path: Path) -> None:
        from gurujee.agents.user_agent import UserAgent

        bus = MockMessageBus()
        agent = UserAgent(name="user_agent", bus=bus, data_dir=tmp_path)
        result = agent._load_user_name()
        assert result is None

    def test_loads_user_name_from_soul_identity(self, tmp_path: Path) -> None:
        from gurujee.agents.user_agent import UserAgent

        soul_path = tmp_path / "soul_identity.yaml"
        soul_path.write_text(
            yaml.safe_dump({"name": "GURUJEE", "user_name": "Taimoor"}),
            encoding="utf-8",
        )
        bus = MockMessageBus()
        agent = UserAgent(name="user_agent", bus=bus, data_dir=tmp_path)
        result = agent._load_user_name()
        assert result == "Taimoor"

    def test_returns_none_when_user_name_key_absent(self, tmp_path: Path) -> None:
        from gurujee.agents.user_agent import UserAgent

        soul_path = tmp_path / "soul_identity.yaml"
        soul_path.write_text(yaml.safe_dump({"name": "GURUJEE"}), encoding="utf-8")

        bus = MockMessageBus()
        agent = UserAgent(name="user_agent", bus=bus, data_dir=tmp_path)
        assert agent._load_user_name() is None

    def test_handles_corrupt_yaml_gracefully(self, tmp_path: Path) -> None:
        from gurujee.agents.user_agent import UserAgent

        soul_path = tmp_path / "soul_identity.yaml"
        soul_path.write_text("<<<invalid yaml>>>", encoding="utf-8")

        bus = MockMessageBus()
        agent = UserAgent(name="user_agent", bus=bus, data_dir=tmp_path)
        # Should not raise; returns None
        assert agent._load_user_name() is None


class TestUserAgentProfileRequest:
    @pytest.mark.asyncio
    async def test_responds_to_user_profile_request(self, tmp_path: Path) -> None:
        from gurujee.agents.user_agent import UserAgent
        from gurujee.agents.base_agent import Message, MessageType

        soul_path = tmp_path / "soul_identity.yaml"
        soul_path.write_text(yaml.safe_dump({"user_name": "Ali"}), encoding="utf-8")

        bus = MockMessageBus()
        bus.register_agent("user_agent", asyncio.Queue())
        bus.register_agent("soul", asyncio.Queue())

        agent = UserAgent(name="user_agent", bus=bus, data_dir=tmp_path)
        agent._user_name = "Ali"

        request = Message(
            type=MessageType.USER_PROFILE_REQUEST,
            from_agent="soul",
            to_agent="user_agent",
            payload={},
        )
        await agent.handle_message(request)

        # The response should be in soul's inbox
        sent = bus.messages_of_type(MessageType.USER_PROFILE_RESPONSE)
        assert len(sent) == 1
        assert sent[0].payload["user_name"] == "Ali"

    @pytest.mark.asyncio
    async def test_run_shuts_down_on_shutdown(self, tmp_path: Path) -> None:
        from gurujee.agents.user_agent import UserAgent
        from gurujee.agents.base_agent import Message, MessageType

        bus = MockMessageBus()
        bus.register_agent("user_agent", asyncio.Queue())
        agent = UserAgent(name="user_agent", bus=bus, data_dir=tmp_path)

        async def _shutdown() -> None:
            await asyncio.sleep(0.01)
            await agent._inbox.put(
                Message(type=MessageType.SHUTDOWN, from_agent="gateway", to_agent="user_agent", payload={})
            )

        asyncio.create_task(_shutdown())
        await asyncio.wait_for(agent.run(), timeout=2)
