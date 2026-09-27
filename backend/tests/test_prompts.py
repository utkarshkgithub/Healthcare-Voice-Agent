"""
Tests for prompt templates.

Templates are rendered with str.format, so a literal brace in a prompt — most
easily introduced by pasting a JSON example — is silently parsed as a format
field and raises at runtime. That bug shipped: chat_prediction.md contained an
unescaped JSON object and the prediction node raised KeyError on every call.

These tests render each template the way its caller does, so the failure is
caught here rather than mid-conversation.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm.prompts import PROMPTS_DIR, load_prompt

#: Every placeholder each template is actually called with.
TEMPLATE_ARGS = {
    "normalize": {"phrases": "headache"},
    "recommend": {"symptoms": "chest pain", "specialists": "Cardiology"},
    "chat_extract_symptoms": {"history": "", "message": "my head hurts"},
    "chat_check_emergency": {"symptoms": "chest pain"},
    "chat_check_missing_info": {"history": "", "message": "x", "symptoms": "y"},
    "chat_ask_questions": {
        "history": "", "message": "x", "symptoms": "y", "missing_info": "duration",
    },
    "chat_risk_assessment": {"history": "", "message": "x", "symptoms": "y"},
    "chat_prediction": {
        "history": "", "message": "x", "symptoms": "y", "risk_assessment": "z",
    },
    "chat_guidance": {
        "history": "", "message": "x", "risk_assessment": "z",
        "prediction_summary": "s", "urgency": "Routine",
    },
}


def test_nine_templates_exist():
    templates = sorted(p.stem for p in PROMPTS_DIR.glob("*.md"))
    assert len(templates) == 9, f"expected 9 templates, found {len(templates)}: {templates}"
    assert templates == sorted(TEMPLATE_ARGS), "template set drifted from what callers use"


def test_every_template_renders():
    """The regression: an unescaped { in a template raises at format time."""
    for name, kwargs in TEMPLATE_ARGS.items():
        try:
            rendered = load_prompt(name).format(**kwargs)
        except (KeyError, IndexError, ValueError) as exc:
            raise AssertionError(f"{name}.md failed to format: {exc!r}") from exc
        assert rendered.strip(), f"{name}.md rendered empty"


def test_prediction_template_keeps_json_example_intact():
    """Doubling the braces must survive formatting as a real JSON object."""
    rendered = load_prompt("chat_prediction").format(
        history="", message="x", symptoms="y", risk_assessment="z"
    )
    assert '"predicted_condition"' in rendered
    assert "{{" not in rendered and "}}" not in rendered


def test_unknown_template_raises_loudly():
    try:
        load_prompt("does_not_exist")
    except FileNotFoundError:
        return
    raise AssertionError("missing template must raise, not return empty")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    raise SystemExit(1 if failures else 0)