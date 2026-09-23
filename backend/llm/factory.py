"""
LLM Provider Factory

Reads LLM_PROVIDER from the environment and returns the appropriate provider.

Supported values:
  - "openai"   (default)
  - "gemini"
  - "cerebras"

Usage:
    from llm.factory import LLMProviderFactory
    llm = LLMProviderFactory.create()
"""
import os
import logging
from llm.base import LLMProvider

logger = logging.getLogger(__name__)


def _resolve(provider_key: str) -> type[LLMProvider]:
    """Map an LLM_PROVIDER value to its provider class."""
    providers: dict[str, tuple[str, str]] = {
        "openai": ("llm.openai_provider", "OpenAIProvider"),
        "gemini": ("llm.gemini_provider", "GeminiProvider"),
        "cerebras": ("llm.cerebras_provider", "CerebrasProvider"),
    }

    module_path, class_name = providers.get(
        provider_key, providers["openai"]
    )
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)


class LLMProviderFactory:
    @staticmethod
    def create() -> LLMProvider:
        provider_key = os.getenv("LLM_PROVIDER", "openai").lower()

        if provider_key not in {"openai", "gemini", "cerebras"}:
            logger.warning(
                f"[LLMProviderFactory] Unknown provider '{provider_key}', "
                "falling back to OpenAI."
            )
            provider_key = "openai"

        provider_cls = _resolve(provider_key)
        logger.info(f"[LLMProviderFactory] Using {provider_cls.__name__}")
        return provider_cls()