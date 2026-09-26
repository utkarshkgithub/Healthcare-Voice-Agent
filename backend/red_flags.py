"""
Deterministic clinical red-flag rules.

This module exists so that the decision to escalate to an emergency does not
depend solely on an LLM. The LLM may escalate; it may never downgrade.

Design rule: this file is deliberately keyword/regex based and free of any
model call. It is a safety net with no probabilistic component, so its
behaviour is testable and reproducible. Clinical review of the pattern list is
required before real deployment.

The asymmetry is intentional. A false positive costs the patient one phone
call; a false negative can cost a life. So the LLM prompt asks it to be
conservative about *what advice to give*, while this layer is deliberately
sensitive about *what to escalate*.
"""
import re

#: Emergency patterns. Each is (name, compiled pattern).
#: Matching is on the raw symptom text produced by the extraction node.
RED_FLAG_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "cardiac chest pain",
        re.compile(
            r"\b(chest\s*(pain|pressure|tightness|heaviness)"
            r"|(?:crushing|squeezing|squeezed|tight|heavy|pressing)\s+chest"
            r"|chest\s+(?:feels\s+)?(?:like\s+(?:it\s+is\s+)?)?"
            r"(?:being\s+)?(?:squeezed|tight|heavy|pressed\s+on)"
            r"|pain\s+in\s+(?:my\s+|the\s+)?chest)\b",
            re.I,
        ),
    ),
    (
        "severe breathlessness",
        re.compile(
            r"\b(cannot\s+breathe|can'?t\s+breathe|unable\s+to\s+breathe"
            r"|struggling\s+to\s+breathe|gasping|severe\s+shortness\s+of\s+breath"
            r"|shortness\s+of\s+breath\s+at\s+rest)\b",
            re.I,
        ),
    ),
    (
        "stroke signs",
        re.compile(
            r"\b((?:face\s+(?:is\s+)?(?:droop\w*|drooping|sagging)"
            r"|(?:my\s+)?(?:speech|talking)\s+(?:is\s+)?(?:slurred|garbled|jumbled)"
            r"|(?:slurred|garbled)\s+(?:speech|talking)"
            r"|sudden\s+(?:confusion|dizziness|weakness)"
            r"|(?:cannot|can't|difficulty|trouble)\s+(?:speak|talk)"
            r"|inability\s+to\s+speak))\b",
            re.I,
        ),
    ),
    (
        "one-sided weakness or numbness",
        re.compile(
            r"\b((?:one|1)[\s-]?(?:sided|side)\s+(?:of\s+)?(?:my|the|his|her|their)?\s*body"
            r"|(?:my\s+)?(?:face|arm|arm|hand|leg|foot)\s+(?:has\s+)?(?:gone\s+)?"
            r"(?:weak|numb|tingl\w*|paralysed|paralyzed)"
            r"|(?:left|right)[\s-]?(?:arm|leg|hand|foot|side)"
            r"|hemiparesis|hemiplegia)\b",
            re.I,
        ),
    ),
    (
        "thunderclap headache",
        re.compile(
            r"\b((?:sudden|worst|severe)\s+(?:severe\s+|worst\s+)?headache"
            r"|thunderclap"
            r"|worst\s+headache\s+(?:of\s+my\s+life|i'?ve\s+ever\s+had))\b",
            re.I,
        ),
    ),
    (
        "loss of consciousness",
        re.compile(
            r"\b(loss\s+of\s+consciousness|unconscious|unresponsive"
            r"|passed\s+out|fainted|fainting|black(ed)?\s+out)\b",
            re.I,
        ),
    ),
    (
        "seizure",
        re.compile(r"\b(seizure|seizing|convulsion|convulsing|fit\s+attack)\b", re.I),
    ),
    (
        "uncontrolled bleeding",
        re.compile(
            r"\b(uncontrolled\s+bleeding|heavy\s+bleeding|haemorrhage|hemorrhage"
            r"|bleeding\s+that\s+(?:won'?t|will\s+not)\s+stop"
            r"|blood\s+(?:that\s+)?(?:keeps?|won'?t|will\s+not)\s+(?:coming|stop\w*)"
            r"|bleeding\s+(?:heavily|a\s+lot))\b",
            re.I,
        ),
    ),
    (
        "anaphylaxis",
        re.compile(
            r"\b(anaphyla(is|xis)|throat\s+(is\s+)?(closing|swelling|tightening)"
            r"|tongue\s+swelling|swelling\s+of\s+(the\s+)?(face|throat|lips))\b",
            re.I,
        ),
    ),
    (
        "severe allergic reaction",
        re.compile(
            r"\b(severe\s+allergic\s+reaction|allergic\s+reaction\s+with\s+"
            r"(difficulty\s+breathing|swelling))\b",
            re.I,
        ),
    ),
    (
        "suicidal ideation",
        re.compile(
            r"\b(suicid(e|al)|kill\s+myself|end\s+my\s+life|harm\s+myself"
            r"|self[\s-]?harm)\b",
            re.I,
        ),
    ),
]


def detect_red_flags(symptoms: str) -> list[str]:
    """
    Return the names of every red flag present in the symptom text.

    Args:
        symptoms: Raw symptom text from the extraction node.

    Returns:
        Names of matched red flags, in declaration order. Empty when none match.
    """
    if not symptoms or not symptoms.strip():
        return []

    return [name for name, pattern in RED_FLAG_PATTERNS if pattern.search(symptoms)]


def is_emergency(symptoms: str) -> bool:
    """True if any deterministic red flag is present."""
    return bool(detect_red_flags(symptoms))