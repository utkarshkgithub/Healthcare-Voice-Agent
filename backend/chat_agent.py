"""
LangGraph agent pipeline for the conversational triage voice assistant.

This handles the conversational workflow:
- Extract structured symptoms
- Check for emergency red flags
- Determine missing information
- Ask targeted questions
- Assess risk
- Predict the likely condition, related symptoms, and immediate remedy
- Provide general guidance and safety-net advice
"""
import json
import re
from typing import List, TypedDict
from langgraph.graph import StateGraph, END
from llm.factory import LLMProviderFactory
import logging

logger = logging.getLogger(__name__)

#: How many clarifying questions the agent may ask before it must give guidance.
#: Bounded deliberately: an unbounded triage questionnaire never terminates, and
#: a patient who is actually an emergency gets interrogated instead of referred.
MAX_CLARIFYING_QUESTIONS = 1

# ─── State ─────────────────────────────────────────────────────────────────────

class ChatAgentState(TypedDict):
    message: str
    history: List[str]
    symptoms: str
    is_emergency: bool
    missing_info: str
    risk_assessment: str
    predicted_condition: str
    predicted_additional_symptoms: List[str]
    immediate_remedy: str
    prediction_summary: str
    final_reply: str
    question_rounds: int


def _parse_prediction_payload(raw: str) -> dict:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S | re.I)
    if fenced:
        text = fenced.group(1).strip()
    else:
        object_match = re.search(r"\{.*\}", text, re.S)
        if object_match:
            text = object_match.group(0).strip()

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        logger.warning("[chat_agent] Prediction payload was not valid JSON")
        return {}

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
    
    return {"final_reply": reply, "question_rounds": state.get("question_rounds", 0) + 1}


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


def generate_prediction_node(state: ChatAgentState) -> dict:
    logger.info("[chat_agent] Generating symptom-based prediction")
    llm = LLMProviderFactory.create()
    history_str = "\n".join(state.get("history", []))

    raw_prediction = llm.call_prompt(
        "chat_prediction",
        history=history_str,
        message=state["message"],
        symptoms=state.get("symptoms", ""),
        risk_assessment=state.get("risk_assessment", ""),
    )

    payload = _parse_prediction_payload(raw_prediction)
    predicted_condition = str(
        payload.get("predicted_condition")
        or payload.get("likely_condition")
        or payload.get("condition")
        or "Unclear"
    ).strip()

    additional_symptoms = payload.get("predicted_additional_symptoms")
    if additional_symptoms is None:
        additional_symptoms = payload.get("additional_symptoms")
    if isinstance(additional_symptoms, str):
        additional_symptoms = [part.strip() for part in additional_symptoms.split(",") if part.strip()]
    elif not isinstance(additional_symptoms, list):
        additional_symptoms = []

    normalized_additional_symptoms = [str(item).strip() for item in additional_symptoms if str(item).strip()]
    immediate_remedy = str(payload.get("immediate_remedy") or payload.get("remedy") or "").strip()

    summary_parts = [f"Likely condition: {predicted_condition}."]
    if normalized_additional_symptoms:
        summary_parts.append(f"Additional symptoms: {', '.join(normalized_additional_symptoms)}.")
    if immediate_remedy:
        summary_parts.append(f"Immediate remedy: {immediate_remedy}.")

    prediction_summary = " ".join(summary_parts).strip()
    logger.info(f"[chat_agent] Prediction summary: {prediction_summary}")

    return {
        "predicted_condition": predicted_condition,
        "predicted_additional_symptoms": normalized_additional_symptoms,
        "immediate_remedy": immediate_remedy,
        "prediction_summary": prediction_summary,
    }


def provide_guidance_node(state: ChatAgentState) -> dict:
    logger.info("[chat_agent] Providing guidance and safety net")
    llm = LLMProviderFactory.create()
    history_str = "\n".join(state.get("history", []))
    
    reply = llm.call_prompt(
        "chat_guidance", 
        history=history_str, 
        message=state["message"],
        risk_assessment=state.get("risk_assessment", ""),
        prediction_summary=state.get("prediction_summary", "")
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
    if state.get("question_rounds", 0) >= MAX_CLARIFYING_QUESTIONS:
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
    builder.add_node("generate_prediction_node", generate_prediction_node)
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
    
    builder.add_edge("risk_assessment_node", "generate_prediction_node")
    builder.add_edge("generate_prediction_node", "provide_guidance_node")
    
    # End edges
    builder.add_edge("emergency_response_node", END)
    builder.add_edge("ask_questions_node", END)
    builder.add_edge("provide_guidance_node", END)

    return builder.compile()
