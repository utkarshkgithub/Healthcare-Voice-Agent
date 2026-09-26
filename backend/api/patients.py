"""
Patient API routes — /patient-details, /medical-history

Both resolve identity from the bearer token. There is deliberately no
/user_id path parameter: accepting one is what made the previous version an
IDOR, where guessing an integer returned another patient's medical records.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder

from auth import get_current_user
from models import PatientDetailsResponse, MedicalHistoryResponse
from repositories import medical_history_repository, patient_repository

router = APIRouter(tags=["patients"])
logger = logging.getLogger(__name__)


@router.get("/patient-details", response_model=PatientDetailsResponse)
def get_patient_details(user_id: int = Depends(get_current_user)):
    logger.info(f"[patients] Fetching details for user_id={user_id}")
    row = patient_repository.get_patient_details(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")
    return jsonable_encoder(row)


@router.get("/medical-history", response_model=MedicalHistoryResponse)
def get_medical_history(user_id: int = Depends(get_current_user)):
    logger.info(f"[patients] Fetching medical history for user_id={user_id}")
    patient_id = patient_repository.get_patient_id_by_user(user_id)
    if not patient_id:
        raise HTTPException(status_code=404, detail="Patient not found")
    history = medical_history_repository.get_medical_history(patient_id)
    if not history:
        raise HTTPException(status_code=404, detail="Medical history not found")
    return jsonable_encoder(history)