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
    DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
    DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "10"))

    # ─── LLM Provider ───────────────────────────────────────────────────────
    # Supported: openai | gemini | cerebras
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")

    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    CEREBRAS_API_KEY: str | None = os.getenv("CEREBRAS_API_KEY")
    CEREBRAS_MODEL: str = os.getenv("CEREBRAS_MODEL", "llama-3.3-70b")

    # ─── Speech Provider ──────────────────────────────────────────────────────────────────
    # Supported: webapi (browser-native) | deepgram
    VOICE_PROVIDER: str = os.getenv("VOICE_PROVIDER", "webapi")
    DEEPGRAM_API_KEY: str | None = os.getenv("DEEPGRAM_API_KEY")

    # ─── Logging ────────────────────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ─── Clinical ───────────────────────────────────────────────────────────
    #: Number given to the patient on the emergency path. Localised because
    #: getting this wrong is a real safety issue, not a config nit.
    EMERGENCY_NUMBER: str = os.getenv("EMERGENCY_NUMBER", "108")

    # ─── Auth ───────────────────────────────────────────────────────────────
    #: Signing key for access tokens. Must be set explicitly in production;
    #: a generated fallback would silently change on every restart and
    #: invalidate every issued token.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_TTL_SECONDS: int = int(os.getenv("JWT_TTL_SECONDS", "3600"))

    @classmethod
    def validate(cls):
        if not cls.DATABASE_URL:
            raise EnvironmentError("DATABASE_URL is required.")

        if cls.DB_POOL_MIN_SIZE < 1:
            raise EnvironmentError("DB_POOL_MIN_SIZE must be at least 1.")
        if cls.DB_POOL_MAX_SIZE < cls.DB_POOL_MIN_SIZE:
            raise EnvironmentError(
                "DB_POOL_MAX_SIZE must be greater than or equal to DB_POOL_MIN_SIZE."
            )

        supported = {"openai", "gemini", "cerebras"}
        if cls.LLM_PROVIDER not in supported:
            raise EnvironmentError(
                f"LLM_PROVIDER must be one of: {', '.join(sorted(supported))}."
            )

        # Only the selected provider's key is required — having all three set
        # is fine and lets you switch without editing anything.
        required_keys = {
            "openai": ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
            "gemini": ("GEMINI_API_KEY", cls.GEMINI_API_KEY),
            "cerebras": ("CEREBRAS_API_KEY", cls.CEREBRAS_API_KEY),
        }
        env_name, key_value = required_keys[cls.LLM_PROVIDER]
        if not key_value:
            raise EnvironmentError(
                f"{env_name} is required when LLM_PROVIDER={cls.LLM_PROVIDER}."
            )

        if cls.VOICE_PROVIDER not in {"webapi", "deepgram"}:
            raise EnvironmentError(
                "VOICE_PROVIDER must be either 'webapi' or 'deepgram'."
            )

        if cls.VOICE_PROVIDER == "deepgram" and not cls.DEEPGRAM_API_KEY:
            raise EnvironmentError(
                "DEEPGRAM_API_KEY is required when VOICE_PROVIDER=deepgram."
            )

        if not cls.JWT_SECRET:
            raise EnvironmentError(
                "JWT_SECRET is required. Generate one with: "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )