"""
LangGraph agent pipeline for the Healthcare AI Voice Agent.

Nodes:
  normalize_agent          → normalize raw symptom phrases using LLM
  specialist_lookup_agent  → query DB for matching specialists
  recommend_specialists_agent → rank specialists using LLM
  fetch_doctor_details_agent  → retrieve available doctors from DB

Each node owns only the fields it updates in AgentState.
"""
from typing import List, TypedDict
from langgraph.graph import StateGraph, END
from llm.factory import LLMProviderFactory
from repositories import doctor_repository
import logging

logger = logging.getLogger(__name__)

# ─── State ─────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    phrases: List[str]
    normalized_symptoms: List[str]
    specialists: List[str]
    recommended_specialists: List[str]
    doctors: List[dict]

# ─── Node implementations ───────────────────────────────────────────────────────

def normalize_agent(state: AgentState) -> AgentState:
    logger.info("[normalize_agent] Running")
    llm = LLMProviderFactory.create()
    normalized = llm.normalize_symptoms(state["phrases"])
    logger.info(f"[normalize_agent] Normalized: {normalized}")
    return {"normalized_symptoms": normalized}


def specialist_lookup_agent(state: AgentState) -> AgentState:
    logger.info("[specialist_lookup_agent] Running")
    normalized = state.get("normalized_symptoms", [])
    if not normalized:
        return {"specialists": []}
    specialists = doctor_repository.get_specialists_for_symptoms(normalized)
    logger.info(f"[specialist_lookup_agent] Found: {specialists}")
    return {"specialists": specialists}


def recommend_specialists_agent(state: AgentState) -> AgentState:
    logger.info("[recommend_specialists_agent] Running")
    symptoms = state.get("normalized_symptoms", [])
    specialists = state.get("specialists", [])
    if not symptoms or not specialists:
        return {"recommended_specialists": []}
    llm = LLMProviderFactory.create()
    recommended = llm.recommend_specialists(symptoms, specialists)
    logger.info(f"[recommend_specialists_agent] Recommended: {recommended}")
    return {"recommended_specialists": recommended}


def fetch_doctor_details_agent(state: AgentState) -> AgentState:
    logger.info("[fetch_doctor_details_agent] Running")
    recommended = state.get("recommended_specialists", [])
    if not recommended:
        return {"doctors": []}
    doctors = doctor_repository.get_doctors_by_specialists(recommended)
    logger.info(f"[fetch_doctor_details_agent] Found {len(doctors)} doctors")
    return {"doctors": doctors}

# ─── Graph builder ──────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("normalize_agent", normalize_agent)
    builder.add_node("specialist_lookup_agent", specialist_lookup_agent)
    builder.add_node("recommend_specialists_agent", recommend_specialists_agent)
    builder.add_node("fetch_doctor_details_agent", fetch_doctor_details_agent)

    builder.set_entry_point("normalize_agent")
    builder.add_edge("normalize_agent", "specialist_lookup_agent")
    builder.add_edge("specialist_lookup_agent", "recommend_specialists_agent")
    builder.add_edge("recommend_specialists_agent", "fetch_doctor_details_agent")
    builder.add_edge("fetch_doctor_details_agent", END)

    return builder.compile()
