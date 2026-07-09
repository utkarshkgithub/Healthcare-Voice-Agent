"""
OpenAI LLM provider — implements LLMProvider using langchain's ChatOpenAI.
Configuration is loaded from environment variables only.
"""
import os
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from llm.base import LLMProvider
import logging

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


class OpenAIProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")

        self._llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            temperature=0.2,
            openai_api_key=api_key,
        )

        # Cache prompts at startup
        self._normalize_prompt = _load_prompt("normalize")
        self._recommend_prompt = _load_prompt("recommend")
        self._followup_prompt = _load_prompt("followup")

    def _invoke(self, system: str, user: str) -> str:
        messages = [SystemMessage(content=system), HumanMessage(content=user)]
        response = self._llm.invoke(messages)
        return response.content.strip()

    def normalize_symptoms(self, phrases: list[str]) -> list[str]:
        logger.info("[OpenAIProvider] Normalizing symptoms")
        prompt = self._normalize_prompt.format(phrases=phrases)
        raw = self._invoke("You are a helpful medical assistant.", prompt)
        return [term.strip().lower() for term in raw.split(",") if term.strip()]

    def recommend_specialists(self, symptoms: list[str], available_specialists: list[str]) -> list[str]:
        logger.info("[OpenAIProvider] Recommending specialists")
        prompt = self._recommend_prompt.format(
            symptoms=", ".join(symptoms),
            specialists=", ".join(available_specialists),
        )
        raw = self._invoke("You are an intelligent medical assistant that triages patients.", prompt)
        return [name.strip() for name in raw.split(",") if name.strip() in available_specialists]

    def generate_response(self, user_message: str, context: str = "") -> str:
        system = "You are a compassionate AI medical assistant. Do not diagnose; only guide."
        user = f"{context}\nPatient: {user_message}" if context else user_message
        return self._invoke(system, user)

    def generate_followup(self, symptoms: list[str]) -> str:
        prompt = self._followup_prompt.format(symptoms=", ".join(symptoms))
        return self._invoke("You are a compassionate AI medical assistant.", prompt)

    def call_prompt(self, prompt_name: str, **kwargs) -> str:
        logger.info(f"[OpenAIProvider] Calling prompt: {prompt_name}")
        prompt_template = _load_prompt(prompt_name)
        prompt = prompt_template.format(**kwargs)
        return self._invoke("You are an intelligent medical assistant.", prompt)
