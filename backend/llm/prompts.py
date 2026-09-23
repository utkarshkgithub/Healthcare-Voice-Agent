"""
Prompt template loading.

Prompts live as .md files in backend/prompts/ so they can be reviewed in a
diff and edited without a deploy. This module is the single place that knows
where they live and how to read them.
"""
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """
    Load a prompt template by name (e.g. "chat_extract_symptoms").

    Raises:
        FileNotFoundError: if the template does not exist. Failing loudly
            matters here — a missing template is a deployment bug, not a
            condition to paper over with a default.
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")