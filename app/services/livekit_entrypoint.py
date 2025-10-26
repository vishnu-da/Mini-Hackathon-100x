"""
LiveKit worker entrypoint for handling voice survey calls.
"""
import logging
import asyncio
import os
from typing import Dict, Any

from livekit.agents import JobContext, WorkerOptions, cli

from app.config import get_settings
from app.database import get_db
from app.services.livekit_voice_agent import create_agent_session

# Enable verbose logging for latency analysis
os.environ["LIVEKIT_LOG_LEVEL"] = "debug"  # Enable detailed LiveKit logs
os.environ["LIVEKIT_AGENTS_DEBUG"] = "1"    # Enable agent debugging

logger = logging.getLogger(__name__)
settings = get_settings()

# Set detailed logging for LiveKit agents components
logging.getLogger("livekit.agents").setLevel(logging.DEBUG)
logging.getLogger("livekit.plugins").setLevel(logging.DEBUG)


async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for LiveKit agent worker.

    For outbound calls: Receives job with metadata, creates SIP participant, starts agent.
    For inbound calls: Room already has SIP participant, just starts agent.

    Args:
        ctx: Job context from LiveKit
    """
    try:
        logger.info(f"New job started: room={ctx.room.name}")

        # Connect to room
        await ctx.connect()

        # Parse metadata from job (for outbound) or room (for inbound)
        room_metadata = await _parse_room_metadata(ctx)

        if not room_metadata:
            logger.error("Could not parse room metadata")
            return

        survey_id = room_metadata["survey_id"]
        contact_id = room_metadata["contact_id"]
        call_sid = room_metadata["call_sid"]
        phone_number = room_metadata.get("phone_number")
        call_type = room_metadata.get("call_type", "inbound")
        trunk_id = room_metadata.get("trunk_id")  # Get user's SIP trunk ID

        logger.info(f"Job type: {call_type}, phone: {phone_number}, trunk: {trunk_id}")

        # For OUTBOUND calls: Dial the SIP participant now
        if call_type == "outbound" and phone_number:
            logger.info(f"Creating SIP participant for outbound call to {phone_number}")

            # Import here to avoid circular dependency
            from livekit import api
            from app.config import get_settings
            settings = get_settings()

            # PRODUCTION: trunk_id must be provided in metadata
            if not trunk_id:
                logger.error(f"No trunk_id in metadata for call {call_sid}")
                raise Exception("No SIP trunk configured for this call")

            # Create API client
            lk_api = api.LiveKitAPI(
                settings.livekit_url,
                settings.livekit_api_key,
                settings.livekit_api_secret
            )

            try:
                # Dial user's phone using their dedicated trunk
                sip_call = await lk_api.sip.create_sip_participant(
                    api.CreateSIPParticipantRequest(
                        sip_trunk_id=trunk_id,  # Use per-user trunk
                        sip_call_to=phone_number,
                        room_name=ctx.room.name,
                        participant_identity=f"caller-{contact_id}",
                        participant_name=f"Participant {phone_number}",
                        play_ringtone=True
                    )
                )
                logger.info(f"SIP participant created: {sip_call.participant_id}, dialing {phone_number}")

                # Close API client to prevent resource leaks
                await lk_api.aclose()
            except Exception as e:
                logger.error(f"Failed to create SIP participant: {e}", exc_info=True)
                # Close API client even on error
                try:
                    await lk_api.aclose()
                except:
                    pass
                return

        # Fetch survey and contact from database
        db = get_db()

        contact_response = db.table("contact").select("*").eq("contact_id", contact_id).execute()
        if not contact_response.data:
            logger.error(f"Contact not found: {contact_id}")
            return

        contact = contact_response.data[0]

        survey_response = db.table("surveys").select("*").eq("survey_id", survey_id).execute()
        if not survey_response.data:
            logger.error(f"Survey not found: {survey_id}")
            return

        survey = survey_response.data[0]

        # Fetch researcher name from users table
        user_id = survey.get("user_id")
        if user_id:
            user_response = db.table("users").select("name").eq("user_id", user_id).execute()
            if user_response.data:
                survey["researcher_name"] = user_response.data[0].get("name")

        # Create agent and session
        agent, session = create_agent_session(survey, contact, call_sid)

        # Start agent session
        await session.start(agent=agent, room=ctx.room)

        logger.info(f"Agent session started for room {ctx.room.name}")

    except Exception as e:
        logger.error(f"Error in entrypoint: {e}", exc_info=True)


async def _parse_room_metadata(ctx: JobContext) -> Dict[str, Any] | None:
    """
    Parse metadata to extract survey_id, contact_id, call_sid, phone_number, call_type.

    Checks job metadata first (for outbound calls via agent dispatch),
    then room metadata (for inbound calls via dispatch rules).

    Args:
        ctx: Job context

    Returns:
        Dict with metadata or None if parsing fails
    """
    try:
        import json

        # First: Check job metadata (for outbound calls via create_agent_dispatch)
        if ctx.job.metadata:
            metadata = json.loads(ctx.job.metadata)
            logger.info(f"Parsed metadata from job: {metadata}")
            return metadata

        # Second: Check room metadata (for inbound calls via dispatch rules)
        if ctx.room.metadata:
            metadata = json.loads(ctx.room.metadata)
            logger.info(f"Parsed metadata from room: {metadata}")
            return metadata

        # Fallback: Parse call_sid from room name if metadata not available
        # Format: "survey-{call_sid}"
        room_name = ctx.room.name
        if room_name.startswith("survey-"):
            call_sid = room_name[7:]  # Remove "survey-" prefix

            # Need to fetch survey_id and contact_id from database using call_sid
            db = get_db()
            call_log = db.table("call_logs").select("contact_id").eq("twilio_call_sid", call_sid).execute()

            if call_log.data:
                contact_id = call_log.data[0]["contact_id"]

                # Fetch survey_id from contact
                contact_data = db.table("contact").select("survey_id").eq("contact_id", contact_id).execute()
                if contact_data.data:
                    survey_id = contact_data.data[0]["survey_id"]

                    logger.info(f"Parsed metadata from room name + DB: survey={survey_id}, contact={contact_id}, call={call_sid}")
                    return {
                        "survey_id": survey_id,
                        "contact_id": contact_id,
                        "call_sid": call_sid,
                        "call_type": "inbound"
                    }

        logger.error(f"Could not parse room metadata from name: {room_name}")
        return None

    except Exception as e:
        logger.error(f"Error parsing room metadata: {e}")
        return None


def start_worker():
    """
    Start LiveKit agent worker.

    This should be run as a separate process/service.
    """
    # Configure logging - DEBUG level for detailed timing analysis
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting LiveKit agent worker...")
    logger.info(f"LiveKit URL: {settings.livekit_url}")
    logger.info("Verbose logging enabled for STT/LLM/TTS latency analysis")

    # Run worker with entrypoint
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="survey-voice-agent",  # Required for explicit dispatch
        )
    )


if __name__ == "__main__":
    start_worker()
