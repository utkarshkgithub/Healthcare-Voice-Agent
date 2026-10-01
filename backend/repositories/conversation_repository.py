"""
Conversation repository — conversation and message persistence.

The transcript is owned by the server. The client sends only the conversation
id, so history can neither be lost on reload nor be fabricated by a caller.
"""
import logging
import uuid

from db import pool

logger = logging.getLogger(__name__)


def get_or_create_conversation(user_id: int) -> str:
    """Return the caller's open conversation, creating one if there is none."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT sp_get_or_create_conversation(%s);", (user_id,))
            return str(cur.fetchone()[0])


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    node: str | None = None,
) -> int:
    """Append one message. role must be 'patient' or 'agent' (CHECK enforced)."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sp_add_message(%s, %s, %s, %s);",
                (conversation_id, role, content, node),
            )
            return cur.fetchone()[0]


def get_history(conversation_id: str, limit: int = 20) -> list[dict]:
    """
    Return the most recent messages, oldest first.

    Capped deliberately: the model only needs the recent window, and an
    unbounded transcript is both a cost and an injection surface.
    """
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM sp_get_conversation_history(%s, %s);",
                (conversation_id, limit),
            )
            return [
                {
                    "id": row[0],
                    "role": row[1],
                    "content": row[2],
                    "node": row[3],
                    "created_at": row[4],
                }
                for row in cur.fetchall()
            ]


def close_conversation(conversation_id: str) -> bool:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT sp_close_conversation(%s);", (conversation_id,))
            return bool(cur.fetchone()[0])


def to_prompt_history(messages: list[dict]) -> list[str]:
    """
    Render stored messages in the "Patient: / Assistant: " form the prompts expect.

    The role prefix is applied here rather than trusted from storage, so a
    stored agent message cannot masquerade as a patient instruction.
    """
    lines = []
    for message in messages:
        label = "Patient" if message["role"] == "patient" else "Assistant"
        lines.append(f"{label}: {message['content']}")
    return lines


def is_valid_conversation(conversation_id: str) -> bool:
    """True if the conversation exists. Guards against client-supplied ids."""
    try:
        uuid.UUID(conversation_id)
    except (ValueError, AttributeError, TypeError):
        return False

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM conversations WHERE id = %s;", (conversation_id,))
            return cur.fetchone() is not None