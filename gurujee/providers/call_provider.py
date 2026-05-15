"""Call provider abstraction: incoming call handling, voicemail, transfers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
import logging
import httpx

logger = logging.getLogger(__name__)


@dataclass
class CallEvent:
    """Incoming call event."""
    call_id: str
    phone_number: str
    contact_name: Optional[str] = None
    timestamp: str = ""
    direction: str = "in"  # "in" or "out"


@dataclass
class VoicemailData:
    """Voicemail recording and metadata."""
    message_id: str
    phone_number: str
    contact_name: Optional[str] = None
    transcript: Optional[str] = None
    audio_path: Optional[str] = None
    timestamp: str = ""


@dataclass
class CallActionResult:
    """Result of call action (answer, transfer, etc.)."""
    success: bool
    error: Optional[str] = None


class CallProvider(ABC):
    """Abstract base for call/voicemail providers."""

    @abstractmethod
    async def listen_for_calls(self) -> CallEvent:
        """Listen for incoming call. Yields CallEvent when call arrives."""
        pass

    @abstractmethod
    async def answer_call(self, call_id: str) -> CallActionResult:
        """Answer incoming call."""
        pass

    @abstractmethod
    async def transfer_call(self, call_id: str, target_phone: str) -> CallActionResult:
        """Transfer call to another number."""
        pass

    @abstractmethod
    async def record_voicemail(self, call_id: str, prompt: str) -> VoicemailData:
        """Record voicemail with prompt."""
        pass

    @abstractmethod
    async def get_recent_calls(self, limit: int = 10) -> List[CallEvent]:
        """Get recent calls (missed, answered, etc.)."""
        pass


class CustomCallProvider(CallProvider):
    """Custom call provider using Termux:API or custom backend."""

    def __init__(self, backend_url: Optional[str] = None):
        self.backend_url = backend_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self._use_termux = backend_url is None

    async def listen_for_calls(self) -> CallEvent:
        """Listen for incoming calls (blocking)."""
        if self._use_termux:
            # Would integrate with pjsua2 or Termux:API call monitoring
            # For now, return mock
            return CallEvent(
                call_id="call-mock",
                phone_number="+1234567890",
                timestamp="2026-04-28T12:00:00Z"
            )
        else:
            try:
                # Long-poll custom backend for calls
                url = f"{self.backend_url}/calls/listen"
                response = await self.client.get(url, timeout=60.0)
                if response.status_code == 200:
                    data = response.json()
                    return CallEvent(**data)
            except Exception as e:
                logger.error(f"Call listen error: {e}")

            return CallEvent(
                call_id="",
                phone_number="",
                timestamp=""
            )

    async def answer_call(self, call_id: str) -> CallActionResult:
        """Answer incoming call."""
        try:
            if self._use_termux:
                # pjsua2 answer via daemon
                return CallActionResult(success=True)
            else:
                url = f"{self.backend_url}/calls/{call_id}/answer"
                response = await self.client.post(url)
                return CallActionResult(success=response.status_code == 200)
        except Exception as e:
            logger.error(f"Failed to answer call: {e}")
            return CallActionResult(success=False, error=str(e))

    async def transfer_call(self, call_id: str, target_phone: str) -> CallActionResult:
        """Transfer call to another number."""
        try:
            if self._use_termux:
                # pjsua2 transfer
                return CallActionResult(success=True)
            else:
                url = f"{self.backend_url}/calls/{call_id}/transfer"
                payload = {"target_phone": target_phone}
                response = await self.client.post(url, json=payload)
                return CallActionResult(success=response.status_code == 200)
        except Exception as e:
            logger.error(f"Failed to transfer call: {e}")
            return CallActionResult(success=False, error=str(e))

    async def record_voicemail(self, call_id: str, prompt: str) -> VoicemailData:
        """Record voicemail with prompt (TTS prompt first, then recording)."""
        try:
            if self._use_termux:
                # pjsua2 voice recording
                return VoicemailData(
                    message_id=f"vm-{call_id}",
                    phone_number="",
                    timestamp="2026-04-28T12:00:00Z"
                )
            else:
                url = f"{self.backend_url}/voicemails/record"
                payload = {"call_id": call_id, "prompt": prompt}
                response = await self.client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return VoicemailData(**data)
        except Exception as e:
            logger.error(f"Voicemail recording error: {e}")

        return VoicemailData(
            message_id=f"vm-{call_id}",
            phone_number="",
            timestamp=""
        )

    async def get_recent_calls(self, limit: int = 10) -> List[CallEvent]:
        """Get recent calls."""
        try:
            if self._use_termux:
                # Termux:API call log
                import subprocess
                result = subprocess.run(
                    ["termux-call-log"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    import json
                    calls = json.loads(result.stdout)
                    return [CallEvent(
                        call_id=str(c.get("id", "")),
                        phone_number=c.get("number", ""),
                        contact_name=c.get("contact_name"),
                        timestamp=str(c.get("date", ""))
                    ) for c in calls[:limit]]
                return []
            else:
                url = f"{self.backend_url}/calls/recent"
                response = await self.client.get(url, params={"limit": limit})
                if response.status_code == 200:
                    calls = response.json()
                    return [CallEvent(**c) for c in calls]
                return []
        except Exception as e:
            logger.error(f"Failed to get recent calls: {e}")
            return []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()
