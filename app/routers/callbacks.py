"""
Callback request management endpoints.

Handles callback link submissions where users can request a survey call.
Simple flow: create contact → trigger outbound call
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, validator
import logging
from typing import Optional
from datetime import datetime, timezone
import uuid

from app.config import get_settings
from app.database import get_db
from app.services.livekit_outbound import initiate_outbound_call

router = APIRouter(prefix="/callbacks", tags=["callbacks"])
logger = logging.getLogger(__name__)
settings = get_settings()


class CallbackRequest(BaseModel):
    """Callback request from user via callback link."""
    survey_id: str
    participant_name: str
    phone_number: str
    email: Optional[str] = None  # Optional email, no validation required
    consent: bool
    preferred_time: Optional[str] = None  # For future scheduling

    @validator('phone_number')
    def validate_phone(cls, v):
        """Validate phone number format."""
        # Remove common formatting characters
        cleaned = v.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')

        # Check if it's all digits and reasonable length
        if not cleaned.isdigit():
            raise ValueError('Phone number must contain only digits')

        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError('Phone number must be between 10-15 digits')

        # Add + prefix if not present
        if not v.startswith('+'):
            # Assume India if 10 digits, otherwise use as-is
            if len(cleaned) == 10:
                return f'+91{cleaned}'
            else:
                return f'+{cleaned}'

        return v

    @validator('consent')
    def validate_consent(cls, v):
        """Ensure consent is given."""
        if not v:
            raise ValueError('Consent is required to participate in the survey')
        return v


class CallbackResponse(BaseModel):
    """Response after callback request submission."""
    success: bool
    message: str
    contact_id: str
    estimated_call_time: str


@router.post("/request", response_model=CallbackResponse)
async def request_callback(
    request: CallbackRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a callback request to receive a survey call.

    Simplified flow:
    1. User submits name, phone, consent via callback link
    2. Create contact with consent=True
    3. Trigger outbound call immediately

    Args:
        request: Callback request data
        background_tasks: FastAPI background tasks

    Returns:
        CallbackResponse with success status
    """
    db = get_db()

    try:
        # 1. Verify survey exists and is active
        survey_result = db.table("surveys").select("*").eq("survey_id", request.survey_id).execute()

        if not survey_result.data:
            raise HTTPException(status_code=404, detail="Survey not found")

        survey = survey_result.data[0]

        if survey.get("status") != "active":
            raise HTTPException(status_code=400, detail="Survey is not active")

        # 2. Create or update contact with consent=True
        contact_id = str(uuid.uuid4())
        contact_data = {
            "contact_id": contact_id,
            "survey_id": request.survey_id,
            "participant_name": request.participant_name,
            "phone_number": request.phone_number,
            "email": request.email,
            "consent": True,  # User gave consent via callback form
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Check if contact already exists
        existing_contact = db.table("contacts").select("*").eq(
            "survey_id", request.survey_id
        ).eq(
            "phone_number", request.phone_number
        ).execute()

        if existing_contact.data:
            # Update existing contact
            contact_id = existing_contact.data[0]["contact_id"]
            db.table("contacts").update({
                "participant_name": request.participant_name,
                "email": request.email,
                "consent": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("contact_id", contact_id).execute()

            logger.info(f"Updated existing contact {contact_id}")
        else:
            # Create new contact
            db.table("contacts").insert(contact_data).execute()
            logger.info(f"Created new contact {contact_id}")

        # 3. Trigger outbound call in background
        background_tasks.add_task(
            initiate_callback_call,
            survey=survey,
            contact_id=contact_id,
            phone_number=request.phone_number
        )

        return CallbackResponse(
            success=True,
            message="Thank you! You will receive a call shortly.",
            contact_id=contact_id,
            estimated_call_time="within 1 minute"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing callback request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process callback request: {str(e)}")


async def initiate_callback_call(
    survey: dict,
    contact_id: str,
    phone_number: str
):
    """
    Initiate outbound call for callback request.

    Args:
        survey: Survey data
        contact_id: Contact ID
        phone_number: Phone number to call
    """
    try:
        logger.info(f"Initiating callback call to {phone_number} for contact {contact_id}")

        # Make outbound call via LiveKit
        call_result = await initiate_outbound_call(
            to_phone=phone_number,
            survey_id=survey["survey_id"],
            contact_id=contact_id
        )

        logger.info(f"Callback call initiated successfully: {call_result.get('call_sid')}")

    except Exception as e:
        logger.error(f"Error initiating callback call: {e}", exc_info=True)
