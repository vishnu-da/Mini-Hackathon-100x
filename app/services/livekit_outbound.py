"""
LiveKit outbound calling service.
Replaces Twilio webhook approach with LiveKit SIP participant dialing.
"""
import logging
import json
from typing import Dict, Any
from livekit import api

from app.config import get_settings
from app.database import get_db

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize LiveKit API client
livekit_api = api.LiveKitAPI(
    settings.livekit_url,
    settings.livekit_api_key,
    settings.livekit_api_secret
)


async def initiate_outbound_call(
    to_phone: str,
    survey_id: str,
    contact_id: str,
    call_sid: str = None,
    trunk_id: str = None
) -> Dict[str, Any]:
    """
    Initiate an outbound call using LiveKit agent dispatch + SIP.

    For outbound calls, we use create_agent_dispatch() to explicitly
    dispatch the agent to a new room with metadata. The agent then
    creates the SIP participant from within the job.

    Args:
        to_phone: Destination phone number (E.164 format)
        survey_id: Survey UUID
        contact_id: Contact UUID
        call_sid: Optional call SID (will be generated if not provided)
        trunk_id: Optional SIP trunk ID (fetched from survey if not provided)

    Returns:
        Dict with room_name, call_sid, and dispatch_id

    Raises:
        Exception: If agent dispatch fails
    """
    try:
        # Generate call identifier
        if not call_sid:
            import uuid
            call_sid = f"LK{uuid.uuid4().hex[:30]}"  # LiveKit call ID

        # Get trunk_id from survey owner if not provided
        if not trunk_id:
            db = get_db()
            survey = db.table("surveys").select("user_id").eq("survey_id", survey_id).execute()
            if survey.data:
                user_id = survey.data[0]["user_id"]
                user = db.table("users").select("livekit_trunk_id").eq("user_id", user_id).execute()
                if user.data:
                    trunk_id = user.data[0].get("livekit_trunk_id")
                    logger.info(f"Using trunk_id from survey owner: {trunk_id}")

        # PRODUCTION: No fallback. User MUST have a trunk.
        if not trunk_id:
            raise Exception(f"No SIP trunk configured for survey {survey_id}. Run phone provisioning first.")

        # Room name
        room_name = f"survey-{call_sid}"

        # Metadata for agent (includes phone number to dial and trunk_id)
        agent_metadata = json.dumps({
            "survey_id": survey_id,
            "contact_id": contact_id,
            "call_sid": call_sid,
            "phone_number": to_phone,
            "call_type": "outbound",
            "trunk_id": trunk_id  # Pass trunk_id to entrypoint
        })

        logger.info(f"Dispatching agent for outbound call: {room_name} -> {to_phone}")

        # Create initial call log entry
        db = get_db()
        try:
            db.table("call_logs").insert({
                "twilio_call_sid": call_sid,
                "contact_id": contact_id,
                "status": "initiated",
                "call_duration": 0,
                "consent": False,
                "raw_transcript": "",
                "raw_responses": [],
                "mapped_responses": []
            }).execute()
            logger.info(f"Created call log for {call_sid}")
        except Exception as e:
            logger.warning(f"Could not create call log: {e}")

        # Dispatch agent to new room with metadata
        # This creates room + dispatches agent in one operation
        dispatch = await livekit_api.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                room=room_name,
                agent_name="survey-voice-agent",
                metadata=agent_metadata
            )
        )

        logger.info(f"Agent dispatched to room {room_name}")

        return {
            "room_name": room_name,
            "call_sid": call_sid,
            "dispatch_id": str(dispatch),
            "status": "dispatching"
        }

    except Exception as e:
        logger.error(f"Failed to initiate outbound call: {e}", exc_info=True)
        raise


async def end_call(room_name: str) -> bool:
    """
    End an ongoing call by deleting the room.

    Args:
        room_name: LiveKit room name

    Returns:
        True if successful
    """
    try:
        await livekit_api.room.delete_room(
            api.DeleteRoomRequest(room=room_name)
        )
        logger.info(f"Room deleted: {room_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete room: {e}")
        raise
