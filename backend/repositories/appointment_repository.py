"""
Appointment repository — all appointment and doctor slot DB operations.
No business logic; only stored procedure calls and result mapping.
"""
from db import pool
import logging

logger = logging.getLogger(__name__)

def create_appointment(patient_id: int, doctor_id: int, slot_id: int, reason: str, payment_id: str = None) -> int:
    """
    Create an appointment via stored procedure.
    Returns the new appointment_id.
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sp_create_appointment(%s, %s, %s, %s, %s)",
                    (patient_id, doctor_id, slot_id, reason, payment_id),
                )
                appointment_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"[appointment_repository] Created appointment_id={appointment_id} payment_id={payment_id}")
                return appointment_id
    except Exception as e:
        logger.error(f"[appointment_repository] create_appointment error: {e}")
        raise
