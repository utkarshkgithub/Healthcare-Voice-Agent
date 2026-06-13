"""
Doctor repository — doctor lookup and specialist mapping DB operations.
"""
from db import pool
import logging

logger = logging.getLogger(__name__)

def get_specialists_for_symptoms(normalized_symptoms: list[str]) -> list[str]:
    """
    Returns matching specialist categories for a list of normalized symptoms.
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sp_get_specialists(%s)", (normalized_symptoms,))
                specialists = [row[0] for row in cur.fetchall()]
                logger.info(f"[doctor_repository] Specialists for {normalized_symptoms}: {specialists}")
                return specialists
    except Exception as e:
        logger.error(f"[doctor_repository] get_specialists error: {e}")
        return []

def get_doctors_by_specialists(recommended: list[str]) -> list[dict]:
    """
    Returns available doctors and their next appointment slots
    for the given specialist categories.
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sp_get_doctors_by_specialists(%s)", (recommended,))
                rows = cur.fetchall()
                doctors = []
                for row in rows:
                    doctors.append({
                        "doctor_id": row[0],
                        "name": row[1],
                        "specialization": row[2],
                        "rating": float(row[3]),
                        "fees": int(row[4]) if row[4] else 0,
                        "hospital": row[5],
                        "next_available_date": str(row[6]) if row[6] else "Not available",
                        "start_time": str(row[7]) if row[7] else "N/A",
                        "end_time": str(row[8]) if row[8] else "N/A",
                        "slot_id": row[9],
                    })
                logger.info(f"[doctor_repository] Found {len(doctors)} doctors for {recommended}")
                return doctors
    except Exception as e:
        logger.error(f"[doctor_repository] get_doctors error: {e}")
        return []
