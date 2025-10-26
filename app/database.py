"""
Supabase database client initialization and management.
"""
from supabase import create_client, Client
from functools import lru_cache
from typing import Dict, List, Any, Optional
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)


@lru_cache()
def get_supabase_client() -> Client:
    """
    Get cached Supabase client instance with service key.

    Uses service key to bypass RLS policies for backend operations.
    Using lru_cache ensures only one client is created.

    Returns:
        Client: Supabase client instance with service key
    """
    settings = get_settings()
    supabase: Client = create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_key
    )
    return supabase


def get_supabase_user_client(access_token: str) -> Client:
    """
    Get Supabase client with user's access token.

    Uses user's JWT token to respect RLS (Row Level Security) policies.
    This allows operations to be performed with user's permissions.

    Args:
        access_token: User's JWT access token from Supabase auth

    Returns:
        Client: Supabase client instance with user's token
    """
    settings = get_settings()

    # Create client with anon key
    supabase: Client = create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_key
    )

    # Set the user's access token for subsequent requests
    supabase.auth.set_session(access_token, access_token)

    return supabase


def get_db() -> Client:
    """
    Dependency function to get Supabase client for FastAPI routes.

    Returns Supabase client with service key for backend operations.

    Returns:
        Client: Supabase client instance
    """
    return get_supabase_client()


# ============================================================================
# TABLE HELPER FUNCTIONS
# ============================================================================

class DatabaseTables:
    """Helper class for database table operations."""

    USERS = "users"
    VOICE_AGENTS = "voice_agents"
    SPREADSHEET_DESTINATIONS = "spreadsheet_destinations"
    SURVEYS = "surveys"
    CONTACT = "contact"
    CALL_LOGS = "call_logs"


# ============================================================================
# USERS TABLE OPERATIONS
# ============================================================================

async def create_user(email: str, phone_number: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new user in the database.

    Args:
        email: User's email address
        phone_number: User's phone number (optional)
        name: User's name (optional)

    Returns:
        Dict containing the created user data
    """
    db = get_db()
    try:
        response = db.table(DatabaseTables.USERS).insert({
            "email": email,
            "phone_number": phone_number,
            "name": name
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    db = get_db()
    try:
        response = db.table(DatabaseTables.USERS).select("*").eq("user_id", user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    db = get_db()
    try:
        response = db.table(DatabaseTables.USERS).select("*").eq("email", email).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        raise


# ============================================================================
# SURVEYS TABLE OPERATIONS
# ============================================================================

async def create_survey(survey_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new survey.

    Args:
        survey_data: Dictionary containing survey information

    Returns:
        Dict containing the created survey data
    """
    db = get_db()
    try:
        response = db.table(DatabaseTables.SURVEYS).insert(survey_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating survey: {e}")
        raise


async def get_survey_by_id(survey_id: str) -> Optional[Dict[str, Any]]:
    """Get survey by ID."""
    db = get_db()
    try:
        response = db.table(DatabaseTables.SURVEYS).select("*").eq("survey_id", survey_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error getting survey: {e}")
        raise


async def get_surveys_by_user(user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all surveys for a user, optionally filtered by status.

    Args:
        user_id: User's ID
        status: Optional status filter

    Returns:
        List of surveys
    """
    db = get_db()
    try:
        query = db.table(DatabaseTables.SURVEYS).select("*").eq("user_id", user_id)
        if status:
            query = query.eq("status", status)
        response = query.order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error getting surveys: {e}")
        raise


async def update_survey(survey_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update survey data."""
    db = get_db()
    try:
        response = db.table(DatabaseTables.SURVEYS).update(updates).eq("survey_id", survey_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating survey: {e}")
        raise


# ============================================================================
# CONTACT TABLE OPERATIONS
# ============================================================================

async def create_contact(contact_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new contact."""
    db = get_db()
    try:
        response = db.table(DatabaseTables.CONTACT).insert(contact_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating contact: {e}")
        raise


async def get_contacts_by_survey(survey_id: str) -> List[Dict[str, Any]]:
    """Get all contacts for a survey."""
    db = get_db()
    try:
        response = db.table(DatabaseTables.CONTACT).select("*").eq("survey_id", survey_id).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error getting contacts: {e}")
        raise


async def bulk_create_contacts(contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bulk create contacts."""
    db = get_db()
    try:
        response = db.table(DatabaseTables.CONTACT).insert(contacts).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error bulk creating contacts: {e}")
        raise


# ============================================================================
# CALL LOGS TABLE OPERATIONS
# ============================================================================

async def create_call_log(call_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new call log entry."""
    db = get_db()
    try:
        response = db.table(DatabaseTables.CALL_LOGS).insert(call_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating call log: {e}")
        raise


async def update_call_log(twilio_call_sid: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update call log data."""
    db = get_db()
    try:
        response = db.table(DatabaseTables.CALL_LOGS).update(updates).eq("twilio_call_sid", twilio_call_sid).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating call log: {e}")
        raise


async def get_call_logs_by_contact(contact_id: str) -> List[Dict[str, Any]]:
    """Get all call logs for a contact."""
    db = get_db()
    try:
        response = db.table(DatabaseTables.CALL_LOGS).select("*").eq("contact_id", contact_id).order("call_timestamp", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error getting call logs: {e}")
        raise


async def get_call_log_by_sid(twilio_call_sid: str) -> Optional[Dict[str, Any]]:
    """Get call log by Twilio Call SID."""
    db = get_db()
    try:
        response = db.table(DatabaseTables.CALL_LOGS).select("*").eq("twilio_call_sid", twilio_call_sid).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error getting call log: {e}")
        raise


# ============================================================================
# VOICE AGENTS TABLE OPERATIONS
# ============================================================================
# Note: voice_agents table does not have user_id column.
# Ownership is derived through the surveys relationship.
# RLS policies automatically enforce access control via surveys.user_id.
# Users can only access voice agents that are referenced by their surveys.

async def create_voice_agent(model_name: str, tools_functions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a new voice agent configuration.

    Note: Voice agents are not directly owned by users. Access is controlled
    through surveys that reference them.
    """
    db = get_db()
    try:
        response = db.table(DatabaseTables.VOICE_AGENTS).insert({
            "model_name": model_name,
            "tools_functions": tools_functions
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating voice agent: {e}")
        raise


async def get_voice_agent_by_id(voice_agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Get voice agent by ID.

    Note: RLS policies ensure users can only access voice agents referenced
    by their surveys.
    """
    db = get_db()
    try:
        response = db.table(DatabaseTables.VOICE_AGENTS).select("*").eq("voice_agent_id", voice_agent_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error getting voice agent: {e}")
        raise


# ============================================================================
# SPREADSHEET DESTINATIONS TABLE OPERATIONS
# ============================================================================
# Note: spreadsheet_destinations table does not have user_id column.
# Ownership is derived through the surveys relationship.
# RLS policies automatically enforce access control via surveys.user_id.
# Users can only access destinations that are referenced by their surveys.

async def create_spreadsheet_destination(destination_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new spreadsheet destination.

    Note: Spreadsheet destinations are not directly owned by users. Access is
    controlled through surveys that reference them.
    """
    db = get_db()
    try:
        response = db.table(DatabaseTables.SPREADSHEET_DESTINATIONS).insert(destination_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating spreadsheet destination: {e}")
        raise


async def get_spreadsheet_destination_by_id(destination_id: str) -> Optional[Dict[str, Any]]:
    """
    Get spreadsheet destination by ID.

    Note: RLS policies ensure users can only access destinations referenced
    by their surveys.
    """
    db = get_db()
    try:
        response = db.table(DatabaseTables.SPREADSHEET_DESTINATIONS).select("*").eq("destination_id", destination_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error getting spreadsheet destination: {e}")
        raise


# ============================================================================
# OAUTH TOKENS TABLE OPERATIONS
# ============================================================================

async def get_oauth_token(user_id: str, provider: str) -> Optional[Dict[str, Any]]:
    """
    Get OAuth token for user and provider.

    Args:
        user_id: User's UUID
        provider: OAuth provider ('google' or 'microsoft')

    Returns:
        Token data or None if not found
    """
    db = get_db()
    try:
        response = db.table("oauth_tokens").select("*").eq("user_id", user_id).eq("provider", provider).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error getting OAuth token: {e}")
        raise


async def store_oauth_token(user_id: str, provider: str, token_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store or update OAuth token.

    Args:
        user_id: User's UUID
        provider: OAuth provider ('google' or 'microsoft')
        token_data: Token information to store

    Returns:
        Stored token record
    """
    db = get_db()
    try:
        # Upsert token (insert or update if exists)
        response = db.table("oauth_tokens").upsert({
            "user_id": user_id,
            "provider": provider,
            **token_data
        }, on_conflict="user_id,provider").execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error storing OAuth token: {e}")
        raise


async def delete_oauth_token(user_id: str, provider: str) -> None:
    """
    Delete OAuth token.

    Args:
        user_id: User's UUID
        provider: OAuth provider ('google' or 'microsoft')
    """
    db = get_db()
    try:
        db.table("oauth_tokens").delete().eq("user_id", user_id).eq("provider", provider).execute()
        logger.info(f"Deleted {provider} OAuth token for user {user_id}")
    except Exception as e:
        logger.error(f"Error deleting OAuth token: {e}")
        raise


async def get_user_oauth_tokens(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all OAuth tokens for a user.

    Args:
        user_id: User's UUID

    Returns:
        List of token records
    """
    db = get_db()
    try:
        response = db.table("oauth_tokens").select("provider, expires_at, scope").eq("user_id", user_id).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error getting user OAuth tokens: {e}")
        raise
