"""
LLM Provider abstract base class.

All LLM providers must implement this interface.
LangGraph nodes call provider methods — never vendor SDKs directly.
"""
from abc import ABC, abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    def normalize_symptoms(self, phrases: list[str]) -> list[str]:
        """
        Given raw patient phrases, return a list of normalized clinical symptom terms.
        """
        ...

    @abstractmethod
    def recommend_specialists(self, symptoms: list[str], available_specialists: list[str]) -> list[str]:
        """
        Given normalized symptoms and a list of available specialist categories,
        return the 1–2 most appropriate specialists.
        """
        ...

    @abstractmethod
    def generate_response(self, user_message: str, context: str = "") -> str:
        """
        Generate a conversational response to a user message.
        Optional context can be passed to ground the response.
        """
        ...

    @abstractmethod
    def generate_followup(self, symptoms: list[str]) -> str:
        """
        Generate a follow-up question to gather more symptom information.
        """
        ...

    @abstractmethod
    def call_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Loads a prompt template by name, formats it with the given kwargs,
        and returns the raw LLM response string.
        """
        ...
