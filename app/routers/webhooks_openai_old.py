"""
Webhooks for Twilio call handling and OpenAI Realtime API integration.
"""
import logging
import json
import base64
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Response, BackgroundTasks
from fastapi.responses import PlainTextResponse
import websockets

from app.database import get_db
from app.services import voice_agent, response_mapper, audio_converter
from app.services.post_call_processor import process_completed_call
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.api_route("/twilio/voice/{contact_id}", methods=["GET", "POST"])
async def twilio_voice_webhook(contact_id: str, request: Request):
    """
    Twilio calls this when a call connects.
    Returns TwiML with survey question.

    Args:
        contact_id: Contact UUID
        request: FastAPI request object

    Returns:
        TwiML XML response
    """
    db = get_db()

    logger.info(f"Twilio voice webhook called for contact {contact_id}")

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

    # Get first question
    try:
        first_question = voice_agent.extract_first_question(survey)
    except ValueError:
        return PlainTextResponse(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, this survey has no questions.</Say><Hangup/></Response>',
            media_type="application/xml"
        )

    # Build WebSocket URL for streaming to OpenAI Realtime API
    # Use wss:// for secure WebSocket connection
    ws_url = f"{settings.callback_base_url.replace('https://', 'wss://').replace('http://', 'ws://')}/webhooks/ws/voice/{contact_id}"

    # Return TwiML that connects to WebSocket for bidirectional audio streaming
    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="survey_id" value="{survey_id}"/>
            <Parameter name="contact_id" value="{contact_id}"/>
        </Stream>
    </Connect>
</Response>'''

    logger.info(f"Returning Stream TwiML for contact {contact_id} - WebSocket: {ws_url}")

    return PlainTextResponse(content=twiml, media_type="application/xml")


# NOTE: These webhooks are no longer used when using OpenAI Realtime API streaming
# The conversation is handled entirely through the WebSocket connection


@router.websocket("/ws/voice/{contact_id}")
async def voice_websocket(websocket: WebSocket, contact_id: str):
    """
    WebSocket for bidirectional audio streaming between Twilio and OpenAI Realtime API.

    Twilio sends audio → we forward to OpenAI
    OpenAI sends audio → we forward to Twilio

    Args:
        websocket: FastAPI WebSocket connection
        contact_id: Contact UUID
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for contact {contact_id}")

    db = get_db()
    openai_ws = None
    call_sid = None
    stream_sid = None

    try:
        # Fetch contact and survey in parallel to reduce latency
        contact_task = asyncio.create_task(
            asyncio.to_thread(
                lambda: db.table("contact").select("*").eq("contact_id", contact_id).execute()
            )
        )

        # Wait for contact first to get survey_id
        contact_response = await contact_task
        if not contact_response.data:
            logger.error(f"Contact not found: {contact_id}")
            await websocket.close()
            return

        contact = contact_response.data[0]
        survey_id = contact["survey_id"]

        # Fetch survey asynchronously
        survey_response = await asyncio.to_thread(
            lambda: db.table("surveys").select("*").eq("survey_id", survey_id).execute()
        )
        if not survey_response.data:
            logger.error(f"Survey not found: {survey_id}")
            await websocket.close()
            return

        survey = survey_response.data[0]

        # Fetch researcher name from users table using user_id from survey
        user_id = survey.get("user_id")
        if user_id:
            user_response = await asyncio.to_thread(
                lambda: db.table("users").select("name").eq("user_id", user_id).execute()
            )
            if user_response.data:
                survey["researcher_name"] = user_response.data[0].get("name")
                logger.info(f"Fetched researcher name: {survey['researcher_name']}")
            else:
                logger.warning(f"User not found for user_id: {user_id}")
        else:
            logger.warning(f"No user_id found in survey {survey_id}")

        # Create voice session config
        session_config = voice_agent.create_voice_session(survey, contact)

        # Reset audio conversion state for this new call
        audio_converter.reset_conversion_state()

        # Connect to OpenAI Realtime API
        openai_url = f"wss://api.openai.com/v1/realtime?model={settings.openai_realtime_model}"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

        logger.info(f"Connecting to OpenAI Realtime API for contact {contact_id}")
        openai_ws = await websockets.connect(openai_url, extra_headers=headers)

        # Send session configuration to OpenAI
        session_update_msg = {
            "type": "session.update",
            "session": session_config
        }
        logger.info(f"Sending session.update to OpenAI: {json.dumps(session_update_msg, indent=2)[:500]}...")
        await openai_ws.send(json.dumps(session_update_msg))

        # Trigger initial response from AI (to greet the user)
        # No sleep needed - OpenAI processes session.update and response.create in order
        initial_response = {
            "type": "response.create",
            "response": {
                "modalities": ["audio", "text"],
                "instructions": "Start the survey exactly as instructed in your system prompt. Greet briefly and ask for consent."
            }
        }
        logger.info("Triggering initial AI response with crisp greeting")
        await openai_ws.send(json.dumps(initial_response))

        # Start bidirectional streaming
        async def twilio_to_openai():
            """Forward audio from Twilio to OpenAI"""
            nonlocal call_sid, stream_sid

            async for message in websocket.iter_text():
                try:
                    data = json.loads(message)
                    event_type = data.get("event")

                    if event_type == "start":
                        stream_sid = data.get("streamSid")
                        call_sid = data.get("start", {}).get("callSid")
                        logger.info(f"Stream started: {stream_sid}, call: {call_sid}")

                        # Create initial call log entry to avoid race conditions
                        try:
                            initial_call_log = {
                                "contact_id": contact_id,
                                "twilio_call_sid": call_sid,
                                "status": "in_progress",
                                "call_duration": 0,
                                "consent": False,
                                "raw_transcript": "",
                                "raw_responses": [],
                                "mapped_responses": []
                            }
                            db.table("call_logs").insert(initial_call_log).execute()
                            logger.info(f"Created initial call log for {call_sid}")
                        except Exception as e:
                            logger.warning(f"Could not create initial call log (may already exist): {e}")

                    elif event_type == "media":
                        # Forward audio payload to OpenAI
                        media = data.get("media", {})
                        payload = media.get("payload")  # Base64 encoded mulaw (8kHz)

                        if payload and openai_ws:
                            try:
                                # Convert Twilio audio (mulaw 8kHz) to OpenAI format (PCM16 24kHz)
                                pcm16_b64 = audio_converter.twilio_to_openai(payload)

                                # Send to OpenAI
                                await openai_ws.send(json.dumps({
                                    "type": "input_audio_buffer.append",
                                    "audio": pcm16_b64
                                }))

                                # Log first audio packet to confirm audio is flowing
                                if not hasattr(twilio_to_openai, '_first_audio_logged'):
                                    logger.info(f"First audio packet sent to OpenAI (converted from 8kHz mulaw to 24kHz PCM16)")
                                    twilio_to_openai._first_audio_logged = True

                            except Exception as e:
                                logger.error(f"Error converting Twilio→OpenAI audio: {e}")

                    elif event_type == "stop":
                        logger.info(f"Stream stopped: {stream_sid}")
                        break

                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from Twilio")
                except Exception as e:
                    logger.error(f"Error processing Twilio message: {e}")

        async def openai_to_twilio():
            """Forward responses from OpenAI to Twilio"""

            async for message in openai_ws:
                try:
                    data = json.loads(message)
                    event_type = data.get("type")

                    # Log important events from OpenAI (reduce noise by filtering common events)
                    if event_type not in ["response.audio_transcript.delta", "rate_limits.updated"]:
                        logger.info(f"OpenAI event: {event_type}")

                    # Log session.updated confirmation
                    if event_type == "session.updated":
                        logger.info(f"OpenAI session updated successfully: {json.dumps(data, indent=2)[:300]}...")

                    # Log session creation
                    elif event_type == "session.created":
                        logger.info(f"OpenAI session created: {json.dumps(data, indent=2)[:300]}...")

                    # Log any errors
                    elif event_type == "error":
                        logger.error(f"OpenAI error: {json.dumps(data, indent=2)}")

                    elif event_type == "response.audio.delta":
                        # Forward audio from OpenAI to Twilio
                        # NOTE: response.audio.delta contains actual audio data (PCM16 24kHz)
                        # response.audio_transcript.delta is TEXT only, not audio!
                        audio_delta = data.get("delta")
                        if audio_delta and stream_sid:
                            try:
                                # Convert OpenAI audio (PCM16 24kHz) to Twilio format (mulaw 8kHz)
                                mulaw_b64 = audio_converter.openai_to_twilio(audio_delta)

                                # Send to Twilio
                                await websocket.send_json({
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {
                                        "payload": mulaw_b64
                                    }
                                })

                                # Log first audio response to confirm audio is flowing back
                                if not hasattr(openai_to_twilio, '_first_response_logged'):
                                    logger.info(f"First audio response sent to Twilio (converted from 24kHz PCM16 to 8kHz mulaw)")
                                    openai_to_twilio._first_response_logged = True

                            except Exception as e:
                                logger.error(f"Error converting OpenAI→Twilio audio: {e}")

                    elif event_type == "response.audio_transcript.delta":
                        # This is the AI's spoken text (transcript), NOT audio
                        # We can log it but should not try to convert it to audio
                        pass  # Ignore - this is text, not audio data

                    elif event_type == "response.audio_transcript.done":
                        # AI's complete transcript for this response (just log it)
                        transcript_text = data.get("transcript", "")
                        if transcript_text:
                            logger.info(f"AI said: {transcript_text}")

                    elif event_type == "conversation.item.input_audio_transcription.completed":
                        # Participant's transcript (just log it)
                        transcript = data.get("transcript", "")
                        logger.info(f"Participant said: {transcript}")

                    elif event_type == "response.done":
                        # Response completed
                        logger.info("OpenAI response completed")

                except json.JSONDecodeError:
                    logger.warning("Invalid JSON from OpenAI")
                except Exception as e:
                    logger.error(f"Error processing OpenAI message: {e}")

        # Run both streaming tasks concurrently
        await asyncio.gather(
            twilio_to_openai(),
            openai_to_twilio()
        )

    except WebSocketDisconnect:
        logger.info(f"Twilio WebSocket disconnected for contact {contact_id}")

    except Exception as e:
        logger.error(f"Error in voice WebSocket: {e}")

    finally:
        # Close connections
        # Note: All transcription and response mapping will happen in post-call processing
        if openai_ws:
            await openai_ws.close()

        try:
            await websocket.close()
        except:
            pass

        logger.info(f"WebSocket closed for contact {contact_id}")


@router.api_route("/twilio/recording", methods=["GET", "POST"])
async def twilio_recording_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Twilio calls this when a recording is ready.
    This is more reliable than using the call completion webhook.

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
                logger.info(f"Triggering post-call processing: Whisper transcription + GPT response mapping")

                # Run post-call processing in background
                background_tasks.add_task(
                    process_completed_call,
                    call_sid=call_sid,
                    contact_id=None
                )
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

            # Map Twilio status to database format (replace hyphens with underscores)
            # Twilio sends: "in-progress", "no-answer"
            # Database expects: "in_progress", "no_answer"
            db_status = call_status.replace("-", "_") if call_status else None

            # Update call log (only update if there's a valid status)
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

                    # Note: Post-call processing is triggered by the recording webhook
                    # See twilio_recording_webhook() for the trigger point

                else:
                    # Create new entry if doesn't exist (race condition handling)
                    # This shouldn't happen normally, but handles edge cases
                    logger.warning(f"Call log {call_sid} doesn't exist yet, skipping status update")
                    # Don't create it here - let the orchestrator or answer webhook create it

    except Exception as e:
        logger.error(f"Failed to process status webhook: {e}")

    return Response(status_code=200)
