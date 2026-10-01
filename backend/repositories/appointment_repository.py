"""
Appointment repository — appointment and slot DB operations.
No business logic; only stored procedure calls and result mapping.
"""
import logging

from db import pool

logger = logging.getLogger(__name__)


def create_appointment(
    patient_id: int, doctor_id: int, slot_id: int, reason: str
) -> int:
    """
    Create an appointment via stored procedure.
    Returns the new appointment_id.
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM sp_create_appointment(%s, %s, %s, %s);",
                (patient_id, doctor_id, slot_id, reason),
            )
            appointment_id = cur.fetchone()[0]
            conn.commit()
            logger.info(
                f"[appointment_repository] Created appointment_id={appointment_id}"
            )
            return appointment_id


def get_idempotent_appointment(key: str) -> int | None:
    """Appointment previously created under this Idempotency-Key, if any."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT sp_get_idempotent_appointment(%s);", (key,))
            row = cur.fetchone()
            return row[0] if row and row[0] is not None else None


def record_idempotency_key(key: str, user_id: int, appointment_id: int) -> None:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sp_record_idempotency_key(%s, %s, %s);",
                (key, user_id, appointment_id),
            )
            conn.commit()