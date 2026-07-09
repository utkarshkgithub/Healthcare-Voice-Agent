"""
Web API voice provider — a no-op server-side provider for when the browser
handles STT and TTS natively via the Web Speech API.

When VOICE_PROVIDER=webapi:
  - STT is performed entirely in the browser (SpeechRecognition API).
  - TTS is performed entirely in the browser (SpeechSynthesis API).
  - The /stt and /tts backend endpoints return HTTP 501 to make this explicit.

This class exists to maintain the factory pattern and to allow the
VoiceProviderFactory to always return a non-null VoiceProvider instance.
"""
import logging
from voice.base import VoiceProvider

logger = logging.getLogger(__name__)


class WebApiProvider(VoiceProvider):
    """
    Browser-delegated voice provider.
    STT and TTS are handled client-side; these methods intentionally raise.
    """

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        logger.warning("[WebApiProvider] transcribe() called but STT is browser-side.")
        raise NotImplementedError(
            "VOICE_PROVIDER=webapi: STT is handled by the browser. "
            "The /stt endpoint is not available in this mode."
        )

    def synthesize(self, text: str) -> bytes:
        logger.warning("[WebApiProvider] synthesize() called but TTS is browser-side.")
        raise NotImplementedError(
            "VOICE_PROVIDER=webapi: TTS is handled by the browser. "
            "The /tts endpoint is not available in this mode."
        )
