"""
Triage service — orchestrates the LangGraph agent pipeline.

This service owns the business logic of running the symptom triage workflow.
Routes delegate here; they never interact with LangGraph directly.
"""
import logging
from langgraph_llm_agents import build_graph

logger = logging.getLogger(__name__)


def run_triage(phrases: list[str]) -> dict:
    """
    Execute the full LangGraph triage pipeline.

    Args:
        phrases: Raw symptom phrases from the patient.

    Returns:
        Dict with keys: phrases, normalized_symptoms, specialists,
        recommended_specialists, doctors.
    """
    logger.info(f"[triage_service] Starting triage with {len(phrases)} phrases")
    graph = build_graph()
    final_state = graph.invoke({"phrases": phrases})

    result = {
        "phrases": final_state.get("phrases", []),
        "normalized_symptoms": final_state.get("normalized_symptoms", []),
        "specialists": final_state.get("specialists", []),
        "recommended_specialists": final_state.get("recommended_specialists", []),
        "doctors": final_state.get("doctors", []),
    }
    logger.info(
        f"[triage_service] Triage complete — "
        f"{len(result['recommended_specialists'])} specialists, "
        f"{len(result['doctors'])} doctors"
    )
    return result
