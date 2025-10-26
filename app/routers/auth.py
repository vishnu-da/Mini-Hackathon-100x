"""
OAuth authentication endpoints for Google and Microsoft Forms integration.
"""
import logging
import secrets
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from typing import Dict, Any

from app.auth import get_current_user_id
from app.services import oauth_service
from app.config import get_settings
from app.schemas.auth import (
    OAuthConnectionResponse,
    OAuthCallbackResponse,
    ConnectedProvidersResponse,
    DisconnectResponse,
    LoginRequest,
    LoginResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory state storage (in production, use Redis or database)
# Maps state -> user_id for CSRF protection
oauth_states: Dict[str, str] = {}


# ============================================================================
# USER LOGIN ENDPOINT (SUPABASE)
# ============================================================================

@router.post("/login", response_model=LoginResponse, tags=["auth"])
async def login(request: LoginRequest):
    """
    Login with email and password via Supabase.

    Returns JWT token for authenticated API requests.
    """
    settings = get_settings()

    try:
        # Call Supabase auth endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.supabase_url}/auth/v1/token?grant_type=password",
                json={
                    "email": request.email,
                    "password": request.password
                },
                headers={
                    "apikey": settings.supabase_key,
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()

                # Extract token and user info
                access_token = data.get("access_token")
                user_data = data.get("user", {})

                logger.info(f"User logged in successfully: {user_data.get('email')}")

                return LoginResponse(
                    access_token=access_token,
                    user_id=user_data.get("id"),
                    email=user_data.get("email"),
                    name=user_data.get("user_metadata", {}).get("name")
                )
            else:
                error_data = response.json()
                error_message = error_data.get("error_description", "Invalid credentials")
                logger.warning(f"Login failed: {error_message}")
                raise HTTPException(status_code=401, detail=error_message)

    except httpx.TimeoutException:
        logger.error("Supabase auth timeout")
        raise HTTPException(status_code=504, detail="Authentication service timeout")
    except httpx.RequestError as e:
        logger.error(f"Supabase auth request error: {e}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable")
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


# ============================================================================
# GOOGLE OAUTH ENDPOINTS
# ============================================================================

@router.get("/google/connect", response_model=OAuthConnectionResponse, tags=["oauth"])
async def google_connect(user_id: str = Depends(get_current_user_id)):
    """
    Initiate Google OAuth flow.

    Returns authorization URL for user to visit.
    """
    # Generate CSRF state token
    state = secrets.token_urlsafe(32)

    # Store state with user_id for validation in callback
    oauth_states[state] = user_id

    # Generate OAuth URL
    auth_url = oauth_service.get_google_auth_url(state)

    logger.info(f"Initiated Google OAuth for user {user_id}")

    return OAuthConnectionResponse(
        provider="google",
        auth_url=auth_url,
        state=state,
        message="Please visit the auth_url to authorize Google Forms access"
    )

@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="CSRF state parameter"),
    error: str = Query(None, description="Error from OAuth provider")
):
    """
    Handle Google OAuth callback.

    Exchanges authorization code for access tokens and stores them.
    """
    # Handle OAuth errors
    if error:
        logger.warning(f"Google OAuth error: {error}")
        # Redirect to frontend error page
        settings = get_settings()
        return RedirectResponse(
            url=f"{settings.frontend_url}/oauth/error?provider=google&error={error}",
            status_code=302
        )

    # Validate state (CSRF protection)
    user_id = oauth_states.pop(state, None)

    if not user_id:
        logger.error(f"Invalid OAuth state: {state}")
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    try:
        # Exchange code for tokens
        token_info = await oauth_service.exchange_google_code(code, user_id)

        logger.info(f"Successfully connected Google account for user {user_id}")

        # Redirect to frontend success page
        settings = get_settings()
        return RedirectResponse(
            url=f"{settings.frontend_url}/oauth/success?provider=google",
            status_code=302
        )

    except oauth_service.OAuthError as e:
        logger.error(f"Error exchanging Google code: {e}")
        settings = get_settings()
        return RedirectResponse(
            url=f"{settings.frontend_url}/oauth/error?provider=google&error={str(e)}",
            status_code=302
        )


# ============================================================================
# MICROSOFT OAUTH ENDPOINTS
# ============================================================================

@router.get("/microsoft/connect", response_model=OAuthConnectionResponse)
async def microsoft_connect(user_id: str = Depends(get_current_user_id)):
    """
    Initiate Microsoft OAuth flow.

    Returns authorization URL for user to visit.
    """
    # Generate CSRF state token
    state = secrets.token_urlsafe(32)

    # Store state with user_id
    oauth_states[state] = user_id

    # Generate OAuth URL
    auth_url = oauth_service.get_microsoft_auth_url(state)

    logger.info(f"Initiated Microsoft OAuth for user {user_id}")

    return OAuthConnectionResponse(
        provider="microsoft",
        auth_url=auth_url,
        state=state,
        message="Please visit the auth_url to authorize Microsoft Forms access"
    )


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str = Query(..., description="Authorization code from Microsoft"),
    state: str = Query(..., description="CSRF state parameter"),
    error: str = Query(None, description="Error from OAuth provider"),
    error_description: str = Query(None, description="Error description")
):
    """
    Handle Microsoft OAuth callback.

    Exchanges authorization code for access tokens and stores them.
    """
    # Handle OAuth errors
    if error:
        error_msg = error_description or error
        logger.warning(f"Microsoft OAuth error: {error_msg}")
        return RedirectResponse(
            url=f"/oauth/error?provider=microsoft&error={error_msg}",
            status_code=302
        )

    # Validate state (CSRF protection)
    user_id = oauth_states.pop(state, None)

    if not user_id:
        logger.error(f"Invalid OAuth state: {state}")
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    try:
        # Exchange code for tokens
        token_info = await oauth_service.exchange_microsoft_code(code, user_id)

        logger.info(f"Successfully connected Microsoft account for user {user_id}")

        # Redirect to frontend success page
        return RedirectResponse(
            url="/oauth/success?provider=microsoft",
            status_code=302
        )

    except oauth_service.OAuthError as e:
        logger.error(f"Error exchanging Microsoft code: {e}")
        return RedirectResponse(
            url=f"/oauth/error?provider=microsoft&error={str(e)}",
            status_code=302
        )


# ============================================================================
# GENERIC OAUTH ENDPOINTS
# ============================================================================

@router.get("/connections", response_model=ConnectedProvidersResponse)
async def get_connections(user_id: str = Depends(get_current_user_id)):
    """
    Get list of connected OAuth providers for current user.

    Returns which providers (Google, Microsoft) are connected.
    """
    # Check if user has tokens for each provider
    google_connected = await oauth_service.has_valid_token(user_id, "google")
    microsoft_connected = await oauth_service.has_valid_token(user_id, "microsoft")

    return ConnectedProvidersResponse(
        google=google_connected,
        microsoft=microsoft_connected
    )


@router.get("/oauth/success")
async def oauth_success(provider: str = Query("google")):
    """OAuth success page."""
    return {"success": True, "provider": provider, "message": "OAuth connection successful"}


@router.get("/oauth/error")
async def oauth_error(provider: str = Query("google"), error: str = Query("Unknown error")):
    """OAuth error page."""
    return {"success": False, "provider": provider, "error": error}


@router.delete("/{provider}/disconnect", response_model=DisconnectResponse)
async def disconnect_provider(
    provider: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Disconnect and revoke OAuth tokens for a provider.

    Args:
        provider: "google" or "microsoft"
    """
    if provider not in ["google", "microsoft"]:
        raise HTTPException(status_code=400, detail="Invalid provider. Must be 'google' or 'microsoft'")

    try:
        await oauth_service.revoke_token(user_id, provider)

        logger.info(f"Disconnected {provider} for user {user_id}")

        return DisconnectResponse(
            success=True,
            provider=provider,
            message=f"Successfully disconnected {provider.title()} account"
        )

    except oauth_service.TokenNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No {provider} connection found for this account"
        )

    except oauth_service.OAuthError as e:
        logger.error(f"Error disconnecting {provider}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect {provider}: {str(e)}"
        )