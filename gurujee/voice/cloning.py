"""Voice cloning with provider abstraction."""

import asyncio
import logging
from typing import Optional
from gurujee.providers.voice_provider import (
    VoiceProvider,
    ElevenLabsVoiceProvider,
    CustomVoiceProvider,
    VoiceCloneResult
)

logger = logging.getLogger(__name__)


class VoiceCloner:
    """Clone voice using ElevenLabs or custom provider with retry logic."""

    def __init__(self, provider: Optional[VoiceProvider] = None):
        # Default to custom provider for testing
        self.provider = provider or CustomVoiceProvider()
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    async def clone_with_retry(self, audio_path: str, voice_name: str) -> VoiceCloneResult:
        """Clone voice with automatic retry."""
        for attempt in range(self.max_retries):
            try:
                result = await self.provider.clone_voice(audio_path, voice_name)

                if result.success:
                    logger.info(f"Voice cloning succeeded: {result.voice_id}")
                    return result

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    return result
            except Exception as e:
                logger.error(f"Clone attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    return VoiceCloneResult(
                        success=False,
                        error=str(e),
                        status="failed"
                    )

        return VoiceCloneResult(success=False, error="Max retries exceeded", status="failed")

    async def get_status(self, voice_id: str) -> str:
        """Get cloning status."""
        return await self.provider.get_voice_status(voice_id)

    async def tts(self, text: str, voice_id: str, model: str = "default") -> bytes:
        """Generate speech."""
        return await self.provider.tts_stream(text, voice_id, model)
