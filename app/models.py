"""
Pydantic models for API requests and responses.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SurveyStatus(str, Enum):
    """Survey status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class CallStatus(str, Enum):
    """Call status enumeration."""
    QUEUED = "queued"
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no_answer"


# Survey Models
class SurveyCreate(BaseModel):
    """Model for creating a new survey."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    questions: List[Dict[str, Any]] = Field(..., min_items=1)
    status: SurveyStatus = SurveyStatus.DRAFT


class SurveyUpdate(BaseModel):
    """Model for updating an existing survey."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    questions: Optional[List[Dict[str, Any]]] = None
    status: Optional[SurveyStatus] = None


class SurveyResponse(BaseModel):
    """Model for survey response."""
    id: str
    name: str
    description: Optional[str]
    questions: List[Dict[str, Any]]
    status: SurveyStatus
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Call Models
class CallCreate(BaseModel):
    """Model for initiating a new call."""
    survey_id: str
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    recipient_name: Optional[str] = None


class CallUpdate(BaseModel):
    """Model for updating call status."""
    status: CallStatus
    recording_url: Optional[str] = None
    duration: Optional[int] = None
    notes: Optional[str] = None


class CallResponse(BaseModel):
    """Model for call response."""
    id: str
    survey_id: str
    phone_number: str
    recipient_name: Optional[str]
    status: CallStatus
    recording_url: Optional[str]
    duration: Optional[int]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Response Models
class SurveyResponseCreate(BaseModel):
    """Model for creating a survey response."""
    call_id: str
    survey_id: str
    answers: Dict[str, Any]


class SurveyResponseData(BaseModel):
    """Model for survey response data."""
    id: str
    call_id: str
    survey_id: str
    answers: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# Generic Response Models
class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"


# Webhook Models
class TwilioWebhook(BaseModel):
    """Model for Twilio webhook data."""
    CallSid: str
    AccountSid: str
    From: str
    To: str
    CallStatus: str
    Direction: Optional[str] = None
    RecordingUrl: Optional[str] = None
    RecordingDuration: Optional[str] = None


class OpenAIConversation(BaseModel):
    """Model for OpenAI conversation request."""
    message: str
    context: Optional[Dict[str, Any]] = None
    max_tokens: int = Field(default=150, ge=1, le=4000)
