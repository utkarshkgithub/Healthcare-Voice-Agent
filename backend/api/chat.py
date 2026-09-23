"""
Chat API route — /chat

Proxies conversational messages to the configured LLM provider.
The API key never leaves the server; it is loaded from environment variables only.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from chat_agent import build_chat_graph
import logging

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    history: list[str] = []
    question_rounds: int = 0


class ChatResponse(BaseModel):
    reply: str
    question_rounds: int = 0
    predicted_condition: str = ""
    predicted_additional_symptoms: list[str] = Field(default_factory=list)
    immediate_remedy: str = ""
    prediction_summary: str = ""


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    logger.info(f"[chat] Received message (len={len(request.message)})")
    try:
        graph = build_chat_graph()
        final_state = graph.invoke({
            "message": request.message,
            "history": request.history,
            "question_rounds": request.question_rounds
        })
        reply = final_state.get("final_reply", "I'm sorry, I couldn't process that.")
        qr = final_state.get("question_rounds", 0)
        predicted_condition = final_state.get("predicted_condition", "")
        predicted_additional_symptoms = final_state.get("predicted_additional_symptoms", [])
        immediate_remedy = final_state.get("immediate_remedy", "")
        prediction_summary = final_state.get("prediction_summary", "")
        logger.info("[chat] Response generated successfully")
        return ChatResponse(
            reply=reply,
            question_rounds=qr,
            predicted_condition=predicted_condition,
            predicted_additional_symptoms=predicted_additional_symptoms,
            immediate_remedy=immediate_remedy,
            prediction_summary=prediction_summary,
        )
    except Exception as e:
        logger.error(f"[chat] LLM error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")
