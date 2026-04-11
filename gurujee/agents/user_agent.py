"""UserAgent — serves user profile data to other agents."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from gurujee.agents.base_agent import BaseAgent, Message, MessageBus, MessageType
from gurujee.config.loader import ConfigLoader

logger = logging.getLogger(__name__)


class UserAgent(BaseAgent):
    """Reads user identity from data/soul_identity.yaml and responds to profile requests."""

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
        self._soul_path = self._data_dir / "soul_identity.yaml"
        self._user_name: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Lifecycle                                                             #
    # ------------------------------------------------------------------ #

    async def run(self) -> None:
        self._user_name = self._load_user_name()
        logger.info("UserAgent started: user_name=%s", self._user_name or "<not set>")
        while True:
            msg = await self._inbox.get()
            if msg.type == MessageType.SHUTDOWN:
                logger.info("UserAgent: shutdown received")
                break
            await self._dispatch(msg)

    async def handle_message(self, msg: Message) -> None:
        if msg.type == MessageType.USER_PROFILE_REQUEST:
            await self._handle_profile_request(msg)

    # ------------------------------------------------------------------ #
    # Handlers                                                              #
    # ------------------------------------------------------------------ #

    async def _handle_profile_request(self, msg: Message) -> None:
        await self.send(
            msg.from_agent,
            MessageType.USER_PROFILE_RESPONSE,
            {"user_name": self._user_name},
            reply_to=msg.id,
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    def _load_user_name(self) -> Optional[str]:
        """Read user_name from data/soul_identity.yaml; return None if absent."""
        if not self._soul_path.exists():
            logger.warning("UserAgent: soul_identity.yaml not found at %s", self._soul_path)
            return None
        try:
            data = ConfigLoader.load_soul_identity(self._soul_path)
            return data.get("user_name") or None
        except Exception as exc:
            logger.error("UserAgent: failed to load soul identity: %s", exc)
            return None
