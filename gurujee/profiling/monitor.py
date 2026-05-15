"""Memory and performance profiling."""

import logging
import os
import psutil
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """Monitor RAM usage with baseline and threshold alerts."""

    def __init__(self, metrics_file: str, alert_threshold_multiplier: float = 2.0):
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self.alert_threshold_multiplier = alert_threshold_multiplier
        self._baseline_rss = None

    def sample_rss(self) -> int:
        """Sample current RSS (Resident Set Size) in MB."""
        try:
            process = psutil.Process(os.getpid())
            rss_mb = process.memory_info().rss / (1024 * 1024)
            return int(rss_mb)
        except Exception as e:
            logger.error(f"Failed to sample RSS: {e}")
            return 0

    def get_baseline(self) -> int:
        """Get baseline RSS (first measurement or lowest recent)."""
        if self._baseline_rss:
            return self._baseline_rss

        # Try to load from file
        try:
            with open(self.metrics_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            if "rss_mb" in entry:
                                self._baseline_rss = entry["rss_mb"]
                                break
                        except:
                            pass
        except:
            pass

        if not self._baseline_rss:
            self._baseline_rss = self.sample_rss()

        return self._baseline_rss

    def check_threshold(self, current_rss: int) -> bool:
        """Check if current RSS exceeds threshold. Returns True if over threshold."""
        baseline = self.get_baseline()
        threshold = baseline * self.alert_threshold_multiplier

        if current_rss > threshold:
            logger.warning(f"Memory threshold exceeded: {current_rss}MB > {threshold}MB (baseline: {baseline}MB)")
            return True

        return False

    def log_sample(self, label: str = "idle") -> None:
        """Log memory sample to metrics file."""
        try:
            rss_mb = self.sample_rss()
            is_alert = self.check_threshold(rss_mb)

            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "label": label,
                "rss_mb": rss_mb,
                "alert": is_alert
            }

            with open(self.metrics_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

            logger.info(f"Memory sample: {rss_mb}MB ({label})" + (" [ALERT]" if is_alert else ""))
        except Exception as e:
            logger.error(f"Failed to log memory sample: {e}")

    def get_metrics(self, limit: int = 100) -> list:
        """Retrieve logged metrics."""
        metrics = []
        try:
            if not self.metrics_file.exists():
                return metrics

            with open(self.metrics_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            metrics.append(json.loads(line))
                        except:
                            pass

            return metrics[-limit:]
        except Exception as e:
            logger.error(f"Failed to read metrics: {e}")
            return metrics

    def get_p95_latency(self) -> Optional[float]:
        """Calculate p95 latency from chat metrics (placeholder)."""
        # Would read from data/metrics/chat.jsonl
        return None

    def get_startup_time(self) -> Optional[float]:
        """Get boot time from startup metrics."""
        # Would read from daemon startup logs
        return None
