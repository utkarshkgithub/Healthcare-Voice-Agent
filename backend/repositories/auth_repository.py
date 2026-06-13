"""
Auth repository — login and registration database operations.
"""
import logging
from db import pool

logger = logging.getLogger(__name__)

def login_user(email: str, password: str) -> int | None:
    """
    Authenticate a user and return their user_id if successful, else None.
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sp_login_user(%s::TEXT, %s::TEXT)",
                    (email, password),
                )
                user = cur.fetchone()
                return user[0] if user else None
    except Exception as e:
        logger.error(f"[auth_repository] DB error during login: {e}")
        raise

def register_user(name: str, email: str, password: str) -> int | None:
    """
    Register a new user and return their user_id if successful, else None.
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sp_register_user(%s::TEXT, %s::TEXT, %s::TEXT)",
                    (name, email, password),
                )
                result = cur.fetchone()
                conn.commit()
                return result[0] if result else None
    except Exception as e:
        logger.error(f"[auth_repository] DB error during registration: {e}")
        raise
