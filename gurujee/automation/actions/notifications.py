"""Notification actions via Termux:API (T047)."""
from __future__ import annotations

import json
import logging
import subprocess
from typing import Optional

from gurujee.automation.executor import ShizukuExecutor

logger = logging.getLogger(__name__)


async def list_notifications(
    executor: ShizukuExecutor,
    long_term_memory: Optional[object] = None,
) -> list[dict]:
    """Fetch notifications via termux-notification-list.

    Uses subprocess (Termux:API), not Shizuku.
    Optionally caches results in *long_term_memory*.
    """
    try:
        result = subprocess.run(
            ["termux-notification-list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        notifs = json.loads(result.stdout or "[]")
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("termux-notification-list failed: %s", exc)
        notifs = []

    if long_term_memory and hasattr(long_term_memory, "cache_notifications"):
        try:
            normalized = [
                {
                    "notif_id": str(n.get("id", "")),
                    "app_package": n.get("packageName", ""),
                    "app_name": n.get("appName", n.get("packageName", "")),
                    "title": n.get("title"),
                    "content": n.get("content"),
                    "is_read": 0,
                }
                for n in notifs
            ]
            long_term_memory.cache_notifications(normalized)  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("Failed to cache notifications: %s", exc)

    return notifs


async def dismiss_notification(executor: ShizukuExecutor, notif_id: str) -> str:
    """Remove a notification by ID via Termux:API."""
    try:
        result = subprocess.run(
            ["termux-notification-remove", str(notif_id)],
            capture_output=True,
            timeout=5,
        )
        return "dismissed" if result.returncode == 0 else "failed"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "termux-api unavailable"
