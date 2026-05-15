"""Call handler: detection, routing, voicemail."""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from gurujee.providers.call_provider import CallProvider, CallEvent, VoicemailData, CustomCallProvider

logger = logging.getLogger(__name__)


class CallHandler:
    """Handle incoming calls, routing, voicemail transcription."""

    def __init__(self, provider: Optional[CallProvider] = None):
        self.provider = provider or CustomCallProvider()
        self._contacts = {}  # Simple in-memory contact store

    def lookup_contact(self, phone_number: str) -> Optional[str]:
        """Lookup contact name by phone number."""
        return self._contacts.get(phone_number)

    def add_contact(self, phone_number: str, contact_name: str) -> None:
        """Add contact."""
        self._contacts[phone_number] = contact_name

    def _mask_phone_number(self, phone_number: Optional[str]) -> str:
        """Mask phone number for safe logging."""
        if not phone_number:
            return "[redacted]"
        visible_digits = 2
        if len(phone_number) <= visible_digits:
            return "*" * len(phone_number)
        return f"{'*' * (len(phone_number) - visible_digits)}{phone_number[-visible_digits:]}"

    def determine_route(self, call_event: CallEvent, priority_tier: str = "normal") -> str:
        """Determine route for call: answer or voicemail."""
        # Simple logic: priority_tier influences route
        if priority_tier == "vip":
            return "answer"  # Auto-answer VIP calls
        elif priority_tier == "spam":
            return "reject"
        else:
            return "voicemail"  # Default to voicemail

    def generate_voicemail_greeting(self, contact_name: Optional[str] = None) -> str:
        """Generate context-aware voicemail greeting."""
        if contact_name:
            return f"Hi {contact_name}, I'm not available right now. Please leave a message."
        else:
            return "I'm not available right now. Please leave a message and I'll get back to you soon."

    def record_call_log(self, call_event: CallEvent, route: str, outcome: str) -> None:
        """Log call for audit trail."""
        masked_phone = self._mask_phone_number(call_event.phone_number)
        logger.info(f"Call from {masked_phone} routed to {route}: {outcome}")

    async def transcribe_voicemail(self, audio_path: str) -> Optional[str]:
        """Transcribe voicemail audio to text (STT)."""
        try:
            # Try to use faster-whisper
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="auto")
            segments, _ = model.transcribe(audio_path, language="en")
            transcript = " ".join(segment.text for segment in segments)
            return transcript
        except ImportError:
            logger.warning("faster-whisper not installed, returning empty transcript")
            return ""
        except Exception as e:
            logger.error(f"Voicemail transcription failed: {e}")
            return ""

    async def store_voicemail(
        self,
        phone_number: str,
        audio_path: str,
        contact_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store voicemail with transcript."""
        transcript = await self.transcribe_voicemail(audio_path)

        voicemail = {
            "message_id": f"vm-{int(datetime.now().timestamp())}",
            "phone_number": phone_number,
            "contact_name": contact_name,
            "transcript": transcript,
            "audio_path": audio_path,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        logger.info(f"Stored voicemail from {phone_number}: {len(transcript)} chars")
        return voicemail

    async def get_voicemail_notifications(self, limit: int = 10) -> List[Dict]:
        """Get recent voicemail notifications."""
        # This would integrate with a voicemail storage backend
        return []

    async def listen_for_calls(self):
        """Listen for incoming calls (blocking)."""
        return await self.provider.listen_for_calls()

    async def answer_call(self, call_id: str):
        """Answer incoming call."""
        result = await self.provider.answer_call(call_id)
        return result.success

    async def transfer_call(self, call_id: str, target_phone: str):
        """Transfer call to another number."""
        result = await self.provider.transfer_call(call_id, target_phone)
        return result.success

    async def record_voicemail_call(self, call_id: str, prompt: str) -> VoicemailData:
        """Record voicemail for call."""
        return await self.provider.record_voicemail(call_id, prompt)

    async def get_recent_calls(self, limit: int = 10) -> List[CallEvent]:
        """Get recent calls."""
        return await self.provider.get_recent_calls(limit)
