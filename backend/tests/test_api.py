"""
Integration tests for the API surface.

These run against the real application and a real PostgreSQL database, because
the bugs worth catching here (IDOR, null handling, status codes) only appear
once the router, the response model and the stored procedures are wired
together.

DATABASE_URL must point at a database built from backend/schema.sql.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

if not os.getenv("DATABASE_URL"):
    pytest.skip("DATABASE_URL not set", allow_module_level=True)

from main import app  # noqa: E402  (import after the env guard)
from repositories import payment_repository  # noqa: E402

client = TestClient(app)


def _any_open_slot(doctor_id: int) -> int:
    """First unbooked slot for a doctor, so booking tests do not collide."""
    with payment_repository.pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM appointment_slots
                WHERE doctor_id = %s AND is_booked = FALSE AND slot_date >= CURRENT_DATE
                ORDER BY slot_date, start_time LIMIT 1
                """,
                (doctor_id,),
            )
            row = cur.fetchone()
    assert row, "no open slots seeded"
    return row[0]


@pytest.fixture
def account():
    """Register a unique account and return (headers, user_id, patient_id)."""
    import uuid

    email = f"test-{uuid.uuid4().hex[:12]}@example.com"
    response = client.post(
        "/auth/register",
        json={"name": "Test Patient", "email": email, "password": "strongpass123"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return (
        {"Authorization": f"Bearer {body['access_token']}"},
        body["user_id"],
        body["patient_id"],
    )


# ─── Authentication ───────────────────────────────────────────────────────


def test_patient_details_requires_authentication():
    """The IDOR: patient records must not be readable without a token."""
    response = client.get("/patient-details")
    assert response.status_code == 401


def test_old_style_path_parameter_is_gone(account):
    """Identity must come from the token, not from a URL."""
    headers, user_id, _ = account
    response = client.get(f"/patient-details/{user_id}", headers=headers)
    assert response.status_code == 404


def test_forged_token_is_rejected(account):
    headers, _, _ = account
    forged = dict(headers)
    forged["Authorization"] = headers["Authorization"][:-4] + "AAAA"
    assert client.get("/patient-details", headers=forged).status_code == 401


def test_medical_history_requires_authentication():
    assert client.get("/medical-history").status_code == 401


def test_auth_me_resolves_from_token(account):
    headers, user_id, _ = account
    body = client.get("/auth/me", headers=headers).json()
    assert body["user_id"] == user_id


# ─── Patient data ─────────────────────────────────────────────────────────


def test_patient_details_returns_row_with_null_demographics(account):
    """
    A freshly registered patient has NULL blood group, gender and so on.
    These used to be declared non-null, which turned every such row into a 500.
    """
    headers, _, _ = account
    response = client.get("/patient-details", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Test Patient"
    assert body["medical_record_number"].startswith("MRN-")


def test_medical_history_returns_record(account):
    headers, _, _ = account
    response = client.get("/medical-history", headers=headers)
    assert response.status_code == 200, response.text


# ─── Booking authorisation ────────────────────────────────────────────────


def test_cannot_book_for_another_patient(account):
    headers, _, _ = account
    response = client.post(
        "/appointments",
        headers=headers,
        json={"patient_id": 1, "doctor_id": 1, "slot_id": 1, "reason": "test"},
    )
    assert response.status_code == 403


def test_booking_requires_authentication():
    response = client.post(
        "/appointments",
        json={"patient_id": 1, "doctor_id": 1, "slot_id": 1, "reason": "test"},
    )
    assert response.status_code == 401


def test_booking_without_payment_is_rejected(account):
    """The slot is still bookable, but money must have been captured first."""
    headers, _, patient_id = account
    response = client.post(
        "/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "doctor_id": 1,
            "slot_id": _any_open_slot(1),
            "reason": "test",
        },
    )
    assert response.status_code == 402


def test_booking_with_forged_payment_id_is_rejected(account):
    """A payment_id the server never recorded must not book anything."""
    headers, _, patient_id = account
    response = client.post(
        "/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "doctor_id": 1,
            "slot_id": _any_open_slot(1),
            "reason": "test",
            "payment_id": "pay_definitely_not_real",
        },
    )
    assert response.status_code == 402


def test_booking_with_captured_payment_succeeds(account):
    headers, _, patient_id = account
    import uuid

    order_id = f"order-{uuid.uuid4().hex[:10]}"
    payment_id = f"pay-{uuid.uuid4().hex[:10]}"

    payment_repository.record_order(order_id, 80000)
    assert payment_repository.capture_payment(order_id, payment_id)

    response = client.post(
        "/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "doctor_id": 1,
            "slot_id": _any_open_slot(1),
            "reason": "test booking",
            "payment_id": payment_id,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["appointment_id"]


def test_slot_cannot_be_booked_twice(account):
    """Second booking of the same slot must be a conflict, not a second row."""
    headers, _, patient_id = account
    import uuid

    def paid_slot():
        order_id = f"order-{uuid.uuid4().hex[:10]}"
        payment_id = f"pay-{uuid.uuid4().hex[:10]}"
        payment_repository.record_order(order_id, 80000)
        payment_repository.capture_payment(order_id, payment_id)
        return payment_id

    slot_id = _any_open_slot(2)
    first = client.post(
        "/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "doctor_id": 2,
            "slot_id": slot_id,
            "reason": "first",
            "payment_id": paid_slot(),
        },
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "doctor_id": 2,
            "slot_id": slot_id,
            "reason": "second",
            "payment_id": paid_slot(),
        },
    )
    assert second.status_code == 409


# ─── Registration edge cases ──────────────────────────────────────────────


def test_duplicate_registration_is_conflict_not_server_error():
    import uuid

    email = f"dupe-{uuid.uuid4().hex[:12]}@example.com"
    payload = {"name": "First", "email": email, "password": "strongpass123"}
    assert client.post("/auth/register", json=payload).status_code == 201

    second = client.post("/auth/register", json=payload)
    assert second.status_code == 409
    assert "already registered" in second.json()["detail"].lower()


def test_weak_password_is_rejected():
    response = client.post(
        "/auth/register",
        json={"name": "X", "email": "weak@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_login_with_wrong_password_is_unauthorized():
    import uuid

    email = f"login-{uuid.uuid4().hex[:12]}@example.com"
    client.post(
        "/auth/register",
        json={"name": "Test", "email": email, "password": "strongpass123"},
    )
    response = client.post("/auth/login", json={"email": email, "password": "wrongpass"})
    assert response.status_code == 401


# ─── Specialist mapping ───────────────────────────────────────────────────


@pytest.fixture
def stub_llm(monkeypatch):
    """
    Replace the LLM with a deterministic stub.

    The provider abstraction exists precisely so the graph can be exercised
    without network calls or an API key. Stubbing normalize/recommend keeps
    these tests focused on the database mapping they are actually asserting.
    """
    import llm.factory as factory

    class StubProvider:
        def normalize_symptoms(self, phrases):
            return [p.strip().lower() for p in phrases]

        def recommend_specialists(self, symptoms, available_specialists):
            # Always prefer Cardiology when it is on offer, else the first one.
            if "Cardiology" in available_specialists:
                return ["Cardiology"]
            return available_specialists[:1]

    monkeypatch.setattr(factory.LLMProviderFactory, "create", staticmethod(StubProvider))


def test_specialist_mapping_maps_symptoms_to_specialty(stub_llm):
    response = client.post(
        "/run_langgraph", json={"phrases": ["chest pain", "palpitations"]}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "Cardiology" in body["specialists"]
    assert body["recommended_specialists"] == ["Cardiology"]
    assert len(body["doctors"]) > 0
    doctor = body["doctors"][0]
    # Every doctor must carry a real bookable slot.
    assert doctor["slot_id"] is not None
    assert doctor["next_available_date"]


def test_unknown_symptom_returns_no_specialists(stub_llm):
    response = client.post("/run_langgraph", json={"phrases": ["quantum flux"]})
    assert response.status_code == 200
    assert response.json()["specialists"] == []


def test_empty_phrases_is_rejected():
    assert client.post("/run_langgraph", json={"phrases": []}).status_code == 400


# ─── Observability ────────────────────────────────────────────────────────


def test_every_response_carries_a_request_id():
    response = client.get("/")
    assert response.headers["X-Request-ID"]


def test_errors_do_not_leak_internals():
    response = client.get("/patient-details")
    body = response.json()
    assert "Traceback" not in response.text
    assert set(body) == {"detail"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))