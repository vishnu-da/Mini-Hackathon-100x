"""
Unified form fetcher service for Google Forms and Microsoft Forms.
Handles OAuth token management and routes to appropriate API client.
"""
import logging
from typing import Dict, Any, Optional
from app.services import oauth_service, google_forms_client, microsoft_forms_client

logger = logging.getLogger(__name__)


class FormFetchError(Exception):
    """Base exception for form fetching errors."""
    pass


def detect_provider(url: str) -> str:
    """
    Detect form provider from URL.

    Args:
        url: Form URL

    Returns:
        Provider name: "google", "microsoft", or "unknown"
    """
    url_lower = url.lower()

    if "docs.google.com/forms" in url_lower:
        return "google"
    elif "forms.office.com" in url_lower or "forms.microsoft.com" in url_lower:
        return "microsoft"
    else:
        return "unknown"


async def validate_form_access(user_id: str, form_url: str) -> Dict[str, Any]:
    """
    Check if user has OAuth token for the form provider.

    Args:
        user_id: User's UUID
        form_url: Form URL

    Returns:
        Dictionary with validation result:
        {
            "has_access": bool,
            "provider": str,
            "needs_auth": bool,
            "auth_url": str (if needs_auth)
        }
    """
    provider = detect_provider(form_url)

    if provider == "unknown":
        return {
            "has_access": False,
            "provider": "unknown",
            "needs_auth": False,
            "error": "Unsupported form URL - only Google Forms and Microsoft Forms are supported"
        }

    # Check if user has valid token
    has_token = await oauth_service.has_valid_token(user_id, provider)

    if has_token:
        return {
            "has_access": True,
            "provider": provider,
            "needs_auth": False,
        }
    else:
        # Generate auth URL
        import secrets
        state = secrets.token_urlsafe(32)

        if provider == "google":
            auth_url = oauth_service.get_google_auth_url(state)
        else:  # microsoft
            auth_url = oauth_service.get_microsoft_auth_url(state)

        return {
            "has_access": False,
            "provider": provider,
            "needs_auth": True,
            "auth_url": auth_url,
            "state": state,
        }


async def fetch_form(user_id: str, form_url: str) -> Dict[str, Any]:
    """
    Fetch form structure from URL using OAuth authentication.

    This is the main entry point for form fetching.

    Args:
        user_id: User's UUID
        form_url: Google Forms or Microsoft Forms URL

    Returns:
        Standardized questionnaire JSON

    Raises:
        FormFetchError: If fetching fails
    """
    # Detect provider
    provider = detect_provider(form_url)

    if provider == "unknown":
        logger.error(f"Unknown form provider for URL: {form_url}")
        return {
            "error": True,
            "error_type": "invalid_url",
            "message": "Unsupported form URL. Please provide a Google Forms or Microsoft Forms link.",
            "action_required": None,
        }

    logger.info(f"Fetching {provider} form for user {user_id}: {form_url}")

    # Check if user has OAuth token
    try:
        access_token = await oauth_service.get_valid_token(user_id, provider)
    except oauth_service.TokenNotFoundError:
        logger.warning(f"User {user_id} not authorized for {provider}")

        # Generate auth URL
        import secrets
        state = secrets.token_urlsafe(32)

        if provider == "google":
            auth_url = oauth_service.get_google_auth_url(state)
            action = "connect_google"
        else:
            auth_url = oauth_service.get_microsoft_auth_url(state)
            action = "connect_microsoft"

        return {
            "error": True,
            "error_type": "not_authorized",
            "message": f"Please connect your {provider.title()} account to import forms.",
            "action_required": action,
            "auth_url": auth_url,
            "state": state,
        }
    except oauth_service.OAuthError as e:
        logger.error(f"OAuth error for user {user_id}: {e}")
        return {
            "error": True,
            "error_type": "oauth_error",
            "message": f"Authentication error: {str(e)}",
            "action_required": f"connect_{provider}",
        }

    # Extract form ID and fetch form
    try:
        if provider == "google":
            form_id = google_forms_client.extract_form_id_from_url(form_url)
            questionnaire = await google_forms_client.fetch_form(form_id, access_token)

        else:  # microsoft
            form_id = microsoft_forms_client.extract_form_id_from_url(form_url)
            questionnaire = await microsoft_forms_client.fetch_form(form_id, access_token)

        logger.info(f"Successfully fetched {provider} form: {form_id}")
        return questionnaire

    except (google_forms_client.GoogleFormsError, microsoft_forms_client.MicrosoftFormsError) as e:
        error_msg = str(e)
        logger.error(f"Form fetch error: {error_msg}")

        # Determine error type
        if "not found" in error_msg.lower() or "404" in error_msg:
            error_type = "form_not_found"
        elif "permission denied" in error_msg.lower() or "403" in error_msg:
            error_type = "permission_denied"
        elif "rate limit" in error_msg.lower() or "429" in error_msg:
            error_type = "rate_limit"
        else:
            error_type = "api_error"

        return {
            "error": True,
            "error_type": error_type,
            "message": error_msg,
            "action_required": None,
        }

    except Exception as e:
        logger.exception(f"Unexpected error fetching form: {e}")
        return {
            "error": True,
            "error_type": "unknown_error",
            "message": f"An unexpected error occurred: {str(e)}",
            "action_required": None,
        }


def validate_form_url(url: str) -> bool:
    """
    Validate if URL is a supported form provider.

    Args:
        url: Form URL

    Returns:
        True if URL is valid Google Forms or Microsoft Forms URL
    """
    provider = detect_provider(url)
    return provider in ["google", "microsoft"]
