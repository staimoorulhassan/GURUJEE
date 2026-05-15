"""Tests for audit logging system."""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from gurujee.audit.logger import AuditLogger


@pytest.fixture
def audit_logger(tmp_path):
    """Create audit logger with temp directory."""
    logger = AuditLogger(str(tmp_path / "audit.jsonl"), str(tmp_path / "archive"))
    yield logger
    # Cleanup
    logger.close()


def test_audit_log_creation(audit_logger):
    """Test creating and retrieving audit log entry."""
    audit_logger.log(
        action="send_message",
        resource="chat",
        user_id="local",
        change={"to": "Alice", "text": "Hello"},
        outcome="success"
    )

    logs = audit_logger.get_logs()
    assert len(logs) == 1
    assert logs[0]["action"] == "send_message"
    assert logs[0]["resource"] == "chat"
    assert logs[0]["user_id"] == "local"
    assert logs[0]["outcome"] == "success"
    assert "timestamp" in logs[0]


def test_audit_log_retention_policy(audit_logger, tmp_path):
    """Test archiving logs older than 90 days."""
    # Create old log (95 days ago)
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=95)).isoformat()
    old_entry = {
        "timestamp": old_timestamp,
        "action": "old_action",
        "resource": "test",
        "user_id": "local",
        "change": {},
        "outcome": "success"
    }

    # Write old entry directly
    audit_file = Path(audit_logger.audit_file)
    with open(audit_file, "a") as f:
        f.write(json.dumps(old_entry) + "\n")

    # Create recent log
    audit_logger.log(
        action="recent_action",
        resource="test",
        user_id="local",
        change={},
        outcome="success"
    )

    # Archive old logs
    archived_count = audit_logger.archive_old_logs(days=90)
    assert archived_count >= 1

    # Verify old log was archived
    logs = audit_logger.get_logs()
    assert all(log["action"] != "old_action" for log in logs)


def test_audit_log_multiple_entries(audit_logger):
    """Test logging multiple entries."""
    for i in range(5):
        audit_logger.log(
            action=f"action_{i}",
            resource="test",
            user_id="local",
            change={"index": i},
            outcome="success"
        )

    logs = audit_logger.get_logs()
    assert len(logs) == 5
    assert logs[0]["change"]["index"] == 0
    assert logs[4]["change"]["index"] == 4


def test_audit_log_export(audit_logger, tmp_path):
    """Test exporting logs."""
    audit_logger.log(
        action="test_export",
        resource="test",
        user_id="local",
        change={"data": "test"},
        outcome="success"
    )

    export_path = tmp_path / "export.jsonl"
    count = audit_logger.export_logs(str(export_path))

    assert count >= 1
    assert export_path.exists()

    # Verify export content
    with open(export_path) as f:
        lines = f.readlines()
        assert len(lines) >= 1
        entry = json.loads(lines[0])
        assert entry["action"] == "test_export"
