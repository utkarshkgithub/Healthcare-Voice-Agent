"""
Tests for the graph routers and the prediction payload parser.

These are the pieces that decide whether a patient gets referred or kept
questioning, and they are pure functions, so they are tested without a model.
Run with:  pytest backend/tests -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chat_agent import (
    MAX_CLARIFYING_QUESTIONS,
    route_after_emergency_check,
    route_after_missing_info_check,
    route_after_risk_assessment,
    route_after_symptom_extraction,
    _parse_prediction_payload,
    _parse_urgency,
)


# ─── Scope gate ──────────────────────────────────────────────────────────
# The regression: every input used to fall through to the missing-info node,
# which asked about symptom duration in response to "who is the president of
# america" and "what is 2+2".

def test_no_symptoms_is_out_of_scope():
    assert route_after_symptom_extraction({"symptoms": "NONE"}) == "out_of_scope"


def test_blank_symptoms_is_out_of_scope():
    assert route_after_symptom_extraction({"symptoms": ""}) == "out_of_scope"
    assert route_after_symptom_extraction({"symptoms": "   "}) == "out_of_scope"
    assert route_after_symptom_extraction({"symptoms": "none"}) == "out_of_scope"
    assert route_after_symptom_extraction({}) == "out_of_scope"


def test_real_symptoms_stay_in_scope():
    for symptoms in ("chest pain", "fever, cough", "NONE BUT REAL"):
        if symptoms.upper() == "NONE" or symptoms.strip().upper() == "NONE":
            continue
        assert route_after_symptom_extraction({"symptoms": symptoms}) == "in_scope"


def test_symptom_list_containing_none_word_is_in_scope():
    # "None" as a standalone token only counts when it is the whole answer.
    assert route_after_symptom_extraction({"symptoms": "chest pain, none"}) == "in_scope"


def test_emergency_check_routes_to_emergency():
    assert route_after_emergency_check({"is_emergency": True}) == "emergency"


def test_non_emergency_continues():
    assert route_after_emergency_check({"is_emergency": False}) == "continue"
    assert route_after_missing_info_check({"missing_info": "NONE"}) == "continue"


# ─── The clarifying-question cap ───────────────────────────────────────────
# The full matrix of (is information missing) x (rounds so far). The bug this
# guards against was the counter never surviving between turns, so the
# "rounds = 0" row is the one that regressed in production code.


def test_asks_a_question_when_info_missing_and_no_rounds_yet():
    state = {"missing_info": "duration", "question_rounds": 0}
    assert route_after_missing_info_check(state) == "ask_questions"


def test_never_asks_more_than_the_cap():
    for rounds in range(MAX_CLARIFYING_QUESTIONS, 10):
        state = {"missing_info": "duration", "question_rounds": rounds}
        assert (
            route_after_missing_info_check(state) == "continue"
        ), f"asked a {rounds + 1}th question"


def test_empty_missing_info_continues():
    assert route_after_missing_info_check({"missing_info": "", "question_rounds": 0}) == "continue"


# ─── Prediction payload parsing ───────────────────────────────────────────


def test_parses_clean_json():
    assert _parse_prediction_payload('{"predicted_condition": "Migraine"}') == {
        "predicted_condition": "Migraine"
    }


def test_strips_markdown_fence():
    raw = '```json\n{"predicted_condition": "Flu"}\n```'
    assert _parse_prediction_payload(raw) == {"predicted_condition": "Flu"}


def test_strips_bare_fence():
    raw = '```\n{"predicted_condition": "Flu"}\n```'
    assert _parse_prediction_payload(raw) == {"predicted_condition": "Flu"}


def test_recovers_object_from_surrounding_prose():
    raw = 'Sure! Here you go: {"predicted_condition": "Gastritis"} hope that helps'
    assert _parse_prediction_payload(raw) == {"predicted_condition": "Gastritis"}


def test_malformed_json_degrades_to_empty_not_raises():
    assert _parse_prediction_payload("I cannot help with that") == {}
    assert _parse_prediction_payload("") == {}
    assert _parse_prediction_payload("[1,2,3]") == {}


def test_json_array_is_not_treated_as_object():
    assert _parse_prediction_payload('["a","b"]') == {}


# ─── Urgency parsing and routing ──────────────────────────────────────────


def test_parses_each_urgency_level():
    for level in ("Routine", "Urgent", "Emergency"):
        text = f"Urgency: {level}\nIllness Category: viral\nConfidence: High"
        assert _parse_urgency(text) == level


def test_urgency_parsing_is_case_insensitive():
    assert _parse_urgency("urgency: routine") == "Routine"


def test_unparseable_assessment_escalates_rather_than_assumes_routine():
    # Defaulting to Routine would silently drop the "see a clinician" advice.
    assert _parse_urgency("I think it might be nothing serious") == "Urgent"
    assert _parse_urgency("") == "Urgent"


def test_emergency_urgency_routes_to_hard_stop():
    assert route_after_risk_assessment({"urgency": "Emergency"}) == "escalate"


def test_non_emergency_urgency_continues_to_prediction():
    assert route_after_risk_assessment({"urgency": "Urgent"}) == "continue"
    assert route_after_risk_assessment({"urgency": "Routine"}) == "continue"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(list(globals().items())):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    raise SystemExit(1 if failures else 0)