"""
Chat API route — /chat

Proxies conversational messages to the configured LLM provider.
The API key never leaves the server; it is loaded from environment variables only.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from chat_agent import build_chat_graph
import logging

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    history: list[str] = []


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    logger.info(f"[chat] Received message (len={len(request.message)})")
    try:
        graph = build_chat_graph()
        final_state = graph.invoke({
            "message": request.message,
            "history": request.history
        })
        reply = final_state.get("final_reply", "I'm sorry, I couldn't process that.")
        logger.info("[chat] Response generated successfully")
        return ChatResponse(reply=reply)
    except Exception as e:
        logger.error(f"[chat] LLM error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")
