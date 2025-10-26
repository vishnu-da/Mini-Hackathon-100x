"""
LiveKit SIP trunk provisioning service.

Creates and manages per-user SIP trunks for outbound calling via Twilio.
Each user gets their own dedicated trunk configured with their Twilio credentials.
"""
import logging
from typing import Dict, Any, Optional
from livekit import api

from app.config import get_settings
from app.database import get_db

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_sip_trunk_for_user(
    user_id: str,
    phone_number: str,
    twilio_username: Optional[str] = None,
    twilio_password: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a LiveKit SIP trunk for a user's Twilio phone number.

    This trunk enables outbound calling from LiveKit agents through Twilio.

    Args:
        user_id: User UUID
        phone_number: User's Twilio phone number (E.164 format)
        twilio_username: Twilio SIP username (defaults to account SID)
        twilio_password: Twilio SIP password (defaults to auth token)

    Returns:
        Dict with trunk_id, trunk_name, and configuration

    Raises:
        Exception: If trunk creation fails
    """
    logger.info(f"Creating SIP trunk for user {user_id} with number {phone_number}")

    try:
        # Default to Twilio account credentials if not provided
        if not twilio_username:
            twilio_username = settings.twilio_account_sid
        if not twilio_password:
            twilio_password = settings.twilio_auth_token

        # Initialize LiveKit API client
        lk_api = api.LiveKitAPI(
            settings.livekit_url,
            settings.livekit_api_key,
            settings.livekit_api_secret
        )

        # Generate unique trunk name
        trunk_name = f"user-{user_id[:8]}-trunk"

        # Twilio SIP domain (same for all users, but each has own credentials)
        twilio_sip_domain = "reso.pstn.twilio.com"

        # Create outbound SIP trunk
        trunk = await lk_api.sip.create_sip_outbound_trunk(
            api.CreateSIPOutboundTrunkRequest(
                trunk=api.SIPOutboundTrunkInfo(
                    name=trunk_name,
                    address=twilio_sip_domain,
                    transport=api.SIPTransport.SIP_TRANSPORT_UDP,
                    numbers=[phone_number],
                    auth_username=twilio_username,
                    auth_password=twilio_password,
                )
            )
        )

        trunk_id = trunk.sip_trunk_id

        logger.info(f"Created SIP trunk: {trunk_id} for user {user_id}")

        # Store in database
        db = get_db()
        try:
            # Update users table
            db.table("users").update({
                "livekit_trunk_id": trunk_id
            }).eq("user_id", user_id).execute()

            # Store in sip_trunks table
            db.table("sip_trunks").insert({
                "user_id": user_id,
                "livekit_trunk_id": trunk_id,
                "trunk_name": trunk_name,
                "sip_address": twilio_sip_domain,
                "phone_number": phone_number,
                "auth_username": twilio_username
            }).execute()

            logger.info(f"Stored SIP trunk configuration for user {user_id}")
        except Exception as db_error:
            logger.error(f"Database update failed: {db_error}")
            # Attempt cleanup
            try:
                await lk_api.sip.delete_sip_trunk(
                    api.DeleteSIPTrunkRequest(sip_trunk_id=trunk_id)
                )
            except:
                pass
            raise

        # Close API client
        await lk_api.aclose()

        return {
            "trunk_id": trunk_id,
            "trunk_name": trunk_name,
            "phone_number": phone_number,
            "sip_address": twilio_sip_domain,
            "status": "created"
        }

    except Exception as e:
        logger.error(f"Failed to create SIP trunk: {e}", exc_info=True)
        raise


async def delete_sip_trunk(user_id: str) -> bool:
    """
    Delete a user's LiveKit SIP trunk.

    Args:
        user_id: User UUID

    Returns:
        True if successful
    """
    logger.info(f"Deleting SIP trunk for user {user_id}")

    try:
        # Get trunk ID from database
        db = get_db()
        user = db.table("users").select("livekit_trunk_id").eq("user_id", user_id).execute()

        if not user.data or not user.data[0].get("livekit_trunk_id"):
            logger.warning(f"No SIP trunk found for user {user_id}")
            return False

        trunk_id = user.data[0]["livekit_trunk_id"]

        # Delete via LiveKit API
        lk_api = api.LiveKitAPI(
            settings.livekit_url,
            settings.livekit_api_key,
            settings.livekit_api_secret
        )

        await lk_api.sip.delete_sip_trunk(
            api.DeleteSIPTrunkRequest(sip_trunk_id=trunk_id)
        )

        logger.info(f"Deleted SIP trunk: {trunk_id}")

        # Close API client
        await lk_api.aclose()

        # Update database
        db.table("users").update({
            "livekit_trunk_id": None
        }).eq("user_id", user_id).execute()

        db.table("sip_trunks").update({
            "deleted_at": "now()"
        }).eq("livekit_trunk_id", trunk_id).execute()

        return True

    except Exception as e:
        logger.error(f"Failed to delete SIP trunk: {e}", exc_info=True)
        return False


async def get_or_create_trunk(user_id: str, phone_number: str) -> str:
    """
    Get user's existing SIP trunk ID or create a new one.

    Args:
        user_id: User UUID
        phone_number: User's phone number

    Returns:
        SIP trunk ID
    """
    try:
        # Check if user already has a trunk
        db = get_db()
        user = db.table("users").select("livekit_trunk_id").eq("user_id", user_id).execute()

        if user.data and user.data[0].get("livekit_trunk_id"):
            trunk_id = user.data[0]["livekit_trunk_id"]
            logger.info(f"User {user_id} already has trunk: {trunk_id}")
            return trunk_id

        # Create new trunk
        logger.info(f"User {user_id} has no trunk, creating...")
        result = await create_sip_trunk_for_user(user_id, phone_number)
        return result["trunk_id"]

    except Exception as e:
        logger.error(f"Failed to get or create trunk: {e}")
        raise


async def verify_trunk_configuration(trunk_id: str) -> Dict[str, Any]:
    """
    Verify SIP trunk configuration is correct.

    Useful for debugging and monitoring.

    Args:
        trunk_id: LiveKit SIP trunk ID

    Returns:
        Dict with trunk details and status
    """
    try:
        lk_api = api.LiveKitAPI(
            settings.livekit_url,
            settings.livekit_api_key,
            settings.livekit_api_secret
        )

        # List all trunks and find the one we want
        result = await lk_api.sip.list_sip_outbound_trunk(
            api.ListSIPOutboundTrunkRequest()
        )

        trunk_info = None
        for trunk in result.items:
            if trunk.sip_trunk_id == trunk_id:
                trunk_info = trunk
                break

        await lk_api.aclose()

        if not trunk_info:
            return {"status": "not_found", "trunk_id": trunk_id}

        return {
            "status": "active",
            "trunk_id": trunk_info.sip_trunk_id,
            "name": trunk_info.name,
            "address": trunk_info.address,
            "numbers": trunk_info.numbers,
            "has_auth": bool(trunk_info.auth_username)
        }

    except Exception as e:
        logger.error(f"Failed to verify trunk: {e}")
        return {"status": "error", "error": str(e)}
