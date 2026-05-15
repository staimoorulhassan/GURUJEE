"""Tests for queue management system."""

import pytest
import asyncio
from pathlib import Path
from gurujee.queue.manager import AIRequestQueue, QueuedRequest


@pytest.fixture
def queue(tmp_path):
    """Create queue with temp database."""
    queue_obj = AIRequestQueue(str(tmp_path / "queue.db"))
    queue_obj.init_db()
    yield queue_obj
    queue_obj.close()


@pytest.mark.asyncio
async def test_queue_fifo_order(queue):
    """Test FIFO queue ordering."""
    req1 = QueuedRequest(id="1", prompt="test1", priority=1)
    req2 = QueuedRequest(id="2", prompt="test2", priority=1)
    req3 = QueuedRequest(id="3", prompt="test3", priority=1)

    await queue.add(req1)
    await queue.add(req2)
    await queue.add(req3)

    # Get should return in FIFO order
    item = await queue.get()
    assert item.id == "1"

    item = await queue.get()
    assert item.id == "2"

    item = await queue.get()
    assert item.id == "3"


@pytest.mark.asyncio
async def test_queue_overflow_eviction(queue):
    """Test that oldest is dropped when capacity exceeded."""
    # Set capacity to 3
    queue.max_capacity = 3

    req1 = QueuedRequest(id="1", prompt="test1", priority=1)
    req2 = QueuedRequest(id="2", prompt="test2", priority=1)
    req3 = QueuedRequest(id="3", prompt="test3", priority=1)
    req4 = QueuedRequest(id="4", prompt="test4", priority=1)

    await queue.add(req1)
    await queue.add(req2)
    await queue.add(req3)

    # Adding 4th should evict oldest
    await queue.add(req4)

    # Size should be 3, and req1 should be gone
    size = await queue.size()
    assert size == 3

    item = await queue.get()
    assert item.id == "2"


@pytest.mark.asyncio
async def test_queue_ttl_expiration(queue):
    """Test TTL-based expiration and cleanup."""
    # Set very short TTL for testing
    req = QueuedRequest(id="1", prompt="test", priority=1, ttl_seconds=1)
    await queue.add(req)

    # Should exist initially
    size = await queue.size()
    assert size == 1

    # Wait for TTL
    await asyncio.sleep(1.5)

    # Cleanup should remove expired
    removed = await queue.cleanup_expired()
    assert removed >= 1

    # Queue should be empty
    size = await queue.size()
    assert size == 0


@pytest.mark.asyncio
async def test_dead_letter_queue(queue):
    """Test moving failed messages to DLQ."""
    req = QueuedRequest(id="1", prompt="test", priority=1)
    await queue.add(req)

    # Move to DLQ
    await queue.move_to_dlq("1", reason="API timeout")

    # Should not be in main queue
    size = await queue.size()
    assert size == 0

    # Should be in DLQ
    dlq_items = await queue.get_dlq()
    assert len(dlq_items) >= 1
    assert dlq_items[0]["request_id"] == "1"
    assert dlq_items[0]["reason"] == "API timeout"


@pytest.mark.asyncio
async def test_queue_concurrent_access(queue):
    """Test thread-safe concurrent access."""
    async def add_requests(count, base_id):
        for i in range(count):
            req = QueuedRequest(id=f"{base_id}-{i}", prompt=f"test-{i}", priority=1)
            await queue.add(req)

    # Add concurrently
    await asyncio.gather(
        add_requests(5, "a"),
        add_requests(5, "b"),
    )

    # Total should be 10
    size = await queue.size()
    assert size == 10


@pytest.mark.asyncio
async def test_queue_empty_get(queue):
    """Test getting from empty queue returns None."""
    item = await queue.get()
    assert item is None
