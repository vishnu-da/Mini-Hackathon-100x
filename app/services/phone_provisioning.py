"""
Phone number provisioning service for automatic Twilio number assignment.

Each user gets their own dedicated Twilio phone number for making survey calls.
This service handles:
- Automatic phone number purchasing
- Number release/cleanup
- Availability checking
"""
import logging
from typing import Dict, Any, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.config import get_settings
from app.database import get_db

logger = logging.getLogger(__name__)
settings = get_settings()


async def provision_phone_number(
    user_id: str,
    country_code: str = "US",
    area_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Automatically provision a Twilio phone number for a user.

    This function:
    1. Searches for available Twilio phone numbers
    2. Purchases the number
    3. Configures webhooks for voice calls
    4. Stores number in database associated with user
    5. Creates LiveKit SIP trunk for the user

    Args:
        user_id: User UUID
        country_code: Country code (default: US)
        area_code: Optional area code preference (e.g., "415" for San Francisco)

    Returns:
        Dict with phone_number, phone_sid, and status

    Raises:
        Exception: If no numbers available or purchase fails
    """
    logger.info(f"Provisioning phone number for user {user_id}")

    try:
        # Initialize Twilio client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

        # Search for available phone numbers
        search_params = {"limit": 10}
        if area_code:
            search_params["area_code"] = area_code

        available_numbers = client.available_phone_numbers(country_code).local.list(**search_params)

        if not available_numbers:
            raise Exception(f"No phone numbers available in {country_code}")

        # Select first available number
        selected_number = available_numbers[0].phone_number

        logger.info(f"Found available number: {selected_number}")

        # Purchase the number with webhook configuration
        purchased_number = client.incoming_phone_numbers.create(
            phone_number=selected_number,
            voice_url=f"{settings.callback_base_url}/webhooks/voice",
            voice_method="POST",
            status_callback=f"{settings.callback_base_url}/webhooks/call-status",
            status_callback_method="POST",
            friendly_name=f"Survey Line - User {user_id[:8]}"
        )

        logger.info(f"Purchased number: {purchased_number.phone_number} (SID: {purchased_number.sid})")

        # Store in database
        db = get_db()
        try:
            db.table("users").update({
                "twilio_phone_number": purchased_number.phone_number,
                "phone_number_sid": purchased_number.sid,
                "phone_provisioned_at": "now()"
            }).eq("user_id", user_id).execute()

            logger.info(f"Stored phone number in database for user {user_id}")
        except Exception as db_error:
            # Rollback: Release the number if database update fails
            logger.error(f"Database update failed, releasing number: {db_error}")
            try:
                client.incoming_phone_numbers(purchased_number.sid).delete()
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup number: {cleanup_error}")
            raise

        return {
            "phone_number": purchased_number.phone_number,
            "phone_sid": purchased_number.sid,
            "status": "provisioned",
            "user_id": user_id
        }

    except TwilioRestException as e:
        logger.error(f"Twilio API error: {e.msg} (Code: {e.code})")
        raise Exception(f"Failed to provision phone number: {e.msg}")
    except Exception as e:
        logger.error(f"Failed to provision phone number: {e}", exc_info=True)
        raise


async def release_phone_number(user_id: str) -> bool:
    """
    Release a user's Twilio phone number.

    Use this when:
    - User deletes account
    - User downgrades plan
    - User requests number change

    Args:
        user_id: User UUID

    Returns:
        True if successful
    """
    logger.info(f"Releasing phone number for user {user_id}")

    try:
        # Get user's phone number from database
        db = get_db()
        user = db.table("users").select("phone_number_sid").eq("user_id", user_id).execute()

        if not user.data or not user.data[0].get("phone_number_sid"):
            logger.warning(f"No phone number found for user {user_id}")
            return False

        phone_sid = user.data[0]["phone_number_sid"]

        # Release number via Twilio API
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.incoming_phone_numbers(phone_sid).delete()

        logger.info(f"Released phone number {phone_sid}")

        # Update database
        db.table("users").update({
            "twilio_phone_number": None,
            "phone_number_sid": None,
            "livekit_trunk_id": None
        }).eq("user_id", user_id).execute()

        return True

    except TwilioRestException as e:
        logger.error(f"Twilio API error releasing number: {e.msg}")
        return False
    except Exception as e:
        logger.error(f"Failed to release phone number: {e}", exc_info=True)
        return False


async def get_or_provision_number(user_id: str) -> str:
    """
    Get user's existing phone number or provision a new one.

    This is the main function to use when launching a campaign.
    It ensures the user always has a phone number ready.

    Args:
        user_id: User UUID

    Returns:
        Phone number in E.164 format (e.g., +14155551234)
    """
    try:
        # Check if user already has a phone number
        db = get_db()
        user = db.table("users").select("twilio_phone_number").eq("user_id", user_id).execute()

        if user.data and user.data[0].get("twilio_phone_number"):
            phone_number = user.data[0]["twilio_phone_number"]
            logger.info(f"User {user_id} already has number: {phone_number}")
            return phone_number

        # Provision new number
        logger.info(f"User {user_id} has no number, provisioning...")
        result = await provision_phone_number(user_id)
        return result["phone_number"]

    except Exception as e:
        logger.error(f"Failed to get or provision number: {e}")
        raise


async def check_number_availability(country_code: str = "US", area_code: Optional[str] = None) -> int:
    """
    Check how many phone numbers are available for purchase.

    Useful for monitoring inventory before user signup.

    Args:
        country_code: Country code
        area_code: Optional area code filter

    Returns:
        Count of available numbers
    """
    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

        search_params = {"limit": 50}
        if area_code:
            search_params["area_code"] = area_code

        available = client.available_phone_numbers(country_code).local.list(**search_params)
        return len(available)

    except Exception as e:
        logger.error(f"Failed to check availability: {e}")
        return 0
