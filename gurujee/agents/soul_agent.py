"""SoulAgent — GURUJEE's identity, personality, and AI conversation handler."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from gurujee.agents.base_agent import BaseAgent, Message, MessageBus, MessageType
from gurujee.config.loader import ConfigLoader

logger = logging.getLogger(__name__)


class SoulAgent(BaseAgent):
    """Manages GURUJEE's identity and drives all AI conversations."""

    def __init__(
        self,
        name: str,
        bus: MessageBus,
        soul_path: Optional[Path] = None,
        models_config_path: Optional[Path] = None,
        user_config_path: Optional[Path] = None,
    ) -> None:
        super().__init__(name, bus)
        data_dir = Path(os.environ.get("GURUJEE_DATA_DIR", "data"))
        config_dir = Path(os.environ.get("GURUJEE_CONFIG_DIR", "config"))

        self._soul_path = Path(soul_path) if soul_path else data_dir / "soul_identity.yaml"
        models_path = Path(models_config_path) if models_config_path else config_dir / "models.yaml"
        user_cfg_path = Path(user_config_path) if user_config_path else data_dir / "user_config.yaml"

        from gurujee.ai.client import AIClient
        self._ai_client = AIClient(
            models_config_path=models_path,
            user_config_path=user_cfg_path,
        )
        self._soul: dict = {}

    # ------------------------------------------------------------------ #
    # Lifecycle                                                             #
    # ------------------------------------------------------------------ #

    async def run(self) -> None:
        self._soul = self._load_soul(self._soul_path)
        logger.info("SoulAgent started: name=%s", self._soul.get("name", "GURUJEE"))
        while True:
            msg = await self._inbox.get()
            if msg.type == MessageType.SHUTDOWN:
                logger.info("SoulAgent: shutdown received")
                break
            await self._dispatch(msg)

    async def handle_message(self, msg: Message) -> None:
        if msg.type == MessageType.CHAT_REQUEST:
            await self._handle_chat_request(msg)

    # ------------------------------------------------------------------ #
    # Chat handling                                                         #
    # ------------------------------------------------------------------ #

    async def _handle_chat_request(self, msg: Message) -> None:
        user_text: str = msg.payload.get("text", "")

        # Request memory context
        await self.send(
            "memory",
            MessageType.MEMORY_CONTEXT_REQUEST,
            {"query_text": user_text},
            reply_to=msg.id,
        )

        # Await memory response (2 second timeout)
        recent_turns: list[dict] = []
        long_term_facts: list[dict] = []
        try:
            resp = await asyncio.wait_for(self._await_memory_response(), timeout=2.0)
            recent_turns = resp.payload.get("recent_turns", [])
            long_term_facts = resp.payload.get("long_term_facts", [])
        except asyncio.TimeoutError:
            logger.warning("SoulAgent: memory context timeout, proceeding without context")

        # Build prompt and stream response
        user_name: str = str(self._soul.get("user_name") or "friend")
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        system_prompt = self._build_system_prompt(user_name, date_str, recent_turns, long_term_facts)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(recent_turns)
        messages.append({"role": "user", "content": user_text})

        full_text = ""
        is_interrupted = False
        try:
            async for token in self._ai_client.stream_chat(messages):
                full_text += token
                await self.send(
                    "broadcast",
                    MessageType.CHAT_CHUNK,
                    {"token": token, "request_id": msg.id},
                )
        except Exception as exc:
            logger.error("SoulAgent: stream interrupted: %s", exc)
            is_interrupted = True
            await self.send(
                "broadcast",
                MessageType.CHAT_ERROR,
                {"error": str(exc), "queued": True, "request_id": msg.id},
            )
            self._ai_client.enqueue_pending(messages)

        # Emit completion (even on interruption — partial text is still stored)
        await self.send(
            "broadcast",
            MessageType.CHAT_RESPONSE_COMPLETE,
            {
                "full_text": full_text + (" [interrupted]" if is_interrupted else ""),
                "is_interrupted": is_interrupted,
                "request_id": msg.id,
            },
        )

        # Store the exchange in memory
        if full_text:
            await self.send(
                "memory",
                MessageType.MEMORY_STORE,
                {
                    "content": f"User: {user_text}\nGURUJEE: {full_text}",
                    "tags": "conversation",
                    "category": "fact",
                    "source": "conversation",
                },
            )

    async def _await_memory_response(self) -> Message:
        while True:
            msg = await self._inbox.get()
            if msg.type == MessageType.MEMORY_CONTEXT_RESPONSE:
                return msg
            # Re-queue other messages for later processing
            await self._inbox.put(msg)
            await asyncio.sleep(0)

    # ------------------------------------------------------------------ #
    # Soul loading and prompt building                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _load_soul(path: Path) -> dict:
        return ConfigLoader.load_soul_identity(path)

    def _build_system_prompt(
        self,
        user_name: str,
        date: str,
        recent_turns: list[dict],
        long_term_facts: list[dict],
    ) -> str:
        soul = self._soul
        template: str = soul.get(
            "system_prompt_template",
            "You are {name}. User: {user_name}. Date: {date}.",
        )
        traits = soul.get("personality_traits", [])
        traits_joined = ", ".join(str(t) for t in traits)

        prompt = template.format(
            name=soul.get("name", "GURUJEE"),
            tagline=soul.get("tagline", ""),
            user_name=user_name,
            date=date,
            traits_joined=traits_joined,
        )

        if long_term_facts:
            facts_text = "\n".join(f"- {f['content']}" for f in long_term_facts)
            prompt += f"\n\nRelevant memories:\n{facts_text}"

        return prompt
