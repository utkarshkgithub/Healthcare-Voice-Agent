"""
Triage API routes — /run_langgraph
"""
from fastapi import APIRouter, HTTPException, Request
from services.triage_service import run_triage
import logging

router = APIRouter(tags=["triage"])
logger = logging.getLogger(__name__)


@router.post("/run_langgraph")
async def run_langgraph(request: Request):
    data = await request.json()
    phrases = data.get("phrases", [])
    if not phrases:
        raise HTTPException(status_code=400, detail="No phrases provided.")

    logger.info(f"[triage] Running triage with {len(phrases)} phrases")
    result = run_triage(phrases)
    return result
