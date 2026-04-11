"""MemoryAgent — manages short-term and long-term memory."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from gurujee.agents.base_agent import BaseAgent, Message, MessageBus, MessageType
from gurujee.memory.long_term import LongTermMemory
from gurujee.memory.short_term import ShortTermMemory

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    """Owns the memory stores and responds to context queries and store requests."""

    def __init__(
        self,
        name: str,
        bus: MessageBus,
        data_dir: Optional[Path] = None,
    ) -> None:
        super().__init__(name, bus)
        self._data_dir = Path(data_dir) if data_dir else Path(
            os.environ.get("GURUJEE_DATA_DIR", "data")
        )
        self._db_path = self._data_dir / "memory.db"
        self._session_path = self._data_dir / "session_context.yaml"
        self._backups_dir = self._data_dir / "backups"

        self._long_term = LongTermMemory(self._db_path)
        self._short_term = ShortTermMemory()

    async def _setup(self) -> None:
        """Initialise DB and load previous session context. Called at startup."""
        try:
            self._long_term.init_db()
        except Exception as exc:
            logger.error("MemoryAgent: DB init failed: %s — attempting recovery", exc)
            self._long_term.handle_corrupt(self._db_path)
            await self.broadcast(
                MessageType.AGENT_STATUS_UPDATE,
                {"agent": self.name, "status": "DEGRADED", "reason": "db_recovered"},
            )

        if self._session_path.exists():
            try:
                self._short_term.load(self._session_path)
                logger.info("MemoryAgent: restored %d turns from session", len(self._short_term.get_recent()))
            except Exception as exc:
                logger.warning("MemoryAgent: could not restore session context: %s", exc)

        asyncio.create_task(self._schedule_backup())

    async def run(self) -> None:
        await self._setup()
        logger.info("MemoryAgent started")
        while True:
            msg = await self._inbox.get()
            if msg.type == MessageType.SHUTDOWN:
                await self._on_shutdown()
                break
            await self._dispatch(msg)

    async def handle_message(self, msg: Message) -> None:
        if msg.type == MessageType.MEMORY_CONTEXT_REQUEST:
            await self._handle_context_request(msg)
        elif msg.type == MessageType.MEMORY_STORE:
            await self._handle_store(msg)

    # ------------------------------------------------------------------ #
    # Handlers                                                              #
    # ------------------------------------------------------------------ #

    async def _handle_context_request(self, msg: Message) -> None:
        query: str = msg.payload.get("query_text", "")
        recent = self._short_term.get_recent()
        try:
            facts = self._long_term.search(query)
            facts_dicts = [
                {"content": r.content, "tags": r.tags, "importance": r.importance}
                for r in facts
            ]
        except Exception as exc:
            logger.error("MemoryAgent: search failed: %s", exc)
            facts_dicts = []

        await self.send(
            msg.from_agent,
            MessageType.MEMORY_CONTEXT_RESPONSE,
            {"recent_turns": recent, "long_term_facts": facts_dicts},
            reply_to=msg.id,
        )

    async def _handle_store(self, msg: Message) -> None:
        content: str = msg.payload.get("content", "")
        tags: str = msg.payload.get("tags", "")
        category: str = msg.payload.get("category", "fact")
        source: str = msg.payload.get("source", "conversation")
        role: str = msg.payload.get("role", "")

        try:
            self._long_term.insert(
                content=content, tags=tags, category=category, source=source
            )
        except Exception as exc:
            logger.error("MemoryAgent: insert failed: %s", exc)

        if role:
            self._short_term.add_turn(role, content)

        await self.send(
            msg.from_agent,
            MessageType.MEMORY_STORED,
            {"status": "ok"},
            reply_to=msg.id,
        )

    async def _on_shutdown(self) -> None:
        try:
            self._short_term.serialize(self._session_path)
            logger.info("MemoryAgent: session context saved")
        except Exception as exc:
            logger.error("MemoryAgent: could not save session: %s", exc)

    async def _schedule_backup(self) -> None:
        """Schedule weekly backup via asyncio (runs once at startup check)."""
        try:
            self._long_term.backup_weekly(self._backups_dir)
        except Exception as exc:
            logger.error("MemoryAgent: backup error: %s", exc)
