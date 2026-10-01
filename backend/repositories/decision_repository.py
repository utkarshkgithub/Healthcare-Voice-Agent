"""
Triage decision repository — the compliance audit trail.

Every triage run writes one row. Without this, "why was this patient escalated"
cannot be answered after the fact, and a prompt edit can change clinical
behaviour with nothing recording that it happened.
"""
import logging

from db import pool

logger = logging.getLogger(__name__)


def record_decision(
    conversation_id: str | None,
    symptom_text: str,
    urgency: str | None,
    is_emergency: bool,
    triggered_red_flags: list[str],
    escalated_by: str,
    provider: str,
    model: str,
    prompt_version: str,
) -> int | None:
    """
    Persist one triage decision.

    Never raises: losing the audit row must not take down the clinical response.
    Returns the decision id, or None if the write failed.
    """
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT sp_record_triage_decision(%s, %s, %s, %s, %s, %s, %s, %s, %s);",
                    (
                        conversation_id,
                        symptom_text,
                        urgency,
                        is_emergency,
                        triggered_red_flags,
                        escalated_by,
                        provider,
                        model,
                        prompt_version,
                    ),
                )
                decision_id = cur.fetchone()[0]
                conn.commit()
                return decision_id
    except Exception as exc:
        # Deliberately swallowed and logged: the patient still needs an answer
        # even if the audit store is unavailable.
        logger.error(f"[decision_repository] record_decision failed: {exc}")
        return None


def get_decisions(conversation_id: str) -> list[dict]:
    """All triage decisions for a conversation, oldest first."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symptom_text, urgency, is_emergency, triggered_red_flags,
                       escalated_by, provider, model, prompt_version, created_at
                FROM triage_decisions
                WHERE conversation_id = %s
                ORDER BY id ASC
                """,
                (conversation_id,),
            )
            return [
                {
                    "symptom_text": r[0],
                    "urgency": r[1],
                    "is_emergency": r[2],
                    "triggered_red_flags": r[3],
                    "escalated_by": r[4],
                    "provider": r[5],
                    "model": r[6],
                    "prompt_version": r[7],
                    "created_at": r[8],
                }
                for r in cur.fetchall()
            ]


def emergency_rate(days: int = 7) -> dict:
    """
    Escalation rate over a window. A sudden change means either a prompt
    regression or a real-world signal, and both need to be visible.
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE is_emergency) AS emergencies,
                       count(*) FILTER (WHERE urgency = 'Urgent') AS urgent,
                       count(*) FILTER (WHERE escalated_by = 'rules') AS by_rules,
                       count(*) FILTER (WHERE escalated_by = 'llm') AS by_llm
                FROM triage_decisions
                WHERE created_at > now() - make_interval(days => %s)
                """,
                (days,),
            )
            row = cur.fetchone()
            total = row[0] or 0
            return {
                "window_days": days,
                "total": total,
                "emergencies": row[1] or 0,
                "urgent": row[2] or 0,
                "escalated_by_rules": row[3] or 0,
                "escalated_by_llm": row[4] or 0,
                "emergency_rate": (row[1] or 0) / total if total else 0.0,
            }