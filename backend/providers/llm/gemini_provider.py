"""
Gemini LLM provider — implements LLMProvider using Google Generative AI SDK.
Configuration is loaded from environment variables only.
"""
import os
from pathlib import Path
import google.generativeai as genai
from providers.llm.base import LLMProvider
import logging

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


class GeminiProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self._model = genai.GenerativeModel(model_name)

        self._normalize_prompt = _load_prompt("normalize")
        self._recommend_prompt = _load_prompt("recommend")
        self._followup_prompt = _load_prompt("followup")

    def _invoke(self, prompt: str) -> str:
        response = self._model.generate_content(prompt)
        return response.text.strip()

    def normalize_symptoms(self, phrases: list[str]) -> list[str]:
        logger.info("[GeminiProvider] Normalizing symptoms")
        prompt = self._normalize_prompt.format(phrases=phrases)
        raw = self._invoke(prompt)
        return [term.strip().lower() for term in raw.split(",") if term.strip()]

    def recommend_specialists(self, symptoms: list[str], available_specialists: list[str]) -> list[str]:
        logger.info("[GeminiProvider] Recommending specialists")
        prompt = self._recommend_prompt.format(
            symptoms=", ".join(symptoms),
            specialists=", ".join(available_specialists),
        )
        raw = self._invoke(prompt)
        return [name.strip() for name in raw.split(",") if name.strip() in available_specialists]

    def generate_response(self, user_message: str, context: str = "") -> str:
        full_prompt = f"You are a compassionate AI medical assistant. Do not diagnose.\n\n"
        if context:
            full_prompt += f"Context: {context}\n\n"
        full_prompt += f"Patient: {user_message}"
        return self._invoke(full_prompt)

    def generate_followup(self, symptoms: list[str]) -> str:
        prompt = self._followup_prompt.format(symptoms=", ".join(symptoms))
        return self._invoke(prompt)

    def call_prompt(self, prompt_name: str, **kwargs) -> str:
        logger.info(f"[GeminiProvider] Calling prompt: {prompt_name}")
        prompt_template = _load_prompt(prompt_name)
        prompt = prompt_template.format(**kwargs)
        return self._invoke(prompt)
