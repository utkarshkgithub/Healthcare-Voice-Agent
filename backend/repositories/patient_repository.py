"""
Patient repository — all patient-related database operations.
No business logic; only stored procedure calls and result mapping.
"""
from db import pool
import logging

logger = logging.getLogger(__name__)

def get_patient_details(user_id: int) -> dict | None:
    """
    Fetch patient details by user_id.
    Returns a dict matching PatientDetailsResponse fields, or None if not found.
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sp_get_patient_details(%s);", (user_id,))
                row = cur.fetchone()
                logger.info(f"[patient_repository] get_patient_details user_id={user_id} row={row}")
                if not row:
                    return None
                return {
                    "name": row[0],
                    "date_of_birth": row[1],
                    "gender": row[2],
                    "contact_number": row[3],
                    "medical_record_number": row[4],
                    "blood_group": row[5],
                    "marital_status": row[6],
                    "id": row[7],
                }
    except Exception as e:
        logger.error(f"[patient_repository] get_patient_details error: {e}")
        raise

def get_patient_id_by_user(user_id: int) -> int | None:
    """
    Resolve the internal patient_id from a user_id.
    Returns patient_id or None.
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sp_get_patient_id(%s);", (user_id,))
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        logger.error(f"[patient_repository] get_patient_id error: {e}")
        raise
