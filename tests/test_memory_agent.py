"""Tests for MemoryAgent, ShortTermMemory, and LongTermMemory."""
from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

import pytest

from gurujee.agents.base_agent import MessageType, Message
from tests.conftest import MockMessageBus


class TestLongTermMemory:
    def test_insert_writes_row(self, tmp_path: Path) -> None:
        from gurujee.memory.long_term import LongTermMemory

        db = LongTermMemory(tmp_path / "memory.db")
        db.init_db()
        record = db.insert(
            content="User's daughter is named Fatima",
            tags="daughter,family,person",
            category="person",
            importance=0.9,
        )
        assert record.id is not None
        assert record.content == "User's daughter is named Fatima"

    def test_search_returns_matching_record(self, tmp_path: Path) -> None:
        from gurujee.memory.long_term import LongTermMemory

        db = LongTermMemory(tmp_path / "memory.db")
        db.init_db()
        db.insert("Daughter is Fatima", tags="daughter,person", category="person", importance=0.9)
        results = db.search("daughter")
        assert len(results) >= 1
        assert any("Fatima" in r.content for r in results)

    def test_explicit_source_sets_importance_1(self, tmp_path: Path) -> None:
        from gurujee.memory.long_term import LongTermMemory

        db = LongTermMemory(tmp_path / "memory.db")
        db.init_db()
        record = db.insert("Remember this", tags="test", category="fact", source="explicit")
        assert record.importance == 1.0

    def test_backup_weekly_creates_backup_file(self, tmp_path: Path) -> None:
        from gurujee.memory.long_term import LongTermMemory

        db = LongTermMemory(tmp_path / "memory.db")
        db.init_db()
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir()
        db.backup_weekly(backups_dir)
        backups = list(backups_dir.glob("memory_*.db"))
        assert len(backups) == 1

    def test_corrupt_db_creates_fresh_db(self, tmp_path: Path) -> None:
        from gurujee.memory.long_term import LongTermMemory

        db_path = tmp_path / "memory.db"
        db_path.write_bytes(b"corrupt data not sqlite")
        db = LongTermMemory(db_path)
        db.handle_corrupt(db_path)
        # Should create a fresh database
        db2 = LongTermMemory(db_path)
        db2.init_db()
        results = db2.search("test")
        assert results == []

    def test_wal_mode_enabled(self, tmp_path: Path) -> None:
        from gurujee.memory.long_term import LongTermMemory

        db = LongTermMemory(tmp_path / "memory.db")
        db.init_db()
        conn = sqlite3.connect(str(tmp_path / "memory.db"))
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"


class TestShortTermMemory:
    def test_deque_drops_oldest_at_11(self, tmp_path: Path) -> None:
        from gurujee.memory.short_term import ShortTermMemory

        stm = ShortTermMemory()
        for i in range(11):
            stm.add_turn("user", f"message {i}")
        turns = stm.get_recent()
        assert len(turns) == 10
        # First message (i=0) should be gone
        assert not any("message 0" in t["content"] for t in turns)

    def test_get_recent_returns_correct_format(self, tmp_path: Path) -> None:
        from gurujee.memory.short_term import ShortTermMemory

        stm = ShortTermMemory()
        stm.add_turn("user", "Hello")
        stm.add_turn("assistant", "Hi there")
        turns = stm.get_recent()
        assert turns[0] == {"role": "user", "content": "Hello"}
        assert turns[1] == {"role": "assistant", "content": "Hi there"}

    def test_serialize_and_load(self, tmp_path: Path) -> None:
        from gurujee.memory.short_term import ShortTermMemory

        stm = ShortTermMemory()
        stm.add_turn("user", "Persist this")
        path = tmp_path / "session.yaml"
        stm.serialize(path)

        stm2 = ShortTermMemory()
        stm2.load(path)
        turns = stm2.get_recent()
        assert len(turns) == 1
        assert turns[0]["content"] == "Persist this"

    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        from gurujee.memory.short_term import ShortTermMemory

        stm = ShortTermMemory()
        stm.load(tmp_path / "nonexistent.yaml")
        assert stm.get_recent() == []


class TestMemoryAgent:
    @pytest.mark.asyncio
    async def test_memory_context_request_returns_response(self, tmp_path: Path) -> None:
        from gurujee.agents.memory_agent import MemoryAgent

        bus = MockMessageBus()
        agent = MemoryAgent(name="memory", bus=bus, data_dir=tmp_path)
        await agent._setup()

        # Insert a memory
        agent._long_term.insert(
            "Daughter is Fatima", tags="daughter,person", category="person", importance=0.9
        )

        msg = Message(
            type=MessageType.MEMORY_CONTEXT_REQUEST,
            from_agent="soul",
            to_agent="memory",
            payload={"query_text": "daughter"},
        )
        await agent._inbox.put(msg)

        task = asyncio.create_task(agent.run())
        await asyncio.sleep(0.1)
        task.cancel()

        responses = bus.messages_of_type(MessageType.MEMORY_CONTEXT_RESPONSE)
        assert len(responses) == 1
        facts = responses[0].payload.get("long_term_facts", [])
        assert any("Fatima" in f["content"] for f in facts)

    @pytest.mark.asyncio
    async def test_memory_store_writes_to_db(self, tmp_path: Path) -> None:
        from gurujee.agents.memory_agent import MemoryAgent

        bus = MockMessageBus()
        agent = MemoryAgent(name="memory", bus=bus, data_dir=tmp_path)
        await agent._setup()

        msg = Message(
            type=MessageType.MEMORY_STORE,
            from_agent="soul",
            to_agent="memory",
            payload={
                "content": "User likes Python",
                "tags": "preference,python",
                "category": "preference",
                "source": "explicit",
            },
        )
        await agent._inbox.put(msg)
        task = asyncio.create_task(agent.run())
        await asyncio.sleep(0.1)
        task.cancel()

        results = agent._long_term.search("python")
        assert any("Python" in r.content for r in results)
