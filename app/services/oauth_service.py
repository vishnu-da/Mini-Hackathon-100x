"""
OAuth 2.0 service for managing Google and Microsoft authentication.
Handles token storage, refresh, and validation.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import httpx
from app.config import get_settings
from app.database import get_db

logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Base exception for OAuth errors."""
    pass


class TokenExpiredError(OAuthError):
    """Raised when token is expired and cannot be refreshed."""
    pass


class TokenNotFoundError(OAuthError):
    """Raised when no token exists for user/provider."""
    pass


# ============================================================================
# GOOGLE OAUTH FUNCTIONS
# ============================================================================

def get_google_auth_url(state: str) -> str:
    """
    Generate Google OAuth 2.0 authorization URL.

    Args:
        state: CSRF protection state parameter

    Returns:
        Authorization URL for user to visit
    """
    settings = get_settings()

    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": settings.google_forms_scope,
        "state": state,
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Force consent screen to get refresh token
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    logger.info(f"Generated Google OAuth URL with state: {state}")

    return auth_url


async def exchange_google_code(code: str, user_id: str) -> Dict[str, Any]:
    """
    Exchange Google authorization code for access tokens.

    Args:
        code: Authorization code from OAuth callback
        user_id: User's UUID

    Returns:
        Token information dictionary

    Raises:
        OAuthError: If exchange fails
    """
    settings = get_settings()
    db = get_db()

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        scope = token_data.get("scope", "")

        if not access_token:
            raise OAuthError("No access token in response")

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Store in database (upsert)
        db.table("oauth_tokens").upsert({
            "user_id": user_id,
            "provider": "google",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_at": expires_at.isoformat(),
            "scope": scope,
        }, on_conflict="user_id,provider").execute()

        logger.info(f"Stored Google OAuth tokens for user {user_id}")

        return {
            "provider": "google",
            "expires_at": expires_at.isoformat(),
            "scope": scope,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error exchanging Google code: {e}")
        raise OAuthError(f"Failed to exchange authorization code: {e.response.text}")
    except Exception as e:
        logger.error(f"Error exchanging Google code: {e}")
        raise OAuthError(f"Failed to exchange authorization code: {str(e)}")


async def refresh_google_token(user_id: str) -> Dict[str, Any]:
    """
    Refresh Google OAuth access token.

    Args:
        user_id: User's UUID

    Returns:
        Updated token information

    Raises:
        TokenNotFoundError: If no token exists
        OAuthError: If refresh fails
    """
    settings = get_settings()
    db = get_db()

    # Get stored token
    response = db.table("oauth_tokens").select("*").eq("user_id", user_id).eq("provider", "google").execute()

    if not response.data:
        raise TokenNotFoundError(f"No Google token found for user {user_id}")

    token_record = response.data[0]
    refresh_token = token_record.get("refresh_token")

    if not refresh_token:
        raise OAuthError("No refresh token available - user needs to re-authorize")

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            raise OAuthError("No access token in refresh response")

        # Calculate new expiration
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        db.table("oauth_tokens").update({
            "access_token": access_token,
            "expires_at": expires_at.isoformat(),
        }).eq("user_id", user_id).eq("provider", "google").execute()

        logger.info(f"Refreshed Google OAuth token for user {user_id}")

        return {
            "provider": "google",
            "expires_at": expires_at.isoformat(),
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error refreshing Google token: {e}")
        raise OAuthError(f"Failed to refresh token: {e.response.text}")
    except Exception as e:
        logger.error(f"Error refreshing Google token: {e}")
        raise OAuthError(f"Failed to refresh token: {str(e)}")


# ============================================================================
# MICROSOFT OAUTH FUNCTIONS
# ============================================================================

def get_microsoft_auth_url(state: str) -> str:
    """
    Generate Microsoft OAuth 2.0 authorization URL.

    Args:
        state: CSRF protection state parameter

    Returns:
        Authorization URL for user to visit
    """
    settings = get_settings()

    params = {
        "client_id": settings.microsoft_oauth_client_id,
        "redirect_uri": settings.microsoft_oauth_redirect_uri,
        "response_type": "code",
        "scope": settings.microsoft_forms_scope,
        "state": state,
        "response_mode": "query",
    }

    auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urlencode(params)}"
    logger.info(f"Generated Microsoft OAuth URL with state: {state}")

    return auth_url


async def exchange_microsoft_code(code: str, user_id: str) -> Dict[str, Any]:
    """
    Exchange Microsoft authorization code for access tokens.

    Args:
        code: Authorization code from OAuth callback
        user_id: User's UUID

    Returns:
        Token information dictionary

    Raises:
        OAuthError: If exchange fails
    """
    settings = get_settings()
    db = get_db()

    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = {
        "code": code,
        "client_id": settings.microsoft_oauth_client_id,
        "client_secret": settings.microsoft_oauth_client_secret,
        "redirect_uri": settings.microsoft_oauth_redirect_uri,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        scope = token_data.get("scope", "")

        if not access_token:
            raise OAuthError("No access token in response")

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Store in database (upsert)
        db.table("oauth_tokens").upsert({
            "user_id": user_id,
            "provider": "microsoft",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_at": expires_at.isoformat(),
            "scope": scope,
        }, on_conflict="user_id,provider").execute()

        logger.info(f"Stored Microsoft OAuth tokens for user {user_id}")

        return {
            "provider": "microsoft",
            "expires_at": expires_at.isoformat(),
            "scope": scope,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error exchanging Microsoft code: {e}")
        raise OAuthError(f"Failed to exchange authorization code: {e.response.text}")
    except Exception as e:
        logger.error(f"Error exchanging Microsoft code: {e}")
        raise OAuthError(f"Failed to exchange authorization code: {str(e)}")


async def refresh_microsoft_token(user_id: str) -> Dict[str, Any]:
    """
    Refresh Microsoft OAuth access token.

    Args:
        user_id: User's UUID

    Returns:
        Updated token information

    Raises:
        TokenNotFoundError: If no token exists
        OAuthError: If refresh fails
    """
    settings = get_settings()
    db = get_db()

    # Get stored token
    response = db.table("oauth_tokens").select("*").eq("user_id", user_id).eq("provider", "microsoft").execute()

    if not response.data:
        raise TokenNotFoundError(f"No Microsoft token found for user {user_id}")

    token_record = response.data[0]
    refresh_token = token_record.get("refresh_token")

    if not refresh_token:
        raise OAuthError("No refresh token available - user needs to re-authorize")

    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = {
        "client_id": settings.microsoft_oauth_client_id,
        "client_secret": settings.microsoft_oauth_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            raise OAuthError("No access token in refresh response")

        # Calculate new expiration
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        db.table("oauth_tokens").update({
            "access_token": access_token,
            "expires_at": expires_at.isoformat(),
        }).eq("user_id", user_id).eq("provider", "microsoft").execute()

        logger.info(f"Refreshed Microsoft OAuth token for user {user_id}")

        return {
            "provider": "microsoft",
            "expires_at": expires_at.isoformat(),
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error refreshing Microsoft token: {e}")
        raise OAuthError(f"Failed to refresh token: {e.response.text}")
    except Exception as e:
        logger.error(f"Error refreshing Microsoft token: {e}")
        raise OAuthError(f"Failed to refresh token: {str(e)}")


# ============================================================================
# GENERIC TOKEN MANAGEMENT
# ============================================================================

async def get_valid_token(user_id: str, provider: str) -> str:
    """
    Get a valid access token, refreshing if necessary.

    Args:
        user_id: User's UUID
        provider: OAuth provider ('google' or 'microsoft')

    Returns:
        Valid access token

    Raises:
        TokenNotFoundError: If no token exists
        OAuthError: If token refresh fails
    """
    db = get_db()

    # Get stored token
    response = db.table("oauth_tokens").select("*").eq("user_id", user_id).eq("provider", provider).execute()

    if not response.data:
        raise TokenNotFoundError(f"No {provider} token found for user {user_id}")

    token_record = response.data[0]
    expires_at_str = token_record.get("expires_at")
    access_token = token_record.get("access_token")

    # Parse expiration time
    expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))

    # Check if token is expired or about to expire (5 minute buffer)
    if datetime.now(timezone.utc) >= expires_at - timedelta(minutes=5):
        logger.info(f"Token expired for user {user_id}, refreshing...")

        # Refresh token
        if provider == "google":
            await refresh_google_token(user_id)
        elif provider == "microsoft":
            await refresh_microsoft_token(user_id)
        else:
            raise ValueError(f"Unknown provider: {provider}")

        # Get updated token
        response = db.table("oauth_tokens").select("*").eq("user_id", user_id).eq("provider", provider).execute()
        token_record = response.data[0]
        access_token = token_record.get("access_token")

    return access_token


async def revoke_token(user_id: str, provider: str) -> None:
    """
    Revoke and delete OAuth tokens.

    Args:
        user_id: User's UUID
        provider: OAuth provider ('google' or 'microsoft')

    Raises:
        TokenNotFoundError: If no token exists
    """
    db = get_db()

    # Get token before deleting (for revocation)
    response = db.table("oauth_tokens").select("*").eq("user_id", user_id).eq("provider", provider).execute()

    if not response.data:
        raise TokenNotFoundError(f"No {provider} token found for user {user_id}")

    token_record = response.data[0]

    try:
        # Attempt to revoke token with provider
        access_token = token_record.get("access_token")

        if provider == "google":
            revoke_url = f"https://oauth2.googleapis.com/revoke?token={access_token}"
            async with httpx.AsyncClient() as client:
                await client.post(revoke_url)

        elif provider == "microsoft":
            # Microsoft doesn't have a simple revocation endpoint
            # Tokens expire automatically
            pass

        logger.info(f"Revoked {provider} token for user {user_id}")

    except Exception as e:
        logger.warning(f"Error revoking {provider} token (continuing with deletion): {e}")

    # Delete from database
    db.table("oauth_tokens").delete().eq("user_id", user_id).eq("provider", provider).execute()

    logger.info(f"Deleted {provider} token for user {user_id}")


async def has_valid_token(user_id: str, provider: str) -> bool:
    """
    Check if user has a valid OAuth token.

    Args:
        user_id: User's UUID
        provider: OAuth provider ('google' or 'microsoft')

    Returns:
        True if user has valid token, False otherwise
    """
    try:
        await get_valid_token(user_id, provider)
        return True
    except (TokenNotFoundError, OAuthError):
        return False
