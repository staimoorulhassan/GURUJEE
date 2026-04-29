"""Persistent voice identity with keystore encryption."""

import logging
import hashlib
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone
from gurujee.keystore.keystore import Keystore

logger = logging.getLogger(__name__)


class VoiceIdentity:
    """Manage persistent voice identity with encryption."""

    def __init__(self, keystore: Keystore):
        self.keystore = keystore
        self.voice_key = "voice_identity"
        self.fallback_voice = "default"

    async def save(
        self,
        voice_id: str,
        voice_name: str,
        audio_sample_hash: str,
        provider: str = "elevenlabs"
    ) -> bool:
        """Save voice identity to encrypted keystore."""
        try:
            identity = {
                "voice_id": voice_id,
                "voice_name": voice_name,
                "audio_sample_hash": audio_sample_hash,
                "provider": provider,
                "cloned_at": datetime.now(timezone.utc).isoformat(),
                "model_version": "1.0",
                "fallback_voice": self.fallback_voice
            }

            # Serialize and store
            import json
            identity_json = json.dumps(identity)
            self.keystore.set(self.voice_key, identity_json)

            logger.info(f"Voice identity saved: {voice_name} ({voice_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to save voice identity: {e}")
            return False

    async def load(self) -> Optional[dict]:
        """Load voice identity from keystore."""
        try:
            identity_json = self.keystore.get(self.voice_key)
            if not identity_json:
                logger.info("No voice identity found, using fallback")
                return {"voice_id": None, "voice_name": self.fallback_voice}

            import json
            return json.loads(identity_json)
        except Exception as e:
            logger.error(f"Failed to load voice identity: {e}")
            return {"voice_id": None, "voice_name": self.fallback_voice}

    async def get_tts_voice(self) -> str:
        """Get voice ID for TTS (falls back to default if not found)."""
        identity = await self.load()
        return identity.get("voice_id") or self.fallback_voice

    def hash_audio_sample(self, audio_path: str) -> str:
        """Hash audio file for fingerprinting."""
        try:
            with open(audio_path, "rb") as f:
                return f"sha256:{hashlib.sha256(f.read()).hexdigest()}"
        except Exception as e:
            logger.error(f"Failed to hash audio: {e}")
            return "unknown"

    async def delete(self) -> bool:
        """Delete stored voice identity."""
        try:
            self.keystore.delete(self.voice_key)
            logger.info("Voice identity deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete voice identity: {e}")
            return False
