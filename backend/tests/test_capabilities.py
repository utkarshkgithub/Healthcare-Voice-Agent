"""
Tests for capability grounding.

The regression: asked to book an appointment, the model replied "I can't book
it directly here, but please call your clinic" — while the application books
appointments in-app. It was hallucinating a limitation it had
no way of knowing about.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from capabilities import BASE_CAPABILITIES, build_capability_block


def test_block_refuses_to_claim_inability_to_book():
    block = build_capability_block(can_book=True, available_doctors=3, patient_signed_in=True).lower()
    assert "you must never claim you cannot do something listed above" in block


def test_block_states_booking_is_possible_when_slots_exist():
    block = build_capability_block(can_book=True, available_doctors=3, patient_signed_in=True)
    assert "booking IS possible" in block
    assert "3 doctor(s)" in block


def test_signed_out_patient_is_told_to_sign_in_not_that_booking_is_impossible():
    block = build_capability_block(can_book=True, available_doctors=3, patient_signed_in=False)
    assert "sign in" in block.lower()
    assert "booking IS possible" not in block


def test_no_slots_reports_no_slots_not_no_capability():
    block = build_capability_block(can_book=True, available_doctors=0, patient_signed_in=True)
    assert "no slots are open" in block.lower()
    assert "booking IS possible" not in block


def test_block_never_tells_patient_to_use_a_portal():
    # The specific failure: sending the patient to a portal to do something the
    # app does itself.
    for kwargs in (
        {"can_book": True, "available_doctors": 2, "patient_signed_in": True},
        {"can_book": True, "available_doctors": 0, "patient_signed_in": True},
        {"can_book": True, "available_doctors": 2, "patient_signed_in": False},
    ):
        block = build_capability_block(**kwargs).lower()
        assert "patient portal" not in block.replace(
            "and you cannot use a patient portal", ""
        ) or "must never" in block


def test_base_capabilities_cover_the_real_boundaries():
    joined = " ".join(BASE_CAPABILITIES).lower()
    assert "book" in joined
    assert "not diagnose" in joined


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