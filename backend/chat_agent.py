"""
LangGraph agent pipeline for the conversational triage voice assistant.

This handles the conversational workflow:
- Extract structured symptoms
- Check for emergency red flags
- Determine missing information
- Ask targeted questions
- Assess risk
- Provide general guidance and safety-net advice
"""
from typing import List, TypedDict
from langgraph.graph import StateGraph, END
from providers.llm.factory import LLMProviderFactory
import logging

logger = logging.getLogger(__name__)

# ─── State ─────────────────────────────────────────────────────────────────────

class ChatAgentState(TypedDict):
    message: str
    history: List[str]
    symptoms: str
    is_emergency: bool
    missing_info: str
    risk_assessment: str
    final_reply: str

# ─── Node implementations ───────────────────────────────────────────────────────

def extract_symptoms_node(state: ChatAgentState) -> dict:
    logger.info("[chat_agent] Extracting symptoms")
    llm = LLMProviderFactory.create()
    history_str = "\n".join(state.get("history", []))
    
    symptoms = llm.call_prompt(
        "chat_extract_symptoms", 
        history=history_str, 
        message=state["message"]
    )
    logger.info(f"[chat_agent] Extracted symptoms: {symptoms}")
    return {"symptoms": symptoms}


def check_emergency_node(state: ChatAgentState) -> dict:
    logger.info("[chat_agent] Checking emergency red flags")
    llm = LLMProviderFactory.create()
    
    result = llm.call_prompt(
        "chat_check_emergency", 
        symptoms=state.get("symptoms", "")
    )
    
    is_emergency = "YES" in result.upper()
    logger.info(f"[chat_agent] Emergency: {is_emergency}")
    return {"is_emergency": is_emergency}


def emergency_response_node(state: ChatAgentState) -> dict:
    logger.info("[chat_agent] Generating emergency response")
    reply = (
        "Based on what you've described, this sounds like a medical emergency. "
        "Please hang up and immediately call emergency services or go to the nearest emergency room. "
        "Do not wait."
    )
    return {"final_reply": reply}


def check_missing_info_node(state: ChatAgentState) -> dict:
    logger.info("[chat_agent] Checking missing information")
    llm = LLMProviderFactory.create()
    history_str = "\n".join(state.get("history", []))
    
    result = llm.call_prompt(
        "chat_check_missing_info", 
        history=history_str, 
        message=state["message"],
        symptoms=state.get("symptoms", "")
    )
    
    logger.info(f"[chat_agent] Missing info result: {result}")
    return {"missing_info": result}


def ask_questions_node(state: ChatAgentState) -> dict:
    logger.info("[chat_agent] Asking follow-up questions")
    llm = LLMProviderFactory.create()
    history_str = "\n".join(state.get("history", []))
    
    reply = llm.call_prompt(
        "chat_ask_questions", 
        history=history_str, 
        message=state["message"],
        symptoms=state.get("symptoms", ""),
        missing_info=state.get("missing_info", "")
    )
    
    return {"final_reply": reply}


def risk_assessment_node(state: ChatAgentState) -> dict:
    logger.info("[chat_agent] Performing risk assessment")
    llm = LLMProviderFactory.create()
    history_str = "\n".join(state.get("history", []))
    
    assessment = llm.call_prompt(
        "chat_risk_assessment", 
        history=history_str, 
        message=state["message"],
        symptoms=state.get("symptoms", "")
    )
    
    logger.info(f"[chat_agent] Risk Assessment: {assessment}")
    return {"risk_assessment": assessment}


def provide_guidance_node(state: ChatAgentState) -> dict:
    logger.info("[chat_agent] Providing guidance and safety net")
    llm = LLMProviderFactory.create()
    history_str = "\n".join(state.get("history", []))
    
    reply = llm.call_prompt(
        "chat_guidance", 
        history=history_str, 
        message=state["message"],
        risk_assessment=state.get("risk_assessment", "")
    )
    
    return {"final_reply": reply}

# ─── Conditional Routers ────────────────────────────────────────────────────────

def route_after_emergency_check(state: ChatAgentState) -> str:
    if state.get("is_emergency", False):
        return "emergency"
    return "continue"


def route_after_missing_info_check(state: ChatAgentState) -> str:
    missing = state.get("missing_info", "").upper()
    if "NONE" in missing or not missing.strip():
        return "continue"
    return "ask_questions"


# ─── Graph builder ──────────────────────────────────────────────────────────────

def build_chat_graph():
    builder = StateGraph(ChatAgentState)
    
    # Add nodes
    builder.add_node("extract_symptoms_node", extract_symptoms_node)
    builder.add_node("check_emergency_node", check_emergency_node)
    builder.add_node("emergency_response_node", emergency_response_node)
    builder.add_node("check_missing_info_node", check_missing_info_node)
    builder.add_node("ask_questions_node", ask_questions_node)
    builder.add_node("risk_assessment_node", risk_assessment_node)
    builder.add_node("provide_guidance_node", provide_guidance_node)

    # Set entry
    builder.set_entry_point("extract_symptoms_node")
    
    # Define edges
    builder.add_edge("extract_symptoms_node", "check_emergency_node")
    
    builder.add_conditional_edges(
        "check_emergency_node",
        route_after_emergency_check,
        {
            "emergency": "emergency_response_node",
            "continue": "check_missing_info_node"
        }
    )
    
    builder.add_conditional_edges(
        "check_missing_info_node",
        route_after_missing_info_check,
        {
            "ask_questions": "ask_questions_node",
            "continue": "risk_assessment_node"
        }
    )
    
    builder.add_edge("risk_assessment_node", "provide_guidance_node")
    
    # End edges
    builder.add_edge("emergency_response_node", END)
    builder.add_edge("ask_questions_node", END)
    builder.add_edge("provide_guidance_node", END)

    return builder.compile()
