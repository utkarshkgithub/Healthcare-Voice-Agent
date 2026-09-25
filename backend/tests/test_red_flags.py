"""
Tests for the deterministic red-flag layer.

This layer decides escalation without a model, so it must be reproducible.
Run with:  pytest backend/tests -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from red_flags import detect_red_flags, is_emergency


# Every one of these must escalate.
EMERGENCY_CASES = [
    "severe chest pain radiating to left arm",
    "crushing chest pressure",
    "cannot breathe",
    "struggling to breathe",
    "gasping for air",
    "face drooping and arm weakness",
    "slurred speech started suddenly",
    "left side of body went numb",
    "unconscious and unresponsive",
    "passed out at the stairs",
    "seizure lasting two minutes",
    "uncontrolled bleeding from the wound",
    "throat closing after eating peanuts",
    "swelling of face and lips",
    "I want to kill myself",
    "CHEST PAIN",              # case insensitivity
    "chest  pain",             # whitespace variance
    "Crushing Chest Pressure", # mixed case
]

# None of these may escalate.
NON_EMERGENCY_CASES = [
    "",
    "   ",
    "mild headache",
    "sore throat",
    "runny nose",
    "mild chest discomfort on exertion that settles with rest",  # not acute chest pain
    "feeling tired",
    "itchy rash on arm",
    "lower back pain after gardening",
    "slightly elevated blood pressure",
    "acne",
    "occasional dizziness when standing up",
    "general body ache",
    "mild nausea after eating",
]


def test_emergency_phrases_all_escalate():
    missed = [c for c in EMERGENCY_CASES if not is_emergency(c)]
    assert not missed, f"red flags failed to escalate: {missed}"


def test_non_emergency_phrases_do_not_escalate():
    false_positives = [c for c in NON_EMERGENCY_CASES if is_emergency(c)]
    assert not false_positives, f"false escalations: {false_positives}"


def test_detect_red_flags_returns_names():
    assert "cardiac chest pain" in detect_red_flags("severe chest pain")
    assert "stroke signs" in detect_red_flags("slurred speech")
    assert detect_red_flags("mild headache") == []


def test_multiple_flags_are_all_reported():
    flags = detect_red_flags("chest pain and face drooping")
    assert "cardiac chest pain" in flags
    assert "stroke signs" in flags


def test_empty_input_is_not_an_emergency():
    assert detect_red_flags("") == []
    assert detect_red_flags("   ") == []
    assert not is_emergency("")


if __name__ == "__main__":
    failures = 0
    for fn in (
        test_emergency_phrases_all_escalate,
        test_non_emergency_phrases_do_not_escalate,
        test_detect_red_flags_returns_names,
        test_multiple_flags_are_all_reported,
        test_empty_input_is_not_an_emergency,
    ):
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {fn.__name__}: {exc}")
    raise SystemExit(1 if failures else 0)