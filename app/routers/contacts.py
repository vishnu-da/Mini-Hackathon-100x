"""
Contact management API endpoints.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Body, HTTPException
from typing import Optional

from app.auth import get_current_user_id
from app.schemas.contact import ContactListResponse, UploadContactsResponse
from app.services import contact_service

router = APIRouter()


@router.post("/{survey_id}/contacts/upload", response_model=UploadContactsResponse, status_code=201)
async def upload_contacts(
    survey_id: str,
    file: UploadFile = File(..., description="CSV file with contact data"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Upload contacts from CSV file for a survey.

    CSV Format:
    ```
    phone_number,participant_name,participant_email
    +1234567890,John Doe,john@example.com
    ```
    """
    result = await contact_service.upload_contacts(survey_id, user_id, file)
    return result


@router.get("/{survey_id}/contacts", response_model=ContactListResponse)
async def get_contacts(
    survey_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get all contacts for a survey.
    """
    result = await contact_service.get_contacts(survey_id, user_id)
    return result


@router.post("/callback/{survey_id}")
async def create_callback_contact(
    survey_id: str,
    phone_number: str = Body(..., embed=True),
    participant_name: Optional[str] = Body(None, embed=True)
):
    """
    Create a callback contact for inbound "call me" requests.
    No authentication required - public endpoint.
    """
    result = await contact_service.create_callback_contact(survey_id, phone_number, participant_name)
    return result
