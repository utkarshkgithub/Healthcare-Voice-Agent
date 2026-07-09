"""
Voice Provider Factory

Reads VOICE_PROVIDER from environment and returns the appropriate provider.

Supported values:
  - "webapi"   (default) — STT/TTS are browser-side; backend endpoints return 501.
  - "deepgram" — STT/TTS are handled by Deepgram REST APIs.

Usage:
    from voice.factory import VoiceProviderFactory
    voice = VoiceProviderFactory.create()
"""
import os
import logging
from voice.base import VoiceProvider

logger = logging.getLogger(__name__)


class VoiceProviderFactory:
    @staticmethod
    def create() -> VoiceProvider:
        provider_key = os.getenv("VOICE_PROVIDER", "webapi").lower()

        if provider_key == "deepgram":
            from voice.deepgram_provider import DeepgramProvider
            logger.info("[VoiceProviderFactory] Using DeepgramProvider")
            return DeepgramProvider()

        elif provider_key == "webapi":
            from voice.webapi_provider import WebApiProvider
            logger.info("[VoiceProviderFactory] Using WebApiProvider (browser-side STT/TTS)")
            return WebApiProvider()

        else:
            logger.warning(
                "[VoiceProviderFactory] Unknown provider '%s', falling back to WebApiProvider.",
                provider_key,
            )
            from voice.webapi_provider import WebApiProvider
            return WebApiProvider()
