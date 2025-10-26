"""
Google Forms API client for fetching form structures.
Uses official Google Forms API with OAuth authentication.
"""
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx

logger = logging.getLogger(__name__)


class GoogleFormsError(Exception):
    """Base exception for Google Forms API errors."""
    pass


def extract_form_id_from_url(url: str) -> str:
    """
    Extract form ID from Google Forms URL.

    Supports URLs like:
    - https://docs.google.com/forms/d/{formId}/edit
    - https://docs.google.com/forms/d/e/{formId}/viewform
    - https://docs.google.com/forms/d/{formId}/viewform

    Args:
        url: Google Forms URL

    Returns:
        Form ID

    Raises:
        GoogleFormsError: If URL is invalid
    """
    # Pattern 1: /d/{formId}/edit or /d/{formId}/viewform
    pattern1 = r'docs\.google\.com/forms/d/([a-zA-Z0-9-_]+)'

    # Pattern 2: /d/e/{formId}/viewform
    pattern2 = r'docs\.google\.com/forms/d/e/([a-zA-Z0-9-_]+)'

    match = re.search(pattern2, url) or re.search(pattern1, url)

    if not match:
        raise GoogleFormsError(f"Invalid Google Forms URL: {url}")

    form_id = match.group(1)
    logger.info(f"Extracted form ID: {form_id}")

    return form_id


async def fetch_form(form_id: str, access_token: str) -> Dict[str, Any]:
    """
    Fetch form structure from Google Forms API.

    Args:
        form_id: Google Form ID
        access_token: Valid OAuth access token

    Returns:
        Standardized questionnaire JSON

    Raises:
        GoogleFormsError: If API call fails
    """
    api_url = f"https://forms.googleapis.com/v1/forms/{form_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, timeout=30.0)
            response.raise_for_status()
            api_response = response.json()

        logger.info(f"Fetched Google Form: {form_id}")

        # Parse to our standard format
        questionnaire = parse_google_form_response(api_response, form_id)

        return questionnaire

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise GoogleFormsError(f"Form not found: {form_id}")
        elif e.response.status_code == 403:
            raise GoogleFormsError("Permission denied - ensure OAuth token has Forms API access")
        elif e.response.status_code == 429:
            raise GoogleFormsError("Rate limit exceeded - please try again later")
        else:
            logger.error(f"HTTP error fetching form: {e.response.text}")
            raise GoogleFormsError(f"API error: {e.response.status_code}")

    except httpx.TimeoutException:
        raise GoogleFormsError("Request timeout - Google Forms API not responding")
    except Exception as e:
        logger.error(f"Error fetching Google Form: {e}")
        raise GoogleFormsError(f"Failed to fetch form: {str(e)}")


def parse_google_form_response(api_response: Dict[str, Any], form_id: str) -> Dict[str, Any]:
    """
    Convert Google Forms API response to standardized JSON format.

    Args:
        api_response: Raw response from Google Forms API
        form_id: Form ID

    Returns:
        Standardized questionnaire dictionary
    """
    title = api_response.get("info", {}).get("title", "Untitled Form")
    items = api_response.get("items", [])

    questions = []

    for idx, item in enumerate(items):
        question_item = item.get("questionItem")
        if not question_item:
            continue  # Skip non-question items (text, images, etc.)

        question = question_item.get("question", {})
        question_text = item.get("title", "")
        required = question.get("required", False)

        # Determine question type and extract options
        question_type, options, scale_info = _parse_question_type(question)

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
        "form_type": "google",
        "form_id": form_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "questions": questions,
    }


def _parse_question_type(question: Dict[str, Any]) -> tuple[str, Optional[List[str]], Optional[Dict[str, Any]]]:
    """
    Parse Google Forms question type and extract options.

    Returns:
        Tuple of (question_type, options, scale_info)
    """
    # Check for each question type
    if "choiceQuestion" in question:
        choice_q = question["choiceQuestion"]
        question_type_enum = choice_q.get("type", "RADIO")

        if question_type_enum == "RADIO":
            question_type = "multiple_choice"
        elif question_type_enum == "CHECKBOX":
            question_type = "checkboxes"
        elif question_type_enum == "DROP_DOWN":
            question_type = "dropdown"
        else:
            question_type = "multiple_choice"

        # Extract options
        options = [opt.get("value", "") for opt in choice_q.get("options", [])]

        return question_type, options, None

    elif "textQuestion" in question:
        text_q = question["textQuestion"]
        paragraph = text_q.get("paragraph", False)

        question_type = "paragraph" if paragraph else "short_answer"

        return question_type, None, None

    elif "scaleQuestion" in question:
        scale_q = question["scaleQuestion"]

        low = scale_q.get("low", 1)
        high = scale_q.get("high", 5)
        low_label = scale_q.get("lowLabel", "")
        high_label = scale_q.get("highLabel", "")

        scale_info = {
            "min": low,
            "max": high,
            "min_label": low_label,
            "high_label": high_label,
        }

        return "linear_scale", None, scale_info

    else:
        # Unknown type - default to short answer
        logger.warning(f"Unknown question type in Google Form: {question.keys()}")
        return "short_answer", None, None
