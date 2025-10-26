"""
Campaign management endpoints.

Handles survey campaign creation, launch, and monitoring.
This is the main interface users interact with - they never touch Twilio/LiveKit directly.
"""
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from app.database import get_db
from app.services import phone_provisioning, sip_trunk_provisioning
from app.services.livekit_outbound import initiate_outbound_call
from app.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


# ============================================
# Request/Response Models
# ============================================

class LaunchCampaignRequest(BaseModel):
    """Request to launch a survey campaign."""
    survey_id: str
    test_mode: bool = False  # If True, only calls first contact


class LaunchCampaignResponse(BaseModel):
    """Response after launching campaign."""
    status: str
    campaign_id: str
    phone_number: str
    total_contacts: int
    estimated_duration_minutes: int
    message: str


class CampaignStatusResponse(BaseModel):
    """Campaign status and statistics."""
    campaign_id: str
    status: str
    phone_number: str
    total_contacts: int
    completed_calls: int
    in_progress_calls: int
    failed_calls: int
    pending_calls: int
    completion_percentage: float


class PhoneNumberInfo(BaseModel):
    """User's phone number information."""
    phone_number: str | None
    status: str
    provisioned_at: str | None
    trunk_id: str | None


# ============================================
# Endpoints
# ============================================

@router.post("/launch", response_model=LaunchCampaignResponse)
async def launch_campaign(
    request: LaunchCampaignRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Launch a survey campaign.

    This is the main endpoint users hit when they click "Start Campaign".
    Backend automatically:
    1. Provisions phone number (if user doesn't have one)
    2. Creates SIP trunk (if needed)
    3. Initiates outbound calls to all contacts

    User never interacts with Twilio/LiveKit directly!
    """
    user_id = current_user["user_id"]

    logger.info(f"User {user_id} launching campaign for survey {request.survey_id}")

    try:
        db = get_db()

        # 1. Verify survey belongs to user
        survey_response = db.table("surveys").select("*").eq("survey_id", request.survey_id).eq("user_id", user_id).execute()

        if not survey_response.data:
            raise HTTPException(status_code=404, detail="Survey not found or access denied")

        survey = survey_response.data[0]

        # 2. Get or provision phone number
        phone_number = await phone_provisioning.get_or_provision_number(user_id)

        logger.info(f"Phone number for campaign: {phone_number}")

        # 3. Get or create SIP trunk
        trunk_id = await sip_trunk_provisioning.get_or_create_trunk(user_id, phone_number)

        logger.info(f"SIP trunk for campaign: {trunk_id}")

        # 4. Get contacts for this survey
        contacts_response = db.table("contact").select("*").eq("survey_id", request.survey_id).execute()

        if not contacts_response.data:
            raise HTTPException(status_code=400, detail="No contacts found for this survey")

        contacts = contacts_response.data

        # Test mode: only call first contact
        if request.test_mode:
            contacts = contacts[:1]
            logger.info("Test mode: calling only first contact")

        # 5. Update survey status
        db.table("surveys").update({
            "status": "active"
        }).eq("survey_id", request.survey_id).execute()

        # 6. Initiate calls in background
        background_tasks.add_task(
            execute_campaign_calls,
            survey_id=request.survey_id,
            contacts=contacts,
            trunk_id=trunk_id,
            phone_number=phone_number
        )

        # 7. Calculate estimated duration (assume 3 min per call on average)
        estimated_duration = len(contacts) * 3

        return LaunchCampaignResponse(
            status="launching",
            campaign_id=request.survey_id,
            phone_number=phone_number,
            total_contacts=len(contacts),
            estimated_duration_minutes=estimated_duration,
            message=f"Survey campaign launched! Calling from {phone_number}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to launch campaign: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to launch campaign: {str(e)}")


@router.get("/{survey_id}/status", response_model=CampaignStatusResponse)
async def get_campaign_status(
    survey_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get real-time campaign status and statistics.

    Shows:
    - Total contacts
    - Calls completed, in progress, failed, pending
    - Completion percentage
    """
    user_id = current_user["user_id"]

    try:
        db = get_db()

        # Verify ownership
        survey = db.table("surveys").select("*").eq("survey_id", survey_id).eq("user_id", user_id).execute()

        if not survey.data:
            raise HTTPException(status_code=404, detail="Survey not found")

        survey_data = survey.data[0]

        # Get user's phone number
        user_data = db.table("users").select("twilio_phone_number").eq("user_id", user_id).execute()
        phone_number = user_data.data[0].get("twilio_phone_number") if user_data.data else None

        # Get all contacts
        all_contacts = db.table("contact").select("contact_id").eq("survey_id", survey_id).execute()
        total_contacts = len(all_contacts.data)

        # Get call logs and count by status
        call_logs = db.table("call_logs").select("status").in_("contact_id", [c["contact_id"] for c in all_contacts.data]).execute()

        status_counts = {
            "completed": 0,
            "in_progress": 0,
            "failed": 0
        }

        for log in call_logs.data:
            status = log.get("status", "pending")
            if status in status_counts:
                status_counts[status] += 1

        pending = total_contacts - sum(status_counts.values())

        completion_pct = (status_counts["completed"] / total_contacts * 100) if total_contacts > 0 else 0

        return CampaignStatusResponse(
            campaign_id=survey_id,
            status=survey_data.get("status", "unknown"),
            phone_number=phone_number or "Not provisioned",
            total_contacts=total_contacts,
            completed_calls=status_counts["completed"],
            in_progress_calls=status_counts["in_progress"],
            failed_calls=status_counts["failed"],
            pending_calls=pending,
            completion_percentage=round(completion_pct, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get campaign status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get campaign status")


@router.get("/phone-number", response_model=PhoneNumberInfo)
async def get_phone_number_info(current_user: Dict = Depends(get_current_user)):
    """
    Get user's phone number information.

    Shows if they have a number provisioned and its details.
    """
    user_id = current_user["user_id"]

    try:
        db = get_db()
        user = db.table("users").select(
            "twilio_phone_number, phone_provisioned_at, livekit_trunk_id"
        ).eq("user_id", user_id).execute()

        if not user.data:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user.data[0]

        phone_number = user_data.get("twilio_phone_number")
        status = "provisioned" if phone_number else "not_provisioned"

        return PhoneNumberInfo(
            phone_number=phone_number,
            status=status,
            provisioned_at=user_data.get("phone_provisioned_at"),
            trunk_id=user_data.get("livekit_trunk_id")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get phone info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get phone number info")


@router.post("/provision-number")
async def provision_number_manually(current_user: Dict = Depends(get_current_user)):
    """
    Manually provision a phone number for the user.

    Usually not needed since numbers are auto-provisioned on campaign launch,
    but useful for pre-provisioning or testing.
    """
    user_id = current_user["user_id"]

    try:
        # Check if already has number
        db = get_db()
        user = db.table("users").select("twilio_phone_number").eq("user_id", user_id).execute()

        if user.data and user.data[0].get("twilio_phone_number"):
            return {
                "status": "already_provisioned",
                "phone_number": user.data[0]["twilio_phone_number"]
            }

        # Provision new number
        result = await phone_provisioning.provision_phone_number(user_id)

        # Create SIP trunk
        await sip_trunk_provisioning.create_sip_trunk_for_user(user_id, result["phone_number"])

        return {
            "status": "provisioned",
            "phone_number": result["phone_number"],
            "message": "Phone number successfully provisioned"
        }

    except Exception as e:
        logger.error(f"Failed to provision number: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to provision number: {str(e)}")


# ============================================
# Background Tasks
# ============================================

async def execute_campaign_calls(
    survey_id: str,
    contacts: List[Dict[str, Any]],
    trunk_id: str,
    phone_number: str
):
    """
    Background task to execute all campaign calls.

    Calls are made sequentially with small delays to avoid overwhelming the system.
    """
    import asyncio

    logger.info(f"Starting campaign calls for survey {survey_id}: {len(contacts)} contacts")

    db = get_db()

    for idx, contact in enumerate(contacts, 1):
        try:
            logger.info(f"Call {idx}/{len(contacts)}: {contact['phone_number']}")

            # Initiate call
            result = await initiate_outbound_call(
                to_phone=contact["phone_number"],
                survey_id=survey_id,
                contact_id=contact["contact_id"]
            )

            logger.info(f"Call initiated: {result['call_sid']}")

            # Small delay between calls (avoid rate limits)
            if idx < len(contacts):
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Failed to call {contact['phone_number']}: {e}")

            # Mark as failed in database
            try:
                db.table("contact").update({
                    "call_status": "failed",
                    "last_call_error": str(e)
                }).eq("contact_id", contact["contact_id"]).execute()
            except:
                pass

    # Update campaign status to closed
    try:
        db.table("surveys").update({
            "status": "closed"
        }).eq("survey_id", survey_id).execute()

        logger.info(f"Campaign completed for survey {survey_id}")
    except Exception as e:
        logger.error(f"Failed to update campaign status: {e}")
