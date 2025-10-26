"""
Webhooks for Twilio call handling with LiveKit integration.
"""
import logging
import json
from typing import Dict, Any
from fastapi import APIRouter, Request, Response, BackgroundTasks
from fastapi.responses import PlainTextResponse
from livekit import api

from app.database import get_db
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# Initialize LiveKit API client
livekit_api = api.LiveKitAPI(
    settings.livekit_url,
    settings.livekit_api_key,
    settings.livekit_api_secret
)


@router.api_route("/twilio/voice/{contact_id}", methods=["GET", "POST"])
async def twilio_voice_webhook(contact_id: str, request: Request):
    """
    Twilio calls this when a call connects.
    Creates LiveKit room and returns TwiML to connect via SIP.

    Args:
        contact_id: Contact UUID
        request: FastAPI request object

    Returns:
        TwiML XML response
    """
    db = get_db()

    logger.info(f"Twilio voice webhook called for contact {contact_id}")

    # Get form data
    form_data = await request.form() if request.method == "POST" else {}
    call_sid = form_data.get("CallSid") or request.query_params.get("CallSid")

    # Fetch contact and survey from database
    contact_response = db.table("contact").select("*").eq("contact_id", contact_id).execute()

    if not contact_response.data:
        logger.error(f"Contact not found: {contact_id}")
        return PlainTextResponse(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, we could not find your contact information.</Say><Hangup/></Response>',
            media_type="application/xml"
        )

    contact = contact_response.data[0]
    survey_id = contact["survey_id"]

    # Fetch survey
    survey_response = db.table("surveys").select("*").eq("survey_id", survey_id).execute()

    if not survey_response.data:
        logger.error(f"Survey not found: {survey_id}")
        return PlainTextResponse(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, this survey is no longer available.</Say><Hangup/></Response>',
            media_type="application/xml"
        )

    survey = survey_response.data[0]

    # Validate survey has questions
    questions = survey.get("json_questionnaire", {}).get("questions", [])
    if not questions:
        return PlainTextResponse(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, this survey has no questions.</Say><Hangup/></Response>',
            media_type="application/xml"
        )

    # Create LiveKit room for this call
    # Room name format: survey-{call_sid} (matches dispatch rule pattern)
    room_name = f"survey-{call_sid}"

    try:
        # Create room with metadata (contains all necessary info)
        room_metadata = json.dumps({
            "survey_id": survey_id,
            "contact_id": contact_id,
            "call_sid": call_sid
        })

        room = await livekit_api.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                metadata=room_metadata,
                empty_timeout=300,  # 5 minutes timeout
                max_participants=2  # Just the caller and the agent
            )
        )

        logger.info(f"Created LiveKit room: {room_name}")

        # Create initial call log entry
        try:
            db.table("call_logs").insert({
                "twilio_call_sid": call_sid,
                "contact_id": contact_id,
                "status": "in_progress",
                "call_duration": 0,
                "consent": False,
                "raw_transcript": "",
                "raw_responses": [],
                "mapped_responses": []
            }).execute()
            logger.info(f"Created initial call log for {call_sid}")
        except Exception as e:
            logger.warning(f"Could not create initial call log: {e}")

        # Return TwiML that connects call to LiveKit room via SIP
        # Use SIP domain from config (shared across all users)
        sip_uri = f"sip:{room_name}@{settings.livekit_sip_domain}"

        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>{sip_uri}</Sip>
    </Dial>
</Response>'''

        logger.info(f"Returning SIP TwiML for contact {contact_id} - Room: {room_name}")

        return PlainTextResponse(content=twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"Failed to create LiveKit room: {e}")
        return PlainTextResponse(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, we encountered a technical error.</Say><Hangup/></Response>',
            media_type="application/xml"
        )


@router.api_route("/twilio/recording", methods=["GET", "POST"])
async def twilio_recording_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Twilio calls this when a recording is ready.

    Args:
        request: FastAPI request with recording data

    Returns:
        Empty response
    """
    try:
        # Handle both GET and POST
        if request.method == "POST":
            form_data = await request.form()
            call_sid = form_data.get("CallSid")
            recording_sid = form_data.get("RecordingSid")
            recording_url = form_data.get("RecordingUrl")
            recording_status = form_data.get("RecordingStatus")
        else:
            call_sid = request.query_params.get("CallSid")
            recording_sid = request.query_params.get("RecordingSid")
            recording_url = request.query_params.get("RecordingUrl")
            recording_status = request.query_params.get("RecordingStatus")

        logger.info(f"Recording webhook: call={call_sid}, recording={recording_sid}, status={recording_status}")

        # Only process when recording is completed
        if recording_status == "completed" and recording_url and call_sid:
            db = get_db()

            # Update call log with recording URL
            existing = db.table("call_logs").select("twilio_call_sid").eq("twilio_call_sid", call_sid).execute()

            if existing.data:
                # Update with recording URL
                db.table("call_logs").update({
                    "recording_url": recording_url
                }).eq("twilio_call_sid", call_sid).execute()

                logger.info(f"Recording ready for {call_sid}: {recording_url}")
                # Post-call processing now happens automatically in LiveKit agent's on_exit()
                # No additional processing needed here
            else:
                logger.warning(f"Call log not found for {call_sid}, skipping recording processing")

    except Exception as e:
        logger.error(f"Failed to process recording webhook: {e}")

    return Response(status_code=200)


@router.api_route("/twilio/status", methods=["GET", "POST"])
async def twilio_status_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Twilio calls this with call status updates.
    Updates call_logs with final status and duration.

    Args:
        request: FastAPI request with form data

    Returns:
        Empty response
    """
    try:
        # Handle both GET and POST
        if request.method == "POST":
            form_data = await request.form()
            call_sid = form_data.get("CallSid")
            call_status = form_data.get("CallStatus")
            call_duration = form_data.get("CallDuration", 0)
            recording_url = form_data.get("RecordingUrl")
        else:
            # GET request
            call_sid = request.query_params.get("CallSid")
            call_status = request.query_params.get("CallStatus")
            call_duration = request.query_params.get("CallDuration", 0)
            recording_url = request.query_params.get("RecordingUrl")

        logger.info(f"Call status update: {call_sid} = {call_status}, duration={call_duration}s")

        if call_sid and call_status:
            db = get_db()

            # Map Twilio status to database format
            db_status = call_status.replace("-", "_") if call_status else None

            # Update call log
            if db_status:
                update_data = {
                    "status": db_status,
                    "call_duration": int(call_duration) if call_duration else 0
                }

                if recording_url:
                    update_data["recording_url"] = recording_url

                # Check if call log exists
                existing = db.table("call_logs").select("twilio_call_sid").eq("twilio_call_sid", call_sid).execute()

                if existing.data:
                    # Update existing
                    db.table("call_logs").update(update_data).eq("twilio_call_sid", call_sid).execute()
                    logger.info(f"Updated call log for {call_sid} with status {db_status}")
                else:
                    logger.warning(f"Call log {call_sid} doesn't exist yet, skipping status update")

    except Exception as e:
        logger.error(f"Failed to process status webhook: {e}")

    return Response(status_code=200)
