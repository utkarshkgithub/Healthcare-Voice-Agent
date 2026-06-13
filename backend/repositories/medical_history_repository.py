"""
Medical history repository — handles fetching medical history records.
"""
from db import pool
import logging

logger = logging.getLogger(__name__)

def get_medical_history(patient_id: int) -> dict | None:
    """
    Fetch medical history by patient_id.
    Returns a dict matching MedicalHistoryResponse fields, or None.
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sp_get_medical_history(%s);", (patient_id,))
                row = cur.fetchone()
                logger.info(f"[medical_history_repository] get_medical_history patient_id={patient_id} row={row}")
                if not row:
                    return None
                return {
                    "past_diagnoses": row[0],
                    "surgeries": row[1],
                    "hospital_admissions": row[2],
                    "immunization_records": row[3],
                    "family_medical_history": row[4],
                    "lifestyle_factors": row[5],
                }
    except Exception as e:
        logger.error(f"[medical_history_repository] get_medical_history error: {e}")
        raise
