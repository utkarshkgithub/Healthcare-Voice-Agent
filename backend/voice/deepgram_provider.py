"""
Deepgram voice provider — implements VoiceProvider using Deepgram REST APIs.

STT: POST audio bytes to Deepgram Listen API → returns transcript text.
TTS: POST text to Deepgram Speak API → returns MP3 audio bytes.

Configuration is loaded from environment variables only.
"""
import os
import logging
import requests
from voice.base import VoiceProvider

logger = logging.getLogger(__name__)

DEEPGRAM_LISTEN_URL = "https://api.deepgram.com/v1/listen"
DEEPGRAM_SPEAK_URL = "https://api.deepgram.com/v1/speak"


class DeepgramProvider(VoiceProvider):
    def __init__(self):
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is not set.")
        self._api_key = api_key
        self._headers = {"Authorization": f"Token {self._api_key}"}

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        """
        Send audio bytes to Deepgram Listen and return the transcript text.
        Uses the nova-2 model for high accuracy medical speech.
        """
        logger.info("[DeepgramProvider] Transcribing audio (%d bytes)", len(audio_bytes))

        params = {
            "model": "nova-2",
            "language": "en-US",
            "punctuate": "true",
            "smart_format": "true",
        }

        response = requests.post(
            DEEPGRAM_LISTEN_URL,
            headers={**self._headers, "Content-Type": mime_type},
            params=params,
            data=audio_bytes,
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        try:
            transcript = (
                result["results"]["channels"][0]["alternatives"][0]["transcript"]
            )
        except (KeyError, IndexError):
            transcript = ""

        logger.info("[DeepgramProvider] Transcript: %r", transcript)
        return transcript.strip()

    def synthesize(self, text: str) -> bytes:
        """
        Send text to Deepgram Speak and return MP3 audio bytes.
        Uses the aura-asteria-en voice — clear, natural, suitable for medical guidance.
        """
        logger.info("[DeepgramProvider] Synthesizing TTS for text (len=%d)", len(text))

        params = {"model": "aura-asteria-en"}

        response = requests.post(
            DEEPGRAM_SPEAK_URL,
            headers={**self._headers, "Content-Type": "application/json"},
            params=params,
            json={"text": text},
            timeout=30,
        )
        response.raise_for_status()

        audio_bytes = response.content
        logger.info("[DeepgramProvider] Synthesized %d bytes of audio", len(audio_bytes))
        return audio_bytes
