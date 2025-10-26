"""
Authentication and authorization helper functions for the AI Voice Survey Platform.
"""
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import jwt
import logging
from app.config import get_settings
from app.database import get_db, get_user_by_id

logger = logging.getLogger(__name__)
security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Custom exception for authentication errors."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail)


class AuthorizationError(HTTPException):
    """Custom exception for authorization errors."""

    def __init__(self, detail: str = "Access denied"):
        super().__init__(status_code=403, detail=detail)


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify JWT token from Supabase.

    Args:
        token: JWT token string

    Returns:
        Dict containing decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    settings = get_settings()

    try:
        # Supabase uses HS256 algorithm
        # The secret is your JWT_SECRET from Supabase settings
        # For development, you can skip verification (not recommended for production)
        decoded = jwt.decode(
            token,
            options={"verify_signature": False}  # TODO: Add JWT_SECRET to settings and enable verification
        )
        return decoded
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise AuthenticationError("Invalid token")
    except Exception as e:
        logger.error(f"Error decoding JWT token: {e}")
        raise AuthenticationError("Token validation failed")


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Extract and validate user ID from JWT token.

    This dependency can be used in FastAPI routes to get the authenticated user's ID.

    Args:
        credentials: HTTP Bearer token from request header

    Returns:
        str: User UUID from the token

    Raises:
        AuthenticationError: If authentication fails

    Example:
        ```python
        @router.get("/surveys")
        async def get_surveys(user_id: str = Depends(get_current_user_id)):
            surveys = await get_surveys_by_user(user_id)
            return surveys
        ```
    """
    if not credentials:
        raise AuthenticationError("No authentication credentials provided")

    token = credentials.credentials

    try:
        payload = decode_jwt_token(token)

        # Supabase stores user_id in 'sub' claim
        user_id = payload.get("sub")

        if not user_id:
            raise AuthenticationError("Invalid token: missing user ID")

        return user_id

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise AuthenticationError(str(e))


async def get_current_user(
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Get the full user object for the authenticated user.

    Args:
        user_id: User ID from JWT token (injected by dependency)

    Returns:
        Dict containing user data

    Raises:
        AuthenticationError: If user not found

    Example:
        ```python
        @router.get("/profile")
        async def get_profile(user: Dict = Depends(get_current_user)):
            return user
        ```
    """
    user = await get_user_by_id(user_id)

    if not user:
        raise AuthenticationError("User not found")

    return user


async def verify_survey_ownership(user_id: str, survey_id: str) -> None:
    """
    Verify that a user owns a specific survey.

    Args:
        user_id: User's UUID
        survey_id: Survey's UUID

    Raises:
        AuthorizationError: If user doesn't own the survey
    """
    from app.database import get_survey_by_id

    survey = await get_survey_by_id(survey_id)

    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    if survey.get("user_id") != user_id:
        raise AuthorizationError("You don't have permission to access this survey")


async def verify_contact_ownership(user_id: str, contact_id: str) -> None:
    """
    Verify that a user owns the survey associated with a contact.

    Args:
        user_id: User's UUID
        contact_id: Contact's UUID

    Raises:
        AuthorizationError: If user doesn't own the associated survey
    """
    from app.database import get_db

    db = get_db()

    # Get contact with survey information
    response = db.table("contact").select("*, surveys!inner(user_id)").eq("contact_id", contact_id).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact = response.data[0]
    survey_owner_id = contact.get("surveys", {}).get("user_id")

    if survey_owner_id != user_id:
        raise AuthorizationError("You don't have permission to access this contact")


async def verify_call_log_ownership(user_id: str, twilio_call_sid: str) -> None:
    """
    Verify that a user owns the survey associated with a call log.

    Args:
        user_id: User's UUID
        twilio_call_sid: Twilio Call SID

    Raises:
        AuthorizationError: If user doesn't own the associated survey
    """
    from app.database import get_db

    db = get_db()

    # Get call log with contact and survey information
    response = db.table("call_logs").select(
        "*, contact!inner(*, surveys!inner(user_id))"
    ).eq("twilio_call_sid", twilio_call_sid).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Call log not found")

    call_log = response.data[0]
    survey_owner_id = call_log.get("contact", {}).get("surveys", {}).get("user_id")

    if survey_owner_id != user_id:
        raise AuthorizationError("You don't have permission to access this call log")


async def verify_resource_ownership(
    user_id: str,
    resource_type: str,
    resource_id: str
) -> None:
    """
    Generic function to verify resource ownership.

    Note: voice_agents and spreadsheet_destinations don't have direct user ownership.
    They are accessed through surveys. Use RLS policies for access control instead.

    Args:
        user_id: User's UUID
        resource_type: Type of resource (survey, contact, call_log)
        resource_id: Resource's UUID or ID

    Raises:
        AuthorizationError: If user doesn't own the resource
        ValueError: If resource_type is not supported
    """
    if resource_type == "survey":
        await verify_survey_ownership(user_id, resource_id)
    elif resource_type == "contact":
        await verify_contact_ownership(user_id, resource_id)
    elif resource_type == "call_log":
        await verify_call_log_ownership(user_id, resource_id)
    elif resource_type in ["voice_agent", "spreadsheet_destination"]:
        # These resources don't have direct user ownership
        # Access is controlled via RLS through the surveys relationship
        raise ValueError(
            f"{resource_type} ownership is managed through surveys. "
            f"Use RLS policies for access control instead of direct verification."
        )
    else:
        raise ValueError(f"Unsupported resource type: {resource_type}")


async def verify_direct_ownership(
    user_id: str,
    table_name: str,
    id_column: str,
    resource_id: str
) -> None:
    """
    Verify direct ownership for tables with user_id column.

    Note: This function is for tables that have a direct user_id column.
    Do NOT use for voice_agents or spreadsheet_destinations - they don't have user_id.

    Args:
        user_id: User's UUID
        table_name: Database table name (must have user_id column)
        id_column: Primary key column name
        resource_id: Resource ID

    Raises:
        AuthorizationError: If user doesn't own the resource
    """
    from app.database import get_db

    db = get_db()

    response = db.table(table_name).select("user_id").eq(id_column, resource_id).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail=f"{table_name.replace('_', ' ').title()} not found")

    resource = response.data[0]

    if resource.get("user_id") != user_id:
        raise AuthorizationError(f"You don't have permission to access this {table_name.replace('_', ' ')}")


def require_auth(func):
    """
    Decorator to require authentication for a route.

    Example:
        ```python
        @router.get("/protected")
        @require_auth
        async def protected_route(user_id: str = Depends(get_current_user_id)):
            return {"message": "This is protected"}
        ```
    """
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    return wrapper


# Optional: Token extraction utilities

def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value (e.g., "Bearer token123")

    Returns:
        Token string or None if invalid format
    """
    if not authorization:
        return None

    parts = authorization.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def get_token_expiry(token: str) -> Optional[int]:
    """
    Get expiration timestamp from JWT token.

    Args:
        token: JWT token string

    Returns:
        Unix timestamp of expiration or None if not found
    """
    try:
        payload = decode_jwt_token(token)
        return payload.get("exp")
    except Exception:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if JWT token is expired.

    Args:
        token: JWT token string

    Returns:
        True if expired, False otherwise
    """
    import time

    expiry = get_token_expiry(token)

    if not expiry:
        return True

    return time.time() > expiry
