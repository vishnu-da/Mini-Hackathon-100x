"""
Survey management service for creating and managing voice surveys.
"""
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from fastapi import HTTPException

from app.config import get_settings
from app.database import get_db
from app.services import oauth_service
from app.services.form_fetcher import fetch_form
from app.schemas.survey import CreateSurveyRequest, UpdateSurveyRequest, VoiceConfigUpdate

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_survey(user_id: str, request: CreateSurveyRequest) -> Dict[str, Any]:
    """
    Create a new survey from Google Form.

    Args:
        user_id: User's UUID
        request: Survey creation request data

    Returns:
        Created survey dict

    Raises:
        HTTPException: If validation fails or form fetch fails
    """
    db = get_db()

    # Step 1: Validate user has Google OAuth connected
    logger.info(f"Creating survey for user {user_id}")
    has_google_token = await oauth_service.has_valid_token(user_id, "google")

    if not has_google_token:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "google_not_connected",
                "message": "Google account not connected",
                "action_required": "connect_google"
            }
        )

    # Step 2: Fetch form using form_fetcher
    logger.info(f"Fetching Google Form: {request.form_url}")
    form_data = await fetch_form(user_id, request.form_url)

    if form_data.get("error"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": form_data.get("error_type"),
                "message": form_data.get("message"),
                "action_required": form_data.get("action_required")
            }
        )

    # Step 3: Create voice_agent record
    logger.info("Creating voice agent configuration")
    voice_agent_response = db.table("voice_agents").insert({
        "model_name": "gpt-4o-realtime-preview",
        "tools_functions": {}
    }).execute()

    if not voice_agent_response.data:
        raise HTTPException(status_code=500, detail="Failed to create voice agent")

    voice_agent_id = voice_agent_response.data[0]["voice_agent_id"]

    # Step 4: Create spreadsheet_destination record
    logger.info("Creating spreadsheet destination")
    spreadsheet_response = db.table("spreadsheet_destinations").insert({
        "spreadsheet_type": "google_sheets",
        "spreadsheet_id": "",  # Empty string instead of None
        "api_credentials": None
    }).execute()

    if not spreadsheet_response.data:
        raise HTTPException(status_code=500, detail="Failed to create spreadsheet destination")

    destination_id = spreadsheet_response.data[0]["destination_id"]

    # Step 5: Insert survey into database
    logger.info("Creating survey record")
    survey_data = {
        "user_id": user_id,
        "form_link": request.form_url,
        "json_questionnaire": form_data,
        "status": "draft",
        "voice_agent_tone": request.voice_agent_tone,
        "voice_agent_instructions": request.voice_agent_instructions,
        "callback_link": "",  # Will be updated after getting survey_id
        "max_call_duration": request.max_call_duration,
        "max_retry_attempts": request.max_retry_attempts,
        "terms_and_conditions": request.terms_and_conditions,
        "voice_agent_id": voice_agent_id,
        "destination_id": destination_id
    }

    survey_response = db.table("surveys").insert(survey_data).execute()

    if not survey_response.data:
        raise HTTPException(status_code=500, detail="Failed to create survey")

    survey = survey_response.data[0]
    survey_id = survey["survey_id"]

    # Step 6: Update callback_link with survey_id
    callback_link = f"{settings.callback_base_url}/callback/{survey_id}"
    db.table("surveys").update({
        "callback_link": callback_link
    }).eq("survey_id", survey_id).execute()

    survey["callback_link"] = callback_link

    logger.info(f"Survey created successfully: {survey_id}")
    return survey


async def get_survey(survey_id: str, user_id: str) -> Dict[str, Any]:
    """
    Get a single survey by ID.

    Args:
        survey_id: Survey UUID
        user_id: User's UUID

    Returns:
        Survey dict

    Raises:
        HTTPException: If survey not found or access denied
    """
    db = get_db()

    response = db.table("surveys").select("*").eq("survey_id", survey_id).eq("user_id", user_id).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Survey not found")

    return response.data[0]


async def list_surveys(user_id: str, status: Optional[str] = None) -> Dict[str, Any]:
    """
    List all surveys for a user.

    Args:
        user_id: User's UUID
        status: Optional status filter

    Returns:
        Dict with surveys list and total count
    """
    db = get_db()

    query = db.table("surveys").select("*").eq("user_id", user_id)

    if status:
        query = query.eq("status", status)

    response = query.order("created_at", desc=True).execute()

    surveys = response.data if response.data else []

    return {
        "surveys": surveys,
        "total": len(surveys)
    }


async def update_survey(survey_id: str, user_id: str, request: UpdateSurveyRequest) -> Dict[str, Any]:
    """
    Update survey details.

    Args:
        survey_id: Survey UUID
        user_id: User's UUID
        request: Update request data

    Returns:
        Updated survey dict

    Raises:
        HTTPException: If survey not found or update fails
    """
    db = get_db()

    # Verify survey exists and user owns it
    existing_survey = await get_survey(survey_id, user_id)

    # Build update dict with only provided fields
    update_data = {}

    if request.terms_and_conditions is not None:
        update_data["terms_and_conditions"] = request.terms_and_conditions

    if request.voice_agent_tone is not None:
        update_data["voice_agent_tone"] = request.voice_agent_tone

    if request.voice_agent_instructions is not None:
        update_data["voice_agent_instructions"] = request.voice_agent_instructions

    if request.max_call_duration is not None:
        update_data["max_call_duration"] = request.max_call_duration

    if request.max_retry_attempts is not None:
        update_data["max_retry_attempts"] = request.max_retry_attempts

    # If form_url changed, re-fetch form
    if request.form_url is not None and request.form_url != existing_survey["form_link"]:
        logger.info(f"Form URL changed, re-fetching form")
        form_data = await fetch_form(user_id, request.form_url)

        if form_data.get("error"):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": form_data.get("error_type"),
                    "message": form_data.get("message")
                }
            )

        update_data["form_link"] = request.form_url
        update_data["json_questionnaire"] = form_data

    if not update_data:
        return existing_survey

    # Perform update
    response = db.table("surveys").update(update_data).eq("survey_id", survey_id).eq("user_id", user_id).execute()

    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update survey")

    logger.info(f"Survey updated: {survey_id}")
    return response.data[0]


async def update_voice_config(survey_id: str, user_id: str, config: VoiceConfigUpdate) -> Dict[str, Any]:
    """
    Update voice agent configuration for survey.

    Args:
        survey_id: Survey UUID
        user_id: User's UUID
        config: Voice configuration data

    Returns:
        Updated survey dict

    Raises:
        HTTPException: If survey not found or update fails
    """
    db = get_db()

    # Verify survey exists and user owns it
    await get_survey(survey_id, user_id)

    # Update voice configuration
    update_data = {
        "voice_agent_tone": config.voice_agent_tone,
        "voice_agent_instructions": config.voice_agent_instructions,
        "max_call_duration": config.max_call_duration,
        "max_retry_attempts": config.max_retry_attempts
    }

    response = db.table("surveys").update(update_data).eq("survey_id", survey_id).eq("user_id", user_id).execute()

    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to update voice configuration")

    logger.info(f"Voice config updated for survey: {survey_id}")
    return response.data[0]


async def activate_survey(survey_id: str, user_id: str) -> Dict[str, Any]:
    """
    Activate a survey (change status from draft to active).

    Args:
        survey_id: Survey UUID
        user_id: User's UUID

    Returns:
        Updated survey dict

    Raises:
        HTTPException: If survey not found or validation fails
    """
    db = get_db()

    # Get survey to validate
    survey = await get_survey(survey_id, user_id)

    # Validate survey is ready
    if not survey.get("json_questionnaire"):
        raise HTTPException(status_code=400, detail="Survey has no questionnaire")

    if survey.get("status") == "active":
        raise HTTPException(status_code=400, detail="Survey is already active")

    # Update status to active
    response = db.table("surveys").update({
        "status": "active"
    }).eq("survey_id", survey_id).eq("user_id", user_id).execute()

    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to activate survey")

    logger.info(f"Survey activated: {survey_id}")
    return response.data[0]


async def deactivate_survey(survey_id: str, user_id: str) -> Dict[str, Any]:
    """
    Deactivate a survey (change status to closed).

    Args:
        survey_id: Survey UUID
        user_id: User's UUID

    Returns:
        Updated survey dict

    Raises:
        HTTPException: If survey not found
    """
    db = get_db()

    # Verify survey exists
    await get_survey(survey_id, user_id)

    # Update status to closed
    response = db.table("surveys").update({
        "status": "closed"
    }).eq("survey_id", survey_id).eq("user_id", user_id).execute()

    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to deactivate survey")

    logger.info(f"Survey deactivated: {survey_id}")
    return response.data[0]


async def delete_survey(survey_id: str, user_id: str) -> bool:
    """
    Delete a survey and related records.

    Args:
        survey_id: Survey UUID
        user_id: User's UUID

    Returns:
        True if successful

    Raises:
        HTTPException: If survey not found or deletion fails
    """
    db = get_db()

    # Verify survey exists and user owns it
    await get_survey(survey_id, user_id)

    # Delete survey (CASCADE will handle related records)
    db.table("surveys").delete().eq("survey_id", survey_id).eq("user_id", user_id).execute()

    logger.info(f"Survey deleted: {survey_id}")
    return True
