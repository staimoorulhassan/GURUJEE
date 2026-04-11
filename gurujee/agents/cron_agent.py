"""CronAgent — scheduled task runner (Phase 1: dormant loader only)."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from gurujee.agents.base_agent import BaseAgent, Message, MessageBus, MessageType

logger = logging.getLogger(__name__)


@dataclass
class CronJob:
    """A single scheduled task entry."""

    id: str
    description: str
    cron_expr: str
    action_type: str
    action_payload: dict
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_run: Optional[str] = None
    next_run: Optional[str] = None


class CronAgent(BaseAgent):
    """Loads cron_jobs.yaml on startup; dormant in Phase 1 — no scheduling executed."""

    def __init__(
        self,
        name: str,
        bus: MessageBus,
        data_dir: Optional[Path] = None,
    ) -> None:
        super().__init__(name, bus)
        self._data_dir = Path(data_dir) if data_dir else Path(
            os.environ.get("GURUJEE_DATA_DIR", "data")
        )
        self._jobs_path = self._data_dir / "cron_jobs.yaml"
        self._jobs: list[CronJob] = []

    # ------------------------------------------------------------------ #
    # Lifecycle                                                             #
    # ------------------------------------------------------------------ #

    async def run(self) -> None:
        self._jobs = self._load_jobs()
        logger.info("CronAgent started: %d active jobs (Phase 1 dormant)", len(self._jobs))
        while True:
            msg = await self._inbox.get()
            if msg.type == MessageType.SHUTDOWN:
                logger.info("CronAgent: shutdown received")
                break
            await self._dispatch(msg)

    async def handle_message(self, msg: Message) -> None:
        # No message types handled in Phase 1
        pass

    # ------------------------------------------------------------------ #
    # Public API (callable from gateway)                                    #
    # ------------------------------------------------------------------ #

    def add_job(self, job: CronJob) -> str:
        """Register a new cron job and persist to data/cron_jobs.yaml."""
        self._jobs.append(job)
        self._save_jobs()
        logger.info("CronAgent: job added id=%s desc=%s", job.id, job.description)
        return job.id

    def list_jobs(self) -> list[CronJob]:
        """Return all registered cron jobs."""
        return list(self._jobs)

    # ------------------------------------------------------------------ #
    # Persistence                                                           #
    # ------------------------------------------------------------------ #

    def _load_jobs(self) -> list[CronJob]:
        if not self._jobs_path.exists():
            return []
        try:
            with self._jobs_path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            raw_jobs = data.get("jobs", [])
            jobs: list[CronJob] = []
            for raw in raw_jobs:
                jobs.append(CronJob(
                    id=raw["id"],
                    description=raw.get("description", ""),
                    cron_expr=raw.get("cron_expr", ""),
                    action_type=raw.get("action_type", ""),
                    action_payload=raw.get("action_payload", {}),
                    active=raw.get("active", True),
                    created_at=raw.get("created_at", ""),
                    last_run=raw.get("last_run"),
                    next_run=raw.get("next_run"),
                ))
            return jobs
        except Exception as exc:
            logger.error("CronAgent: failed to load cron_jobs.yaml: %s", exc)
            return []

    def _save_jobs(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "jobs": [
                {
                    "id": j.id,
                    "description": j.description,
                    "cron_expr": j.cron_expr,
                    "action_type": j.action_type,
                    "action_payload": j.action_payload,
                    "active": j.active,
                    "created_at": j.created_at,
                    "last_run": j.last_run,
                    "next_run": j.next_run,
                }
                for j in self._jobs
            ]
        }
        with self._jobs_path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, allow_unicode=True)
