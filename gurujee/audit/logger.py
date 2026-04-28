"""Audit logging: append-only JSONL with 90-day retention and archival."""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class AuditLogger:
    """JSONL-based audit logger with retention policy."""

    def __init__(self, audit_file: str, archive_dir: str):
        self.audit_file = audit_file
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Ensure audit file parent directory exists
        Path(audit_file).parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        action: str,
        resource: str,
        user_id: str,
        change: Dict[str, Any],
        outcome: str
    ) -> None:
        """Log an audit entry (append-only)."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "resource": resource,
            "user_id": user_id,
            "change": change,
            "outcome": outcome,
        }

        try:
            with open(self.audit_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def get_logs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve all audit logs (or last N)."""
        logs = []
        try:
            if not Path(self.audit_file).exists():
                return logs

            with open(self.audit_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            logger.warning(f"Skipped malformed audit line: {line[:50]}")
        except Exception as e:
            logger.error(f"Failed to read audit logs: {e}")

        if limit:
            return logs[-limit:]
        return logs

    def archive_old_logs(self, days: int = 90) -> int:
        """Archive logs older than N days. Returns count archived."""
        if not Path(self.audit_file).exists():
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        logs = self.get_logs()

        old_logs = []
        recent_logs = []

        for log in logs:
            try:
                log_time = datetime.fromisoformat(log["timestamp"].replace("Z", "+00:00"))
                if log_time < cutoff:
                    old_logs.append(log)
                else:
                    recent_logs.append(log)
            except (ValueError, KeyError):
                recent_logs.append(log)  # Keep if parsing fails

        archived_count = len(old_logs)

        if old_logs:
            # Write archived logs to archive file
            archive_file = self.archive_dir / f"audit-archive-{datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
            try:
                with open(archive_file, "w") as f:
                    for log in old_logs:
                        f.write(json.dumps(log) + "\n")
                logger.info(f"Archived {archived_count} logs to {archive_file}")
            except Exception as e:
                logger.error(f"Failed to archive logs: {e}")
                return 0

            # Rewrite audit file with only recent logs
            try:
                with open(self.audit_file, "w") as f:
                    for log in recent_logs:
                        f.write(json.dumps(log) + "\n")
            except Exception as e:
                logger.error(f"Failed to rewrite audit file: {e}")

        return archived_count

    def export_logs(self, export_path: str) -> int:
        """Export all logs to file. Returns count exported."""
        logs = self.get_logs()
        try:
            with open(export_path, "w") as f:
                for log in logs:
                    f.write(json.dumps(log) + "\n")
            logger.info(f"Exported {len(logs)} logs to {export_path}")
        except Exception as e:
            logger.error(f"Failed to export logs: {e}")
            return 0

        return len(logs)

    def close(self) -> None:
        """Close logger (no-op for file-based logger)."""
        pass
