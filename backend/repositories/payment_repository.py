"""
Payment repository — Razorpay order and payment DB operations.

The database, not the client, is the source of truth for whether money was
taken. A verified signature alone is not enough to book an appointment; the
payment has to be recorded and then re-checked at booking time.
"""
import logging

from db import pool

logger = logging.getLogger(__name__)


def record_order(order_id: str, amount: int, currency: str = "INR") -> int:
    """Record an order at creation time so its amount is server-side."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sp_record_payment_order(%s, %s, %s);",
                (order_id, amount, currency),
            )
            payment_row_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"[payment_repository] Recorded order {order_id}")
            return payment_row_id


def capture_payment(order_id: str, payment_id: str) -> bool:
    """
    Mark an order captured after its signature verified.

    Returns False when the order is unknown, i.e. the signature was valid but
    the order was never created by us.
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sp_capture_payment(%s, %s);", (order_id, payment_id)
            )
            captured = cur.fetchone()[0]
            conn.commit()
            return bool(captured)


def get_payment(payment_id: str) -> dict | None:
    """Return the recorded payment, or None if it was never captured by us."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM sp_get_payment(%s);", (payment_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {"payment_id": row[0], "amount": row[1], "status": row[2]}