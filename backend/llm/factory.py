"""
LLM Provider Factory

Reads LLM_PROVIDER from environment and returns the appropriate provider.

Supported values:
  - "openai"  (default)
  - "gemini"

Usage:
    from llm.factory import LLMProviderFactory
    llm = LLMProviderFactory.create()
"""
import os
import logging
from llm.base import LLMProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    @staticmethod
    def create() -> LLMProvider:
        provider_key = os.getenv("LLM_PROVIDER", "openai").lower()

        if provider_key == "gemini":
            from llm.gemini_provider import GeminiProvider
            logger.info("[LLMProviderFactory] Using GeminiProvider")
            return GeminiProvider()

        elif provider_key == "openai":
            from llm.openai_provider import OpenAIProvider
            logger.info("[LLMProviderFactory] Using OpenAIProvider")
            return OpenAIProvider()

        else:
            logger.warning(
                f"[LLMProviderFactory] Unknown provider '{provider_key}', falling back to OpenAI."
            )
            from llm.openai_provider import OpenAIProvider
            return OpenAIProvider()
