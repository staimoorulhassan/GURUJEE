"""Short-term in-RAM conversation buffer."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ConversationTurn:
    role: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ShortTermMemory:
    """Holds the last 10 conversation turns in a deque."""

    def __init__(self, maxlen: int = 10) -> None:
        self._turns: deque[ConversationTurn] = deque(maxlen=maxlen)

    def add_turn(self, role: str, content: str) -> None:
        self._turns.append(ConversationTurn(role=role, content=content))

    def get_recent(self, n: int = 10) -> list[dict[str, str]]:
        """Return the last *n* turns as OpenAI message dicts."""
        turns = list(self._turns)[-n:]
        return [{"role": t.role, "content": t.content} for t in turns]

    def to_messages(self) -> list[dict[str, str]]:
        """Return all buffered turns as OpenAI-compatible message list."""
        return self.get_recent(n=len(self._turns))

    def add(self, role: str, content: str) -> None:
        """Alias for add_turn() — matches tasks.md API contract."""
        self.add_turn(role, content)

    def summarize_to_long_term(self, long_term_memory: object) -> None:
        """Summarise the current short-term buffer into long-term memory.

        Called by MemoryAgent when context approaches the model's limit.
        Creates a single summary MemoryRecord from the buffered turns.
        Clears the buffer after persisting.
        """
        if not self._turns:
            return
        summary_lines = [f"{t.role}: {t.content}" for t in self._turns]
        summary = "Session summary: " + " | ".join(summary_lines[:5])
        tags = "session,summary"
        if hasattr(long_term_memory, "store_memory"):
            long_term_memory.store_memory(  # type: ignore[union-attr]
                content=summary,
                tags=tags,
                category="fact",
                importance=0.3,
                source="conversation",
            )
        self._turns.clear()

    def deserialize(self, path: Path) -> None:
        """Alias for load() — matches tasks.md API contract."""
        self.load(path)

    def serialize(self, path: Path) -> None:
        data = [
            {
                "role": t.role,
                "content": t.content,
                "timestamp": t.timestamp.isoformat(),
            }
            for t in self._turns
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump({"turns": data}, fh, allow_unicode=True)

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        for turn in data.get("turns", []):
            self._turns.append(
                ConversationTurn(
                    role=turn["role"],
                    content=turn["content"],
                    timestamp=datetime.fromisoformat(turn["timestamp"]),
                )
            )
