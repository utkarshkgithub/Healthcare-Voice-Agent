"""
Centralized configuration module.
All runtime configuration is loaded from environment variables.
No secrets or provider-specific configuration should appear elsewhere.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ─── Application ────────────────────────────────────────────────────────
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # ─── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")

    # ─── LLM Provider ───────────────────────────────────────────────────────
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")

    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # ─── Speech Provider ──────────────────────────────────────────────────────────────────
    # Supported: webapi (browser-native) | deepgram
    VOICE_PROVIDER: str = os.getenv("VOICE_PROVIDER", "webapi")
    DEEPGRAM_API_KEY: str | None = os.getenv("DEEPGRAM_API_KEY")

    # ─── Logging ────────────────────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        if not cls.DATABASE_URL:
            raise EnvironmentError("DATABASE_URL is required.")

        if cls.LLM_PROVIDER not in {"openai", "gemini"}:
            raise EnvironmentError(
                "LLM_PROVIDER must be either 'openai' or 'gemini'."
            )

        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            raise EnvironmentError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai."
            )

        if cls.LLM_PROVIDER == "gemini" and not cls.GEMINI_API_KEY:
            raise EnvironmentError(
                "GEMINI_API_KEY is required when LLM_PROVIDER=gemini."
            )

        if cls.VOICE_PROVIDER not in {"webapi", "deepgram"}:
            raise EnvironmentError(
                "VOICE_PROVIDER must be either 'webapi' or 'deepgram'."
            )

        if cls.VOICE_PROVIDER == "deepgram" and not cls.DEEPGRAM_API_KEY:
            raise EnvironmentError(
                "DEEPGRAM_API_KEY is required when VOICE_PROVIDER=deepgram."
            )