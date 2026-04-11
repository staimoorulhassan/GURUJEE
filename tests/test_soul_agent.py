"""Tests for SoulAgent — TDD: must fail before soul_agent.py is implemented."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from gurujee.agents.base_agent import MessageType
from tests.conftest import MockMessageBus


@pytest.fixture
def bus() -> MockMessageBus:
    return MockMessageBus()


@pytest.fixture
def soul_agent(bus, fake_soul_yaml, fake_user_config, tmp_path):
    from gurujee.agents.soul_agent import SoulAgent
    return SoulAgent(
        name="soul",
        bus=bus,
        soul_path=fake_soul_yaml,
        models_config_path=tmp_path / "config" / "models.yaml",
        user_config_path=fake_user_config,
    )


class TestSystemPrompt:
    def test_system_prompt_contains_name(self, soul_agent):
        prompt = soul_agent._build_system_prompt("Ali", "2026-04-11", [], [])
        assert "GURUJEE" in prompt

    def test_system_prompt_contains_date(self, soul_agent):
        prompt = soul_agent._build_system_prompt("Ali", "2026-04-11", [], [])
        assert "2026-04-11" in prompt

    def test_system_prompt_contains_user_name(self, soul_agent):
        prompt = soul_agent._build_system_prompt("Ali", "2026-04-11", [], [])
        assert "Ali" in prompt


class TestChatRequest:
    @pytest.mark.asyncio
    async def test_chat_request_triggers_memory_context_request(self, soul_agent, bus):
        """CHAT_REQUEST must cause a MEMORY_CONTEXT_REQUEST to be sent."""
        from gurujee.agents.base_agent import Message

        # Provide a MEMORY_CONTEXT_RESPONSE so soul doesn't hang waiting
        async def _inject_response() -> None:
            await asyncio.sleep(0.05)
            resp = Message(
                type=MessageType.MEMORY_CONTEXT_RESPONSE,
                from_agent="memory",
                to_agent="soul",
                payload={"recent_turns": [], "long_term_facts": []},
            )
            await soul_agent._inbox.put(resp)

        async def _empty_stream(*a, **kw):
            return
            yield  # noqa: unreachable — makes this an async generator

        with patch.object(soul_agent._ai_client, "stream_chat", new=_empty_stream):
            asyncio.create_task(_inject_response())
            msg = Message(
                type=MessageType.CHAT_REQUEST,
                from_agent="tui",
                to_agent="soul",
                payload={"text": "Hello"},
            )
            await soul_agent._inbox.put(msg)
            # Run one iteration of the run loop
            task = asyncio.create_task(soul_agent.run())
            await asyncio.sleep(0.3)
            task.cancel()

        assert any(
            m.type == MessageType.MEMORY_CONTEXT_REQUEST for m in bus.sent_messages
        )

    @pytest.mark.asyncio
    async def test_chat_chunk_emitted_per_token(self, soul_agent, bus):
        """Each token from stream_chat must produce a CHAT_CHUNK message."""
        from gurujee.agents.base_agent import Message

        tokens = ["Hello", " ", "world"]

        async def _inject_memory() -> None:
            await asyncio.sleep(0.02)
            resp = Message(
                type=MessageType.MEMORY_CONTEXT_RESPONSE,
                from_agent="memory",
                to_agent="soul",
                payload={"recent_turns": [], "long_term_facts": []},
            )
            await soul_agent._inbox.put(resp)

        async def _token_stream(*a, **kw):
            for t in tokens:
                yield t

        with patch.object(soul_agent._ai_client, "stream_chat", new=_token_stream):
            asyncio.create_task(_inject_memory())
            msg = Message(
                type=MessageType.CHAT_REQUEST,
                from_agent="tui",
                to_agent="soul",
                payload={"text": "Hi"},
            )
            await soul_agent._inbox.put(msg)
            task = asyncio.create_task(soul_agent.run())
            await asyncio.sleep(0.4)
            task.cancel()

        chunks = bus.messages_of_type(MessageType.CHAT_CHUNK)
        assert len(chunks) == len(tokens)

    @pytest.mark.asyncio
    async def test_chat_response_complete_emitted_after_stream(self, soul_agent, bus):
        from gurujee.agents.base_agent import Message

        async def _inject_memory() -> None:
            await asyncio.sleep(0.02)
            resp = Message(
                type=MessageType.MEMORY_CONTEXT_RESPONSE,
                from_agent="memory",
                to_agent="soul",
                payload={"recent_turns": [], "long_term_facts": []},
            )
            await soul_agent._inbox.put(resp)

        async def _single_token_stream(*a, **kw):
            yield "Hi"

        with patch.object(soul_agent._ai_client, "stream_chat", new=_single_token_stream):
            asyncio.create_task(_inject_memory())
            msg = Message(
                type=MessageType.CHAT_REQUEST,
                from_agent="tui",
                to_agent="soul",
                payload={"text": "Hey"},
            )
            await soul_agent._inbox.put(msg)
            task = asyncio.create_task(soul_agent.run())
            await asyncio.sleep(0.4)
            task.cancel()

        complete = bus.messages_of_type(MessageType.CHAT_RESPONSE_COMPLETE)
        assert len(complete) == 1
        assert complete[0].payload.get("full_text") == "Hi"

    @pytest.mark.asyncio
    async def test_chat_error_emitted_on_ai_failure(self, soul_agent, bus):
        from gurujee.agents.base_agent import Message

        async def _inject_memory() -> None:
            await asyncio.sleep(0.02)
            resp = Message(
                type=MessageType.MEMORY_CONTEXT_RESPONSE,
                from_agent="memory",
                to_agent="soul",
                payload={"recent_turns": [], "long_term_facts": []},
            )
            await soul_agent._inbox.put(resp)

        async def _failing_stream(*args, **kwargs):
            raise RuntimeError("AI endpoint down")
            yield  # make it an async generator

        with patch.object(soul_agent._ai_client, "stream_chat", new=_failing_stream):
            asyncio.create_task(_inject_memory())
            msg = Message(
                type=MessageType.CHAT_REQUEST,
                from_agent="tui",
                to_agent="soul",
                payload={"text": "Hey"},
            )
            await soul_agent._inbox.put(msg)
            task = asyncio.create_task(soul_agent.run())
            await asyncio.sleep(0.4)
            task.cancel()

        errors = bus.messages_of_type(MessageType.CHAT_ERROR)
        assert len(errors) >= 1


async def _aiter(items):
    for item in items:
        yield item
