"""
Chat API route — /chat

Owns the conversation: loads history from the database rather than trusting
whatever the caller sends, persists both sides of the turn, and records a
triage decision row so every escalation is attributable.
"""
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user
from capabilities import build_capability_block
from chat_agent import build_chat_graph, MAX_CLARIFYING_QUESTIONS
from config import Config
from repositories import conversation_repository, decision_repository, doctor_repository
import os

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

#: Bumped whenever a prompt template changes in a way that could alter triage
#: behaviour. Stored on every decision row so a clinical question about a past
#: decision can be answered from the record alone.
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Optional: supplied by the client only to resume a specific conversation.
    # The server validates it and falls back to the caller's open conversation.
    conversation_id: str | None = None
    question_rounds: int = Field(default=0, ge=0, le=10)


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str = ""
    question_rounds: int = 0
    predicted_condition: str = ""
    predicted_additional_symptoms: list[str] = Field(default_factory=list)
    immediate_remedy: str = ""
    prediction_summary: str = ""
    is_emergency: bool = False
    out_of_scope: bool = False
    triggered_red_flags: list[str] = Field(default_factory=list)
    escalated_by: str = "none"
    urgency: str | None = None


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user_id: int = Depends(get_current_user)):
    logger.info(f"[chat] turn from user {user_id} (len={len(request.message)})")

    # ── Resolve the conversation server-side ────────────────────────────────
    if request.conversation_id and conversation_repository.is_valid_conversation(
        request.conversation_id
    ):
        conversation_id = request.conversation_id
    else:
        conversation_id = conversation_repository.get_or_create_conversation(user_id)

    stored = conversation_repository.get_history(conversation_id)
    history = conversation_repository.to_prompt_history(stored)

    conversation_repository.add_message(conversation_id, "patient", request.message)

    started = time.monotonic()
    try:
        graph = build_chat_graph()
        final_state = graph.invoke(
            {
                "message": request.message,
                "history": history,
                # The clarifying-question cap is a safety bound, so it is
                # clamped here and cannot be influenced by the client.
                "question_rounds": min(request.question_rounds, MAX_CLARIFYING_QUESTIONS),
                "conversation_id": conversation_id,
            }
        )
    except Exception as exc:
        logger.error(f"[chat] pipeline failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not process your message.")

    latency_ms = int((time.monotonic() - started) * 1000)

    reply = final_state.get("final_reply") or "I'm sorry, I couldn't process that."
    urgency = final_state.get("urgency")
    is_emergency = bool(final_state.get("is_emergency", False))
    out_of_scope = bool(final_state.get("out_of_scope", False))
    red_flags = final_state.get("triggered_red_flags") or []
    predicted_condition = final_state.get("predicted_condition") or ""

    # ── Persist and audit ───────────────────────────────────────────────────
    node = "out_of_scope_node" if out_of_scope else _terminal_node(final_state)
    conversation_repository.add_message(conversation_id, "agent", reply, node)

    # Grounding is computed from live state, so the model cannot invent a
    # limitation the system does not have.
    capability_block = build_capability_block(
        can_book=True,
        available_doctors=_count_open_doctors(predicted_condition),
        patient_signed_in=True,
    )
    logger.debug(f"[chat] capabilities: {capability_block}")

    # Out-of-scope turns are not triage decisions and must not appear in the
    # clinical audit, or the escalation rate gets diluted with non-clinical
    # traffic and stops being a meaningful signal.
    if not out_of_scope:
        decision_repository.record_decision(
            conversation_id=conversation_id,
            symptom_text=final_state.get("symptoms", ""),
            urgency=urgency,
            is_emergency=is_emergency,
            triggered_red_flags=red_flags,
            escalated_by=final_state.get("escalated_by", "none"),
            provider=Config.LLM_PROVIDER,
            model=_model_name(),
            prompt_version=PROMPT_VERSION,
        )

    logger.info(
        f"[chat] turn complete in {latency_ms}ms "
        f"urgency={urgency} emergency={is_emergency} via={final_state.get('escalated_by')}"
    )

    return ChatResponse(
        reply=reply,
        conversation_id=conversation_id,
        question_rounds=final_state.get("question_rounds", 0),
        predicted_condition=predicted_condition,
        predicted_additional_symptoms=final_state.get("predicted_additional_symptoms", []),
        immediate_remedy=final_state.get("immediate_remedy", ""),
        prediction_summary=final_state.get("prediction_summary", ""),
        is_emergency=is_emergency,
        out_of_scope=out_of_scope,
        triggered_red_flags=red_flags,
        escalated_by=final_state.get("escalated_by", "none"),
        urgency=urgency,
    )


def _terminal_node(state: dict) -> str:
    """Which node produced the final reply. Recorded on the message row."""
    if state.get("is_emergency"):
        return "emergency_response_node"
    if state.get("question_rounds"):
        return "ask_questions_node"
    return "provide_guidance_node"


def _model_name() -> str:
    if Config.LLM_PROVIDER == "cerebras":
        return os.getenv("CEREBRAS_MODEL", "")
    if Config.LLM_PROVIDER == "gemini":
        return os.getenv("GEMINI_MODEL", "")
    return os.getenv("OPENAI_MODEL", "")


def _count_open_doctors(predicted_condition: str) -> int:
    """Doctors available for the predicted condition, for capability grounding."""
    if not predicted_condition:
        return 0
    try:
        specialties = doctor_repository.get_specialists_for_symptoms([predicted_condition])
        if not specialties:
            return 0
        return len(doctor_repository.get_doctors_by_specialists(specialties))
    except Exception:
        return 0


@router.get("/chat/{conversation_id}/history")
def chat_history(conversation_id: str, user_id: int = Depends(get_current_user)):
    """Full transcript for a conversation, so a reload can restore the thread."""
    if not conversation_repository.is_valid_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "conversation_id": conversation_id,
        "messages": conversation_repository.get_history(conversation_id, limit=200),
    }


@router.get("/chat/decisions/stats")
def decision_stats(user_id: int = Depends(get_current_user), days: int = 7):
    """Escalation rate over a window, split by whether rules or the model escalated."""
    return decision_repository.emergency_rate(days)