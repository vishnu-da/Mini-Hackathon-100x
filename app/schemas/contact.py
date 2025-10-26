"""
Pydantic schemas for contact management.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ContactResponse(BaseModel):
    """Response schema for contact data."""

    contact_id: UUID
    survey_id: UUID
    phone_number: str
    participant_name: Optional[str]
    participant_email: Optional[str]
    participant_metadata: Optional[dict]
    callback: str
    upload_timestamp: datetime

    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    """Response schema for list of contacts."""

    contacts: List[ContactResponse]
    total: int


class UploadContactsResponse(BaseModel):
    """Response schema for contact upload."""

    contacts_added: int
    upload_timestamp: datetime
    filename: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
