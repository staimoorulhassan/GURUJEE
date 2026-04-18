"""HeartbeatAgent — monitors agent liveness via ping/pong."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
import yaml
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from gurujee.agents.base_agent import BaseAgent, Message, MessageBus, MessageType
from gurujee.config.loader import ConfigLoader

logger = logging.getLogger(__name__)

_PING_INTERVAL = 8.0   # seconds between ping rounds
_PONG_TIMEOUT = 5.0    # seconds to wait for pongs (increased from 2.0 to avoid false positives)
_MISS_THRESHOLD = 2    # consecutive misses allowed before restart


class HeartbeatAgent(BaseAgent):
    """Broadcasts HEARTBEAT_PING every *ping_interval* s; signals the gateway if an agent fails to pong.

    Default: 8s + 2s = 10s worst-case detection (SC-007). Overridden by
    config/agents.yaml heartbeat.ping_interval_seconds / response_timeout_seconds.
    """

    def __init__(
        self,
        name: str,
        bus: MessageBus,
        data_dir: Optional[Path] = None,
        log_path: Optional[Path] = None,
        ping_interval: float = _PING_INTERVAL,
        pong_timeout: float = _PONG_TIMEOUT,
        miss_threshold: int = _MISS_THRESHOLD,
    ) -> None:
        super().__init__(name, bus)

        # Support either explicit log_path (for tests) or derive from data_dir
        if log_path is not None:
            self._log_path: Optional[Path] = Path(log_path)
        else:
            data = Path(data_dir) if data_dir else Path(
                os.environ.get("GURUJEE_DATA_DIR", "data")
            )
            self._log_path = data / "heartbeat.log"

        # Load intervals from agents.yaml if not explicitly overridden by caller.
        if ping_interval == _PING_INTERVAL and pong_timeout == _PONG_TIMEOUT:
            try:
                config_dir = Path(os.environ.get("GURUJEE_CONFIG_DIR", "config"))
                agents_cfg = ConfigLoader.load_yaml(config_dir / "agents.yaml")
                hb = agents_cfg.get("heartbeat", {})
                ping_interval = float(hb.get("ping_interval_seconds", _PING_INTERVAL))
                pong_timeout = float(hb.get("response_timeout_seconds", _PONG_TIMEOUT))
                miss_threshold = int(hb.get("consecutive_miss_threshold", _MISS_THRESHOLD))
            except (FileNotFoundError, OSError, ValueError, KeyError, yaml.YAMLError):
                pass  # fall back to module-level defaults

        self._ping_interval = ping_interval
        self._pong_timeout = pong_timeout
        self._miss_threshold = miss_threshold

        # ping_id → set of agent names that have NOT yet ponged
        self._pending_pings: dict[str, set[str]] = {}
        # agent_name → how many restarts have been requested
        self._restart_counts: dict[str, int] = {}
        # agent_name → consecutive missed pongs
        self._missed_pongs: dict[str, int] = {}

        self._setup_file_logger()

    # ------------------------------------------------------------------ #
    # Lifecycle                                                             #
    # ------------------------------------------------------------------ #

    async def run(self) -> None:
        logger.info("HeartbeatAgent started")
        ping_task = asyncio.create_task(self._ping_loop())
        try:
            while True:
                msg = await self._inbox.get()
                if msg.type == MessageType.SHUTDOWN:
                    logger.info("HeartbeatAgent: shutdown received")
                    ping_task.cancel()
                    break
                await self._dispatch(msg)
        finally:
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass

    async def handle_message(self, msg: Message) -> None:
        if msg.type == MessageType.HEARTBEAT_PONG:
            await self._handle_pong(msg)

    # ------------------------------------------------------------------ #
    # Ping loop                                                             #
    # ------------------------------------------------------------------ #

    async def _ping_loop(self) -> None:
        """Send HEARTBEAT_PING broadcast every *ping_interval* seconds."""
        while True:
            await self._send_ping()
            await asyncio.sleep(self._ping_interval)

    async def _send_ping(self) -> None:
        """Broadcast a ping and schedule a pong-timeout check."""
        ping_id = str(uuid.uuid4())

        # Track every registered agent except ourselves; broadcast regardless
        try:
            tracked = {
                n for n in self._bus._inboxes  # type: ignore[attr-defined]
                if n != self.name
            }
        except AttributeError:
            tracked = set()

        self._pending_pings[ping_id] = set(tracked)
        logger.debug("HeartbeatAgent: ping %s → %s", ping_id, tracked)

        await self.broadcast(
            MessageType.HEARTBEAT_PING,
            {"ping_id": ping_id},
        )

        # Wait then check who hasn't ponged
        await asyncio.sleep(self._pong_timeout)
        await self._check_pending_pings(ping_id)

    async def _check_pending_pings(self, ping_id: str) -> None:
        """Signal gateway for every agent that missed the pong window N times."""
        missing = self._pending_pings.pop(ping_id, set())
        for agent_name in missing:
            self._missed_pongs[agent_name] = self._missed_pongs.get(agent_name, 0) + 1
            miss_count = self._missed_pongs[agent_name]

            if miss_count >= self._miss_threshold:
                logger.warning(
                    "HeartbeatAgent: %s missed %d pongs — requesting restart",
                    agent_name,
                    miss_count,
                )
                self._restart_counts[agent_name] = self._restart_counts.get(agent_name, 0) + 1
                await self._request_restart(agent_name, ping_id)
            else:
                logger.info(
                    "HeartbeatAgent: %s missed pong (%d/%d) — warning only",
                    agent_name,
                    miss_count,
                    self._miss_threshold,
                )

    # ------------------------------------------------------------------ #
    # Pong handler                                                          #
    # ------------------------------------------------------------------ #

    async def _handle_pong(self, msg: Message) -> None:
        ping_id: str = msg.payload.get("ping_id", "")
        from_agent: str = msg.from_agent
        status: str = msg.payload.get("status", "ok")

        if status == "degraded":
            logger.warning(
                "HeartbeatAgent: pong from %s with degraded status (ping_id=%s)",
                from_agent,
                ping_id,
            )

        pending = self._pending_pings.get(ping_id)
        if pending is not None:
            # Any valid pong resets the miss counter for that agent
            self._missed_pongs[from_agent] = 0

            pending.discard(from_agent)
            logger.debug(
                "HeartbeatAgent: pong from %s (ping_id=%s, remaining=%d)",
                from_agent,
                ping_id,
                len(pending),
            )
            if not pending:
                del self._pending_pings[ping_id]
        else:
            # Even if the ping_id is no longer pending (e.g. late pong),
            # we should still reset the miss counter because the agent is alive.
            self._missed_pongs[from_agent] = 0

    # ------------------------------------------------------------------ #
    # Restart signaling                                                     #
    # ------------------------------------------------------------------ #

    async def _request_restart(self, agent_name: str, ping_id: str) -> None:
        """Signal the gateway that *agent_name* is unresponsive."""
        await self.send(
            "gateway",
            MessageType.AGENT_STATUS_UPDATE,
            {
                "agent": agent_name,
                "status": "ERROR",
                "reason": "pong_timeout",
                "ping_id": ping_id,
                "restart_count": self._restart_counts.get(agent_name, 0),
            },
        )

    # ------------------------------------------------------------------ #
    # File logging                                                          #
    # ------------------------------------------------------------------ #

    def _setup_file_logger(self) -> None:
        """Attach a RotatingFileHandler to the heartbeat logger."""
        if self._log_path is None:
            return
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                str(self._log_path),
                maxBytes=5_242_880,
                backupCount=3,
                encoding="utf-8",
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            )
            logger.addHandler(handler)
        except OSError as exc:
            logger.warning("HeartbeatAgent: could not set up file logger: %s", exc)
