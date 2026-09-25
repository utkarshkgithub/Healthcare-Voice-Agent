"""
LLM Provider abstract base class.

All LLM providers must implement this interface.
LangGraph nodes call provider methods — never vendor SDKs directly.

Every method here is called by a graph node or a service. Adding a method to
this ABC is a contract change for all vendors, so prompts that are used by
exactly one node live behind call_prompt() as .md templates instead of here.
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
        return the 1-2 most appropriate specialists.
        """
        ...

    @abstractmethod
    def call_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Loads a prompt template by name, formats it with the given kwargs,
        and returns the raw LLM response string.
        """
        ...