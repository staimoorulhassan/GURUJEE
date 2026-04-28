"""Voice provider abstraction: ElevenLabs, custom, fallback."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging
import asyncio
import httpx

logger = logging.getLogger(__name__)


@dataclass
class VoiceCloneResult:
    """Result of voice cloning operation."""
    success: bool
    voice_id: Optional[str] = None
    error: Optional[str] = None
    status: str = "pending"  # pending, processing, ready, failed


class VoiceProvider(ABC):
    """Abstract base for voice cloning and TTS providers."""

    @abstractmethod
    async def clone_voice(self, audio_path: str, voice_name: str) -> VoiceCloneResult:
        """Clone voice from audio file. Returns voice_id if successful."""
        pass

    @abstractmethod
    async def get_voice_status(self, voice_id: str) -> str:
        """Get status of cloning job: pending, processing, ready, failed."""
        pass

    @abstractmethod
    async def tts_stream(self, text: str, voice_id: str, model: str = "default") -> bytes:
        """Generate speech from text using voice_id. Returns audio bytes."""
        pass


class ElevenLabsVoiceProvider(VoiceProvider):
    """ElevenLabs voice cloning and TTS provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def clone_voice(self, audio_path: str, voice_name: str) -> VoiceCloneResult:
        """Clone voice from audio file via ElevenLabs API."""
        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            # POST /v1/voices/add with audio file
            url = f"{self.base_url}/v1/voices/add"
            headers = {"xi-api-key": self.api_key}
            files = {"files": (audio_path, audio_data, "audio/wav")}
            data = {"name": voice_name, "labels": '{"accent": "neutral"}'}

            response = await self.client.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()

            result = response.json()
            return VoiceCloneResult(
                success=True,
                voice_id=result.get("voice_id"),
                status="ready"
            )
        except Exception as e:
            logger.error(f"ElevenLabs cloning failed: {e}")
            return VoiceCloneResult(
                success=False,
                error=str(e),
                status="failed"
            )

    async def get_voice_status(self, voice_id: str) -> str:
        """ElevenLabs voices are instantly ready."""
        return "ready"

    async def tts_stream(self, text: str, voice_id: str, model: str = "default") -> bytes:
        """Generate speech via ElevenLabs TTS API."""
        try:
            url = f"{self.base_url}/v1/text-to-speech/{voice_id}"
            headers = {"xi-api-key": self.api_key}
            payload = {
                "text": text,
                "model_id": model or "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            }

            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            return response.content
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            return b""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()


class CustomVoiceProvider(VoiceProvider):
    """Custom voice provider: mock implementation for testing and custom backends."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self._voice_store = {}  # in-memory store for testing

    async def clone_voice(self, audio_path: str, voice_name: str) -> VoiceCloneResult:
        """Clone voice using custom provider API."""
        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()

            # POST /v1/voices/clone to custom endpoint
            url = f"{self.base_url}/v1/voices/clone"
            files = {"audio": (audio_path, audio_data)}
            data = {"name": voice_name}

            try:
                response = await self.client.post(url, files=files, data=data)
                response.raise_for_status()
                result = response.json()
                return VoiceCloneResult(
                    success=True,
                    voice_id=result.get("voice_id"),
                    status=result.get("status", "ready")
                )
            except (httpx.ConnectError, httpx.TimeoutException):
                # Fallback to mock for testing
                voice_id = f"custom-{voice_name}-{hash(audio_path) % 10000}"
                self._voice_store[voice_id] = {"name": voice_name, "audio": audio_data}
                return VoiceCloneResult(
                    success=True,
                    voice_id=voice_id,
                    status="ready"
                )
        except Exception as e:
            logger.warning(f"Custom voice provider error: {e}, using mock")
            return VoiceCloneResult(
                success=True,
                voice_id=f"mock-{voice_name}",
                status="ready"
            )

    async def get_voice_status(self, voice_id: str) -> str:
        """Get status from custom provider."""
        try:
            url = f"{self.base_url}/v1/voices/{voice_id}/status"
            response = await self.client.get(url)
            if response.status_code == 200:
                return response.json().get("status", "ready")
        except:
            pass

        # Fallback: check in-memory store
        if voice_id in self._voice_store:
            return "ready"

        return "unknown"

    async def tts_stream(self, text: str, voice_id: str, model: str = "default") -> bytes:
        """Generate speech using custom provider."""
        try:
            url = f"{self.base_url}/v1/tts/{voice_id}"
            payload = {"text": text, "model": model}

            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.content
        except:
            # Fallback: return empty (real provider would handle)
            logger.warning(f"Custom TTS failed for voice {voice_id}")
            return b""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()
