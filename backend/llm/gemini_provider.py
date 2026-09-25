"""
Gemini LLM provider — implements LLMProvider using Google Generative AI SDK.

Gemini does not speak the OpenAI chat dialect, so this is a standalone
implementation rather than a subclass of OpenAICompatibleProvider. The only
difference from an OpenAI-compatible provider is that system instructions are
inlined into a single user prompt.

Configuration is loaded from environment variables only.
"""
import os
import google.generativeai as genai

from llm.base import LLMProvider
from llm.prompts import load_prompt
import logging

logger = logging.getLogger(__name__)

SYSTEM_TRIAGE = "You are an intelligent medical assistant that triages patients."
SYSTEM_COMPASSIONATE = "You are a compassionate AI medical assistant. Do not diagnose; only guide."


class GeminiProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._model = genai.GenerativeModel(model_name)

    def _invoke(self, system: str, user: str) -> str:
        # No system role available, so fold the instruction into the prompt.
        response = self._model.generate_content(f"{system}\n\n{user}")
        return response.text.strip()

    def normalize_symptoms(self, phrases: list[str]) -> list[str]:
        logger.info("[GeminiProvider] Normalizing symptoms")
        prompt = load_prompt("normalize").format(phrases=phrases)
        raw = self._invoke(SYSTEM_COMPASSIONATE, prompt)
        return [term.strip().lower() for term in raw.split(",") if term.strip()]

    def recommend_specialists(
        self, symptoms: list[str], available_specialists: list[str]
    ) -> list[str]:
        logger.info("[GeminiProvider] Recommending specialists")
        prompt = load_prompt("recommend").format(
            symptoms=", ".join(symptoms),
            specialists=", ".join(available_specialists),
        )
        raw = self._invoke(SYSTEM_TRIAGE, prompt)
        # Same output filter as the OpenAI-compatible providers: a hallucinated
        # specialist is dropped rather than routed to.
        return [
            name.strip()
            for name in raw.split(",")
            if name.strip() in available_specialists
        ]

    def call_prompt(self, prompt_name: str, **kwargs) -> str:
        logger.info(f"[GeminiProvider] Calling prompt: {prompt_name}")
        prompt = load_prompt(prompt_name).format(**kwargs)
        return self._invoke(SYSTEM_TRIAGE, prompt)