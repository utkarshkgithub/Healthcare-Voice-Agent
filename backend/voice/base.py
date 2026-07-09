"""
Voice Provider abstract base class.

All voice providers must implement this interface.
API endpoints call provider methods — never vendor SDKs directly.

Follows the same SOLID structure as llm/base.py:
  - transcribe(): STT — audio bytes → text
  - synthesize(): TTS — text → audio bytes
"""
from abc import ABC, abstractmethod


class VoiceProvider(ABC):

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
        """
        Convert audio bytes to a text transcript.

        Args:
            audio_bytes: Raw audio data from the client.
            mime_type: MIME type of the audio (e.g. 'audio/webm', 'audio/wav').

        Returns:
            The transcribed text string.

        Raises:
            NotImplementedError: If this provider does not support server-side STT
                                 (e.g. WebApiProvider, where STT is browser-side).
        """
        ...

    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """
        Convert text to speech audio bytes.

        Args:
            text: The text to synthesize.

        Returns:
            Raw audio bytes (e.g. MP3 or linear16 PCM).

        Raises:
            NotImplementedError: If this provider does not support server-side TTS
                                 (e.g. WebApiProvider, where TTS is browser-side).
        """
        ...
