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
        turns = list(self._turns)[-n:]
        return [{"role": t.role, "content": t.content} for t in turns]

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
