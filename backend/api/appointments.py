"""
Appointments API routes — /appointments
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from auth import get_current_user
from models import AppointmentRequest
from repositories import appointment_repository, patient_repository
import logging

router = APIRouter(tags=["appointments"])
logger = logging.getLogger(__name__)


@router.post("/appointments")
def create_appointment(
    req: AppointmentRequest,
    user_id: int = Depends(get_current_user),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """
    Books a slot for the authenticated patient.

    The caller must not be able to book on someone else's behalf: the patient
    is resolved from the token, and a mismatch with the request body is
    rejected rather than trusted.

    An Idempotency-Key makes a retry safe. Without one, a client that times
    out and retries creates two appointments for one slot.
    """
    patient_id = patient_repository.get_patient_id_by_user(user_id)
    if not patient_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    if req.patient_id != patient_id:
        raise HTTPException(
            status_code=403, detail="Cannot book an appointment for another patient."
        )

    # Replay protection: return the original appointment instead of booking again.
    if idempotency_key:
        existing = appointment_repository.get_idempotent_appointment(idempotency_key)
        if existing:
            logger.info(
                f"[appointments] Replay of {idempotency_key} -> appointment {existing}"
            )
            return {"message": "Appointment already created", "appointment_id": existing}

    logger.info(
        f"[appointments] Creating for patient_id={patient_id} doctor_id={req.doctor_id}"
    )
    try:
        appointment_id = appointment_repository.create_appointment(
            patient_id=patient_id,
            doctor_id=req.doctor_id,
            slot_id=req.slot_id,
            reason=req.reason,
        )
    except Exception as e:
        # The procedure raises a specific message when the slot was taken
        # between discovery and booking; surface it as a conflict, not a 500.
        detail = str(e)
        if "no longer available" in detail:
            raise HTTPException(status_code=409, detail="That slot was just taken.")
        logger.error(f"[appointments] Creation failed: {e}")
        raise HTTPException(status_code=500, detail="Could not create appointment")

    if idempotency_key:
        appointment_repository.record_idempotency_key(
            idempotency_key, user_id, appointment_id
        )

    return {"message": "Appointment created", "appointment_id": appointment_id}