"""
Call management API endpoints.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from typing import Dict, Any

from app.auth import get_current_user_id
from app.services import call_orchestrator

router = APIRouter()


@router.post("/{survey_id}/calls/start")
async def start_call_campaign(
    survey_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Start voice call campaign for a survey.

    Initiates calls to all contacts in the survey who haven't been called yet.

    Args:
        survey_id: Survey UUID
        background_tasks: FastAPI background tasks
        user_id: Authenticated user ID

    Returns:
        Campaign status with number of calls queued
    """
    result = await call_orchestrator.start_campaign(survey_id, user_id, background_tasks)
    return result


@router.get("/{survey_id}/calls/logs")
async def get_call_logs(
    survey_id: str,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Get call logs for a survey.

    Returns all call logs with status, responses, and transcripts.

    Args:
        survey_id: Survey UUID
        user_id: Authenticated user ID

    Returns:
        Dict with call logs list and total count
    """
    result = await call_orchestrator.get_call_logs(survey_id, user_id)
    return result
