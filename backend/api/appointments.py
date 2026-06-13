"""
Appointments API routes — /appointments
"""
from fastapi import APIRouter, HTTPException
from models import AppointmentRequest
from repositories import appointment_repository
import logging

router = APIRouter(tags=["appointments"])
logger = logging.getLogger(__name__)


@router.post("/appointments")
def create_appointment(req: AppointmentRequest):
    logger.info(f"[appointments] Creating for patient_id={req.patient_id} doctor_id={req.doctor_id} payment_id={req.payment_id}")
    try:
        appointment_id = appointment_repository.create_appointment(
            patient_id=req.patient_id,
            doctor_id=req.doctor_id,
            slot_id=req.slot_id,
            reason=req.reason,
            payment_id=req.payment_id,
        )
        return {"message": "Appointment created", "appointment_id": appointment_id}
    except Exception as e:
        logger.error(f"[appointments] Creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
