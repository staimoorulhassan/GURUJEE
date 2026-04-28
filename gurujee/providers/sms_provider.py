"""SMS provider abstraction: custom backend support."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
import logging
import httpx

logger = logging.getLogger(__name__)


@dataclass
class SMSMessage:
    """SMS message data."""
    id: str
    phone_number: str
    text: str
    timestamp: str
    direction: str  # "in" or "out"
    contact_name: Optional[str] = None


@dataclass
class SMSSendResult:
    """Result of SMS send operation."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class SMSProvider(ABC):
    """Abstract base for SMS providers."""

    @abstractmethod
    async def get_recent_messages(self, phone_number: Optional[str] = None, limit: int = 10) -> List[SMSMessage]:
        """Retrieve recent SMS messages."""
        pass

    @abstractmethod
    async def send_sms(self, phone_number: str, text: str) -> SMSSendResult:
        """Send SMS message."""
        pass

    @abstractmethod
    async def get_conversation_thread(self, phone_number: str, depth: int = 10) -> List[SMSMessage]:
        """Get SMS conversation with contact (last N messages)."""
        pass


class CustomSMSProvider(SMSProvider):
    """Custom SMS provider using local Termux:API or custom backend."""

    def __init__(self, backend_url: Optional[str] = None):
        self.backend_url = backend_url  # e.g., http://localhost:8000
        self.client = httpx.AsyncClient(timeout=30.0)
        self._use_termux = backend_url is None  # Use Termux:API if no backend

    async def get_recent_messages(self, phone_number: Optional[str] = None, limit: int = 10) -> List[SMSMessage]:
        """Retrieve recent SMS from device (Termux:API) or backend."""
        try:
            if self._use_termux:
                # Use Termux:API /sdcard/termux.sms.list.json
                import subprocess
                result = subprocess.run(
                    ["termux-sms-list"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    import json
                    messages = json.loads(result.stdout)
                    # Filter by phone_number if provided
                    if phone_number:
                        messages = [m for m in messages if m.get("number") == phone_number]
                    return self._convert_termux_messages(messages[:limit])
                return []
            else:
                # Query custom backend
                url = f"{self.backend_url}/sms/messages"
                params = {"limit": limit}
                if phone_number:
                    params["phone_number"] = phone_number

                response = await self.client.get(url, params=params)
                if response.status_code == 200:
                    messages = response.json()
                    return [SMSMessage(**m) for m in messages]
                return []
        except Exception as e:
            logger.error(f"Failed to get SMS messages: {e}")
            return []

    async def send_sms(self, phone_number: str, text: str) -> SMSSendResult:
        """Send SMS via Termux:API or backend."""
        try:
            if self._use_termux:
                # Use Termux:API
                import subprocess
                result = subprocess.run(
                    ["termux-sms-send", "-n", phone_number, text],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    return SMSSendResult(success=True, message_id=f"sms-{hash(text) % 100000}")
                return SMSSendResult(success=False, error=result.stderr)
            else:
                # Send via custom backend
                url = f"{self.backend_url}/sms/send"
                payload = {"phone_number": phone_number, "text": text}

                response = await self.client.post(url, json=payload)
                if response.status_code in [200, 201]:
                    result = response.json()
                    return SMSSendResult(success=True, message_id=result.get("message_id"))
                return SMSSendResult(success=False, error=response.text)
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return SMSSendResult(success=False, error=str(e))

    async def get_conversation_thread(self, phone_number: str, depth: int = 10) -> List[SMSMessage]:
        """Get SMS conversation with contact (last N messages)."""
        messages = await self.get_recent_messages(phone_number, limit=depth)
        # Return in chronological order (oldest first)
        return sorted(messages, key=lambda m: m.timestamp)

    def _convert_termux_messages(self, messages: List[dict]) -> List[SMSMessage]:
        """Convert Termux:API message format to SMSMessage."""
        result = []
        for msg in messages:
            result.append(SMSMessage(
                id=str(msg.get("_id", "")),
                phone_number=msg.get("number", ""),
                text=msg.get("body", ""),
                timestamp=str(msg.get("date", "")),
                direction="in" if msg.get("type") == 1 else "out",
                contact_name=msg.get("contact_name")
            ))
        return result

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()
