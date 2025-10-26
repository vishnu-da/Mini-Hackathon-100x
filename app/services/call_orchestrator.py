"""
Call orchestration service for managing survey call campaigns.
"""
import logging
import asyncio
from typing import Dict, Any
from fastapi import HTTPException, BackgroundTasks
from datetime import datetime, timezone

from app.database import get_db
from app.services import livekit_outbound
from app.services.survey_service import get_survey

logger = logging.getLogger(__name__)


async def start_campaign(survey_id: str, user_id: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Start a call campaign for a survey.

    Args:
        survey_id: Survey UUID
        user_id: User UUID
        background_tasks: FastAPI background tasks

    Returns:
        Dict with campaign status

    Raises:
        HTTPException: If survey not active or no contacts
    """
    db = get_db()

    # Verify survey exists and user owns it
    survey = await get_survey(survey_id, user_id)

    # Check survey is active
    if survey.get("status") != "active":
        raise HTTPException(
            status_code=400,
            detail="Survey must be active to start calls"
        )

    # Fetch all contacts for this survey
    contacts_response = db.table("contact").select("*").eq("survey_id", survey_id).execute()

    contacts = contacts_response.data if contacts_response.data else []

    if not contacts:
        raise HTTPException(
            status_code=400,
            detail="No contacts found for this survey"
        )

    logger.info(f"Starting campaign for survey {survey_id} with {len(contacts)} contacts")

    calls_initiated = 0

    # Initiate calls for each contact
    for contact in contacts:
        contact_id = contact["contact_id"]
        phone_number = contact["phone_number"]

        # Queue call as background task (allow multiple calls per contact for retries)
        background_tasks.add_task(
            process_single_call,
            contact_id=contact_id,
            phone_number=phone_number,
            survey_id=survey_id
        )

        calls_initiated += 1

    logger.info(f"Queued {calls_initiated} calls for survey {survey_id}")

    return {
        "status": "started",
        "calls_queued": calls_initiated,
        "total_contacts": len(contacts)
    }


async def process_single_call(contact_id: str, phone_number: str, survey_id: str):
    """
    Background task to process a single call using LiveKit outbound SIP.

    Args:
        contact_id: Contact UUID
        phone_number: Phone number to call (E.164 format)
        survey_id: Survey UUID
    """
    db = get_db()

    try:
        logger.info(f"Processing call for contact {contact_id}")

        # Initiate outbound call via LiveKit SIP
        # This creates a room, dials the user, and the agent will auto-connect
        result = await livekit_outbound.initiate_outbound_call(
            to_phone=phone_number,
            survey_id=survey_id,
            contact_id=contact_id
        )

        logger.info(f"Call initiated for contact {contact_id}: room={result['room_name']}, call_sid={result['call_sid']}")

    except Exception as e:
        logger.error(f"Failed to process call for contact {contact_id}: {e}", exc_info=True)

        # Create failed call log
        try:
            db.table("call_logs").insert({
                "twilio_call_sid": f"failed-{contact_id}-{datetime.now(timezone.utc).timestamp()}",
                "contact_id": contact_id,
                "status": "failed",
                "raw_transcript": str(e)
            }).execute()
        except Exception as log_error:
            logger.error(f"Failed to create error log: {log_error}")


async def get_call_logs(survey_id: str, user_id: str) -> Dict[str, Any]:
    """
    Get call logs for a survey.

    Args:
        survey_id: Survey UUID
        user_id: User UUID

    Returns:
        Dict with call logs list

    Raises:
        HTTPException: If survey not found
    """
    db = get_db()

    # Verify survey exists and user owns it
    await get_survey(survey_id, user_id)

    # Fetch all contacts for survey
    contacts_response = db.table("contact").select("contact_id").eq("survey_id", survey_id).execute()

    contact_ids = [c["contact_id"] for c in (contacts_response.data or [])]

    if not contact_ids:
        return {
            "call_logs": [],
            "total": 0
        }

    # Fetch call logs with contact information
    logs_response = db.table("call_logs").select(
        "*, contact(participant_name, phone_number, participant_email)"
    ).in_("contact_id", contact_ids).order("call_timestamp", desc=True).execute()

    logs = logs_response.data if logs_response.data else []

    # Flatten contact data into logs for easier frontend access
    for log in logs:
        if log.get("contact"):
            log["participant_name"] = log["contact"].get("participant_name", "Unknown")
            log["phone_number"] = log["contact"].get("phone_number", "")
            log["participant_email"] = log["contact"].get("participant_email", "")

    return {
        "call_logs": logs,
        "total": len(logs)
    }
