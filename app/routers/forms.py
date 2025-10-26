"""
Form fetching endpoints for Google and Microsoft Forms.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any

from app.auth import get_current_user_id
from app.services.form_fetcher import fetch_form

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/fetch")
async def fetch_form_endpoint(
    form_url: str = Query(..., description="Google or Microsoft Forms URL"),
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Fetch form structure from Google Forms or Microsoft Forms.

    Automatically detects form type and fetches using appropriate API.
    Requires user to have connected OAuth for the respective provider.
    """
    try:
        result = await fetch_form(user_id, form_url)

        if result.get("error"):
            raise HTTPException(
                status_code=400,
                detail={
                    "error_type": result.get("error_type"),
                    "message": result.get("message"),
                    "action_required": result.get("action_required")
                }
            )

        return result

    except Exception as e:
        logger.error(f"Error fetching form: {e}")
        raise HTTPException(status_code=500, detail=str(e))
