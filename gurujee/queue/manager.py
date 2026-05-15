"""AI Request Queue: FIFO with capacity, TTL, and dead-letter queue (DLQ)."""

import asyncio
import sqlite3
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class QueuedRequest:
    """Queued AI request."""
    id: str
    prompt: str
    priority: int = 1
    ttl_seconds: int = 3600  # 1 hour default
    created_at: str = None
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.context is None:
            self.context = {}


class AIRequestQueue:
    """FIFO queue with capacity, TTL, and DLQ."""

    def __init__(self, db_path: str, max_capacity: int = 100):
        self.db_path = db_path
        self.max_capacity = max_capacity
        self._lock = asyncio.Lock()

    def init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main queue table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_request_queue (
                id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                ttl_seconds INTEGER DEFAULT 3600,
                created_at TEXT NOT NULL,
                context TEXT,
                position INTEGER
            )
        """)

        # Dead-letter queue
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dead_letter_queue (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                prompt TEXT,
                reason TEXT,
                moved_at TEXT NOT NULL,
                context TEXT
            )
        """)

        conn.commit()
        conn.close()

    async def add(self, request: QueuedRequest) -> None:
        """Add request to queue. Evict oldest if at capacity."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                # Check capacity
                cursor.execute("SELECT COUNT(*) FROM ai_request_queue")
                count = cursor.fetchone()[0]

                if count >= self.max_capacity:
                    # Evict oldest (by rowid)
                    cursor.execute("""
                        DELETE FROM ai_request_queue
                        WHERE ROWID = (SELECT MIN(ROWID) FROM ai_request_queue)
                    """)
                    logger.warning(f"Queue overflow: evicted oldest request (capacity={self.max_capacity})")

                # Insert new request
                cursor.execute("""
                    INSERT INTO ai_request_queue (id, prompt, priority, ttl_seconds, created_at, context)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    request.id,
                    request.prompt,
                    request.priority,
                    request.ttl_seconds,
                    request.created_at,
                    json.dumps(request.context) if request.context else None
                ))

                conn.commit()
            finally:
                conn.close()

    async def get(self) -> Optional[QueuedRequest]:
        """Get next request (FIFO). Returns None if empty."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    SELECT id, prompt, priority, ttl_seconds, created_at, context
                    FROM ai_request_queue
                    ORDER BY ROWID ASC
                    LIMIT 1
                """)

                row = cursor.fetchone()
                if not row:
                    return None

                request_id, prompt, priority, ttl, created_at, context = row

                # Delete from queue
                cursor.execute("DELETE FROM ai_request_queue WHERE id = ?", (request_id,))
                conn.commit()

                return QueuedRequest(
                    id=request_id,
                    prompt=prompt,
                    priority=priority,
                    ttl_seconds=ttl,
                    created_at=created_at,
                    context=json.loads(context) if context else {}
                )
            finally:
                conn.close()

    async def size(self) -> int:
        """Get current queue size."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM ai_request_queue")
                return cursor.fetchone()[0]
            finally:
                conn.close()

    async def cleanup_expired(self) -> int:
        """Remove TTL-expired requests. Returns count removed."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                # Get expired requests
                cursor.execute("""
                    SELECT id, prompt, created_at, context FROM ai_request_queue
                    WHERE datetime(created_at) <= datetime('now', '-' || ttl_seconds || ' seconds')
                """)

                expired = cursor.fetchall()

                if expired:
                    # Move to DLQ
                    now = datetime.now(timezone.utc).isoformat()
                    for req_id, prompt, created_at, context in expired:
                        cursor.execute("""
                            INSERT INTO dead_letter_queue (id, request_id, prompt, reason, moved_at, context)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            f"dlq-{req_id}",
                            req_id,
                            prompt,
                            "TTL_EXPIRED",
                            now,
                            context
                        ))

                    # Delete from main queue
                    for req_id, _, _, _ in expired:
                        cursor.execute("DELETE FROM ai_request_queue WHERE id = ?", (req_id,))

                    conn.commit()
                    logger.info(f"Cleaned up {len(expired)} TTL-expired requests")

                return len(expired)
            finally:
                conn.close()

    async def move_to_dlq(self, request_id: str, reason: str) -> None:
        """Move request to dead-letter queue."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                # Get request
                cursor.execute("""
                    SELECT prompt, context FROM ai_request_queue WHERE id = ?
                """, (request_id,))

                row = cursor.fetchone()
                if row:
                    prompt, context = row

                    # Add to DLQ
                    now = datetime.now(timezone.utc).isoformat()
                    cursor.execute("""
                        INSERT INTO dead_letter_queue (id, request_id, prompt, reason, moved_at, context)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        f"dlq-{request_id}",
                        request_id,
                        prompt,
                        reason,
                        now,
                        context
                    ))

                    # Remove from main queue
                    cursor.execute("DELETE FROM ai_request_queue WHERE id = ?", (request_id,))
                    conn.commit()
                    logger.info(f"Moved request {request_id} to DLQ: {reason}")
            finally:
                conn.close()

    async def get_dlq(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get dead-letter queue items."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    SELECT id, request_id, prompt, reason, moved_at, context
                    FROM dead_letter_queue
                    ORDER BY moved_at DESC
                    LIMIT ?
                """, (limit,))

                results = []
                for row in cursor.fetchall():
                    dlq_id, req_id, prompt, reason, moved_at, context = row
                    results.append({
                        "dlq_id": dlq_id,
                        "request_id": req_id,
                        "prompt": prompt,
                        "reason": reason,
                        "moved_at": moved_at,
                        "context": json.loads(context) if context else {}
                    })

                return results
            finally:
                conn.close()

    def close(self) -> None:
        """Close queue (cleanup)."""
        pass
