"""
OpenAI LLM provider — the default backend.

Shares all logic with llm/openai_compatible.py; this file only declares which
endpoint, credential and model to use.
"""
import logging

from llm.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(OpenAICompatibleProvider):
    base_url = "https://api.openai.com/v1"
    api_key_env = "OPENAI_API_KEY"
    model_env = "OPENAI_MODEL"
    default_model = "gpt-4.1-mini"