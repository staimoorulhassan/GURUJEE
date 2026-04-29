"""Tests for CronAgent — Phase 1 dormant loader."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from tests.conftest import MockMessageBus


class TestCronAgentInit:
    def test_loads_empty_jobs_when_no_file(self, tmp_path: Path) -> None:
        from gurujee.agents.cron_agent import CronAgent

        bus = MockMessageBus()
        agent = CronAgent(name="cron", bus=bus, data_dir=tmp_path)
        assert agent.list_jobs() == []

    def test_loads_jobs_from_yaml(self, tmp_path: Path) -> None:
        from gurujee.agents.cron_agent import CronAgent, CronJob

        jobs_file = tmp_path / "cron_jobs.yaml"
        jobs_file.write_text(
            yaml.safe_dump({
                "jobs": [{
                    "id": "j1",
                    "description": "test job",
                    "cron_expr": "0 9 * * *",
                    "action_type": "reminder",
                    "action_payload": {"text": "hello"},
                }]
            }),
            encoding="utf-8",
        )
        bus = MockMessageBus()
        agent = CronAgent(name="cron", bus=bus, data_dir=tmp_path)
        # _load_jobs is called in run(); call it directly for the unit test
        jobs = agent._load_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "j1"
        assert jobs[0].cron_expr == "0 9 * * *"

    def test_loads_empty_on_corrupt_yaml(self, tmp_path: Path) -> None:
        from gurujee.agents.cron_agent import CronAgent

        jobs_file = tmp_path / "cron_jobs.yaml"
        jobs_file.write_text("<<<invalid yaml>>>", encoding="utf-8")

        bus = MockMessageBus()
        agent = CronAgent(name="cron", bus=bus, data_dir=tmp_path)
        jobs = agent._load_jobs()
        assert jobs == []


class TestCronAgentAddJob:
    def test_add_job_persists_to_yaml(self, tmp_path: Path) -> None:
        from gurujee.agents.cron_agent import CronAgent, CronJob

        bus = MockMessageBus()
        agent = CronAgent(name="cron", bus=bus, data_dir=tmp_path)
        job = CronJob(
            id="remind-1",
            description="Daily reminder",
            cron_expr="0 8 * * *",
            action_type="reminder",
            action_payload={"text": "Good morning"},
        )
        returned_id = agent.add_job(job)
        assert returned_id == "remind-1"
        assert len(agent.list_jobs()) == 1

        # Verify persisted to disk
        assert (tmp_path / "cron_jobs.yaml").exists()
        with (tmp_path / "cron_jobs.yaml").open() as fh:
            data = yaml.safe_load(fh)
        assert data["jobs"][0]["id"] == "remind-1"

    def test_list_jobs_returns_copy(self, tmp_path: Path) -> None:
        from gurujee.agents.cron_agent import CronAgent, CronJob

        bus = MockMessageBus()
        agent = CronAgent(name="cron", bus=bus, data_dir=tmp_path)
        original = agent.list_jobs()
        original.append("INJECTED")  # mutating return value should not affect agent state
        assert len(agent.list_jobs()) == 0


class TestCronAgentRun:
    @pytest.mark.asyncio
    async def test_run_shuts_down_on_shutdown_message(self, tmp_path: Path) -> None:
        from gurujee.agents.cron_agent import CronAgent
        from gurujee.agents.base_agent import Message, MessageType

        bus = MockMessageBus()
        bus.register_agent("cron", asyncio.Queue())
        agent = CronAgent(name="cron", bus=bus, data_dir=tmp_path)

        async def _send_shutdown() -> None:
            await asyncio.sleep(0.01)
            await agent._inbox.put(
                Message(type=MessageType.SHUTDOWN, from_agent="gateway", to_agent="cron", payload={})
            )

        asyncio.create_task(_send_shutdown())
        await asyncio.wait_for(agent.run(), timeout=2)
