"""
OpenAI-compatible LLM provider base class.

Cerebras and OpenAI both expose an OpenAI-compatible chat completions API,
so they share every line of logic except the base URL, the API key env var,
and the default model. That shared logic lives here; the concrete providers
supply only those three values.

This also means adding a fourth OpenAI-compatible vendor is ~10 lines and
no new dependency.
"""
import os

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from llm.base import LLMProvider
from llm.prompts import load_prompt

SYSTEM_TRIAGE = "You are an intelligent medical assistant that triages patients."
SYSTEM_COMPASSIONATE = "You are a compassionate AI medical assistant. Do not diagnose; only guide."


class OpenAICompatibleProvider(LLMProvider):
    """Base for any provider speaking the OpenAI chat completions dialect."""

    #: Subclasses override these four.
    base_url: str = ""
    api_key_env: str = ""
    model_env: str = ""
    default_model: str = ""
    integration_header: str = ""

    def __init__(self):
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(f"{self.api_key_env} environment variable is not set.")

        headers = {}
        if self.integration_header:
            headers["X-Cerebras-3rd-Party-Integration"] = self.integration_header

        self._llm = ChatOpenAI(
            model=os.getenv(self.model_env, self.default_model),
            temperature=0.2,
            openai_api_key=api_key,
            base_url=self.base_url,
            default_headers=headers or None,
        )

    def _invoke(self, system: str, user: str) -> str:
        response = self._llm.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        return response.content.strip()

    # ─── LLMProvider interface ───────────────────────────────────────────────

    def normalize_symptoms(self, phrases: list[str]) -> list[str]:
        prompt = load_prompt("normalize").format(phrases=phrases)
        raw = self._invoke(SYSTEM_COMPASSIONATE, prompt)
        return [term.strip().lower() for term in raw.split(",") if term.strip()]

    def recommend_specialists(
        self, symptoms: list[str], available_specialists: list[str]
    ) -> list[str]:
        prompt = load_prompt("recommend").format(
            symptoms=", ".join(symptoms),
            specialists=", ".join(available_specialists),
        )
        raw = self._invoke(SYSTEM_TRIAGE, prompt)
        # Filter to the provided list: a hallucinated specialist is dropped
        # rather than routed to. Prompt instructions alone are not enforcement.
        return [
            name.strip()
            for name in raw.split(",")
            if name.strip() in available_specialists
        ]

    def call_prompt(self, prompt_name: str, **kwargs) -> str:
        prompt = load_prompt(prompt_name).format(**kwargs)
        return self._invoke(SYSTEM_TRIAGE, prompt)