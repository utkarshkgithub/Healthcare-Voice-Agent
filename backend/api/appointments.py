"""
Appointments API routes — /appointments
"""
from fastapi import APIRouter, Depends, HTTPException
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
):
    """
    Books a slot for the authenticated patient.

    The caller must not be able to book on someone else's behalf: the patient
    is resolved from the token, and a mismatch with the request body is
    rejected rather than trusted.
    """
    patient_id = patient_repository.get_patient_id_by_user(user_id)
    if not patient_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    if req.patient_id != patient_id:
        raise HTTPException(
            status_code=403, detail="Cannot book an appointment for another patient."
        )

    logger.info(
        f"[appointments] Creating for patient_id={patient_id} "
        f"doctor_id={req.doctor_id} payment_id={req.payment_id}"
    )
    try:
        appointment_id = appointment_repository.create_appointment(
            patient_id=patient_id,
            doctor_id=req.doctor_id,
            slot_id=req.slot_id,
            reason=req.reason,
            payment_id=req.payment_id,
        )
        return {"message": "Appointment created", "appointment_id": appointment_id}
    except Exception as e:
        # The procedure raises a specific message when the slot was taken
        # between discovery and booking; surface it as a conflict, not a 500.
        detail = str(e)
        if "no longer available" in detail:
            raise HTTPException(status_code=409, detail="That slot was just taken.")
        logger.error(f"[appointments] Creation failed: {e}")
        raise HTTPException(status_code=500, detail="Could not create appointment")
