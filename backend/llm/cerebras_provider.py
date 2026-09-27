"""
Cerebras LLM provider.

Cerebras serves an OpenAI-compatible chat completions API, so this provider
reuses the already-installed langchain_openai client pointed at Cerebras'
endpoint rather than pulling in a second SDK. That keeps the dependency list
short and means Cerebras and OpenAI can never drift in behaviour.

Why it exists: Cerebras inference is substantially faster and cheaper than
hosted frontier models, which matters for a voice pipeline where the patient is
waiting on five sequential calls per turn.
"""
import logging

from llm.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class CerebrasProvider(OpenAICompatibleProvider):
    base_url = "https://api.cerebras.ai/v1"
    api_key_env = "CEREBRAS_API_KEY"
    model_env = "CEREBRAS_MODEL"
    default_model = "qwen-3.8-27b"
    #: Cerebras uses this header to attribute third-party SDK traffic.
    integration_header = "healthcare-voice-agent"