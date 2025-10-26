"""
Microsoft Forms API client for fetching form structures.
Uses Microsoft Graph API with OAuth authentication.
"""
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx

logger = logging.getLogger(__name__)


class MicrosoftFormsError(Exception):
    """Base exception for Microsoft Forms API errors."""
    pass


def extract_form_id_from_url(url: str) -> str:
    """
    Extract form ID from Microsoft Forms URL.

    Supports URLs like:
    - https://forms.office.com/Pages/ResponsePage.aspx?id={formId}
    - https://forms.microsoft.com/Pages/ResponsePage.aspx?id={formId}
    - https://forms.office.com/r/{shortId}

    Args:
        url: Microsoft Forms URL

    Returns:
        Form ID

    Raises:
        MicrosoftFormsError: If URL is invalid
    """
    # Pattern 1: ?id={formId} parameter
    pattern1 = r'[?&]id=([a-zA-Z0-9_-]+)'

    # Pattern 2: /r/{shortId} short URL
    pattern2 = r'forms\.(office|microsoft)\.com/r/([a-zA-Z0-9_-]+)'

    match = re.search(pattern2, url) or re.search(pattern1, url)

    if not match:
        raise MicrosoftFormsError(f"Invalid Microsoft Forms URL: {url}")

    form_id = match.group(2) if match.lastindex == 2 else match.group(1)
    logger.info(f"Extracted Microsoft form ID: {form_id}")

    return form_id


async def fetch_form(form_id: str, access_token: str) -> Dict[str, Any]:
    """
    Fetch form structure from Microsoft Graph API.

    Args:
        form_id: Microsoft Form ID
        access_token: Valid OAuth access token

    Returns:
        Standardized questionnaire JSON

    Raises:
        MicrosoftFormsError: If API call fails
    """
    # Microsoft Forms API endpoint
    api_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{form_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            # First, get the form metadata
            response = await client.get(api_url, headers=headers, timeout=30.0)
            response.raise_for_status()
            form_metadata = response.json()

            # Get form content (questions)
            # Note: Microsoft Graph API structure may vary - this is a simplified approach
            # For production, you may need to use Microsoft Forms specific endpoints
            content_url = f"{api_url}/content"
            content_response = await client.get(content_url, headers=headers, timeout=30.0)

            if content_response.status_code == 200:
                form_content = content_response.json()
            else:
                # Fallback: use basic metadata
                form_content = form_metadata

        logger.info(f"Fetched Microsoft Form: {form_id}")

        # Parse to our standard format
        questionnaire = parse_microsoft_form_response(form_content, form_id)

        return questionnaire

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise MicrosoftFormsError(f"Form not found: {form_id}")
        elif e.response.status_code == 403:
            raise MicrosoftFormsError("Permission denied - ensure OAuth token has Forms.Read.All permission")
        elif e.response.status_code == 429:
            raise MicrosoftFormsError("Rate limit exceeded - please try again later")
        else:
            logger.error(f"HTTP error fetching Microsoft form: {e.response.text}")
            raise MicrosoftFormsError(f"API error: {e.response.status_code}")

    except httpx.TimeoutException:
        raise MicrosoftFormsError("Request timeout - Microsoft Graph API not responding")
    except Exception as e:
        logger.error(f"Error fetching Microsoft Form: {e}")
        raise MicrosoftFormsError(f"Failed to fetch form: {str(e)}")


def parse_microsoft_form_response(api_response: Dict[str, Any], form_id: str) -> Dict[str, Any]:
    """
    Convert Microsoft Graph API response to standardized JSON format.

    Args:
        api_response: Raw response from Microsoft Graph API
        form_id: Form ID

    Returns:
        Standardized questionnaire dictionary
    """
    # Microsoft Forms API structure
    title = api_response.get("name", "Untitled Form")

    # Extract questions - structure may vary based on API version
    questions_data = api_response.get("questions", [])
    if not questions_data:
        # Try alternative structure
        questions_data = api_response.get("items", [])
    if not questions_data:
        # Try form body structure
        form_body = api_response.get("body", {})
        questions_data = form_body.get("questions", [])

    questions = []

    for idx, item in enumerate(questions_data):
        question_text = item.get("title") or item.get("questionText") or item.get("text", "")
        required = item.get("isRequired", False) or item.get("required", False)

        # Determine question type and extract options
        question_type, options, scale_info = _parse_question_type(item)

        question_dict = {
            "question_id": f"q{idx + 1}",
            "question_text": question_text,
            "question_type": question_type,
            "options": options,
            "required": required,
            "scale_min": scale_info.get("min") if scale_info else None,
            "scale_max": scale_info.get("max") if scale_info else None,
            "scale_min_label": scale_info.get("min_label") if scale_info else None,
            "scale_max_label": scale_info.get("max_label") if scale_info else None,
        }

        questions.append(question_dict)

    return {
        "title": title,
        "form_type": "microsoft",
        "form_id": form_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "questions": questions,
    }


def _parse_question_type(question: Dict[str, Any]) -> tuple[str, Optional[List[str]], Optional[Dict[str, Any]]]:
    """
    Parse Microsoft Forms question type and extract options.

    Returns:
        Tuple of (question_type, options, scale_info)
    """
    # Get question type
    q_type = question.get("type", "").lower()
    question_type_field = question.get("questionType", "").lower()

    # Combine both possible type fields
    type_str = q_type or question_type_field

    # Choice questions (single or multiple)
    if type_str in ["choice", "choices", "multiplechoice"]:
        allow_multiple = question.get("allowMultipleSelections", False) or question.get("multiSelect", False)

        if allow_multiple:
            question_type = "checkboxes"
        else:
            question_type = "multiple_choice"

        # Extract choices
        choices = question.get("choices", []) or question.get("options", [])
        options = []

        for choice in choices:
            if isinstance(choice, str):
                options.append(choice)
            elif isinstance(choice, dict):
                option_text = choice.get("value") or choice.get("text") or choice.get("displayName", "")
                if option_text:
                    options.append(option_text)

        return question_type, options, None

    # Text questions
    elif type_str in ["text", "textarea", "shortanswer", "longanswer"]:
        is_long = question.get("isLongText", False) or "long" in type_str or "paragraph" in type_str

        question_type = "paragraph" if is_long else "short_answer"

        return question_type, None, None

    # Rating/Scale questions
    elif type_str in ["rating", "scale", "likert"]:
        min_value = question.get("minValue", 1) or question.get("min", 1)
        max_value = question.get("maxValue", 5) or question.get("max", 5)
        min_label = question.get("minLabel", "") or question.get("startLabel", "")
        max_label = question.get("maxLabel", "") or question.get("endLabel", "")

        scale_info = {
            "min": min_value,
            "max": max_value,
            "min_label": min_label,
            "max_label": max_label,
        }

        return "linear_scale", None, scale_info

    # Dropdown
    elif type_str in ["dropdown", "select"]:
        choices = question.get("choices", []) or question.get("options", [])
        options = []

        for choice in choices:
            if isinstance(choice, str):
                options.append(choice)
            elif isinstance(choice, dict):
                option_text = choice.get("value") or choice.get("text") or choice.get("displayName", "")
                if option_text:
                    options.append(option_text)

        return "dropdown", options, None

    else:
        # Unknown type - default to short answer
        logger.warning(f"Unknown Microsoft Forms question type: {type_str}")
        return "short_answer", None, None
