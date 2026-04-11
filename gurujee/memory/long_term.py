"""Long-term SQLite memory store with hybrid recency + keyword retrieval."""
from __future__ import annotations

import logging
import shutil
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryRecord:
    id: int
    content: str
    tags: str
    category: str
    importance: float
    created_at: str
    source: str


class LongTermMemory:
    """SQLite-backed long-term memory (WAL mode, single writer)."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)

    def init_db(self) -> None:
        """Create schema and enable WAL. Idempotent."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    content   TEXT    NOT NULL,
                    tags      TEXT    NOT NULL DEFAULT '',
                    category  TEXT    NOT NULL,
                    importance REAL   NOT NULL DEFAULT 0.5,
                    created_at TEXT  NOT NULL,
                    source    TEXT    NOT NULL DEFAULT 'conversation'
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags)"
            )

    def insert(
        self,
        content: str,
        tags: str,
        category: str,
        importance: float = 0.5,
        source: str = "conversation",
    ) -> MemoryRecord:
        """Insert a new memory and return the created record."""
        if source == "explicit":
            importance = 1.0
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO memories (content, tags, category, importance, created_at, source)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (content, tags, category, importance, created_at, source),
            )
            return MemoryRecord(
                id=cursor.lastrowid,
                content=content,
                tags=tags,
                category=category,
                importance=importance,
                created_at=created_at,
                source=source,
            )

    def search(self, query_text: str) -> list[MemoryRecord]:
        """Return up to 5 records matching keyword(s) in *query_text*."""
        keywords = [w.strip() for w in query_text.split() if w.strip()]
        if not keywords:
            return []

        # Build WHERE clause: at least one keyword matches tags or content
        conditions = " OR ".join(
            "(tags LIKE ? OR content LIKE ?)" for _ in keywords
        )
        params = []
        for kw in keywords:
            like = f"%{kw}%"
            params.extend([like, like])

        sql = f"""
            SELECT id, content, tags, category, importance, created_at, source
            FROM memories
            WHERE {conditions}
            ORDER BY (importance * 2 + 1.0 / (julianday('now') - julianday(created_at) + 1)) DESC
            LIMIT 5
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            MemoryRecord(
                id=r[0], content=r[1], tags=r[2], category=r[3],
                importance=r[4], created_at=r[5], source=r[6],
            )
            for r in rows
        ]

    def backup_weekly(self, backups_dir: Path) -> None:
        """Copy the database to backups_dir if no backup exists from the past 7 days."""
        backups_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        # Check whether any backup file is dated within the last 7 days.
        for existing in backups_dir.glob("memory_????????.db"):
            try:
                stamp = datetime.strptime(existing.stem[7:], "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
                if (now - stamp).days < 7:
                    return  # recent backup exists
            except ValueError:
                pass
        dest = backups_dir / f"memory_{now.strftime('%Y%m%d')}.db"
        try:
            shutil.copy2(self._db_path, dest)
            logger.info("Memory backup written to %s", dest)
        except OSError as exc:
            logger.error("Memory backup failed: %s", exc)

    def handle_corrupt(self, path: Path) -> None:
        """Rename corrupt DB and create a fresh empty one."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        corrupt_path = path.with_suffix(f".corrupt.{ts}")
        try:
            path.rename(corrupt_path)
            logger.warning("Corrupt database renamed to %s", corrupt_path)
        except OSError as exc:
            logger.error("Could not rename corrupt database: %s", exc)
        # Re-initialise with empty schema
        self.init_db()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager that yields a Connection, commits/rolls back, then closes it."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            with conn:        # commits on clean exit, rolls back on exception
                yield conn
        finally:
            conn.close()      # always release the file descriptor
