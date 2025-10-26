"""
Pydantic schemas for survey management.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import re


class CreateSurveyRequest(BaseModel):
    """Request schema for creating a new survey."""

    form_url: str = Field(..., description="Google Form URL")
    terms_and_conditions: Optional[str] = Field(None, description="Terms and conditions text (optional)")
    voice_agent_tone: str = Field(default="friendly", description="Voice agent tone")
    voice_agent_instructions: Optional[str] = Field(None, description="Custom instructions for voice agent")
    max_call_duration: int = Field(default=5, description="Maximum call duration in minutes")
    max_retry_attempts: int = Field(default=2, description="Maximum retry attempts for failed calls")

    @field_validator("form_url")
    @classmethod
    def validate_form_url(cls, v: str) -> str:
        """Validate that form_url is a valid Google Forms URL."""
        pattern = r'docs\.google\.com/forms/d/[a-zA-Z0-9-_]+'
        if not re.search(pattern, v):
            raise ValueError("Invalid Google Forms URL format")
        return v

    @field_validator("voice_agent_tone")
    @classmethod
    def validate_tone(cls, v: str) -> str:
        """Validate voice agent tone."""
        allowed_tones = ["friendly", "professional", "casual"]
        if v not in allowed_tones:
            raise ValueError(f"voice_agent_tone must be one of: {', '.join(allowed_tones)}")
        return v

    @field_validator("max_call_duration")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        """Validate max call duration."""
        if not 1 <= v <= 30:
            raise ValueError("max_call_duration must be between 1 and 30 minutes")
        return v

    @field_validator("max_retry_attempts")
    @classmethod
    def validate_retry(cls, v: int) -> int:
        """Validate retry attempts."""
        if not 0 <= v <= 5:
            raise ValueError("max_retry_attempts must be between 0 and 5")
        return v


class UpdateSurveyRequest(BaseModel):
    """Request schema for updating a survey."""

    form_url: Optional[str] = Field(None, description="Google Form URL")
    terms_and_conditions: Optional[str] = Field(None, description="Terms and conditions text")
    voice_agent_tone: Optional[str] = Field(None, description="Voice agent tone")
    voice_agent_instructions: Optional[str] = Field(None, description="Custom instructions for voice agent")
    max_call_duration: Optional[int] = Field(None, description="Maximum call duration in minutes")
    max_retry_attempts: Optional[int] = Field(None, description="Maximum retry attempts")

    @field_validator("form_url")
    @classmethod
    def validate_form_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate form URL if provided."""
        if v is not None:
            pattern = r'docs\.google\.com/forms/d/[a-zA-Z0-9-_]+'
            if not re.search(pattern, v):
                raise ValueError("Invalid Google Forms URL format")
        return v

    @field_validator("voice_agent_tone")
    @classmethod
    def validate_tone(cls, v: Optional[str]) -> Optional[str]:
        """Validate voice agent tone if provided."""
        if v is not None:
            allowed_tones = ["friendly", "professional", "casual"]
            if v not in allowed_tones:
                raise ValueError(f"voice_agent_tone must be one of: {', '.join(allowed_tones)}")
        return v

    @field_validator("max_call_duration")
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        """Validate max call duration if provided."""
        if v is not None and not 1 <= v <= 30:
            raise ValueError("max_call_duration must be between 1 and 30 minutes")
        return v

    @field_validator("max_retry_attempts")
    @classmethod
    def validate_retry(cls, v: Optional[int]) -> Optional[int]:
        """Validate retry attempts if provided."""
        if v is not None and not 0 <= v <= 5:
            raise ValueError("max_retry_attempts must be between 0 and 5")
        return v


class VoiceConfigUpdate(BaseModel):
    """Request schema for updating voice configuration only."""

    voice_agent_tone: str = Field(..., description="Voice agent tone")
    voice_agent_instructions: Optional[str] = Field(None, description="Custom instructions")
    max_call_duration: int = Field(..., description="Maximum call duration in minutes")
    max_retry_attempts: int = Field(..., description="Maximum retry attempts")

    @field_validator("voice_agent_tone")
    @classmethod
    def validate_tone(cls, v: str) -> str:
        """Validate voice agent tone."""
        allowed_tones = ["friendly", "professional", "casual"]
        if v not in allowed_tones:
            raise ValueError(f"voice_agent_tone must be one of: {', '.join(allowed_tones)}")
        return v

    @field_validator("max_call_duration")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        """Validate max call duration."""
        if not 1 <= v <= 30:
            raise ValueError("max_call_duration must be between 1 and 30 minutes")
        return v

    @field_validator("max_retry_attempts")
    @classmethod
    def validate_retry(cls, v: int) -> int:
        """Validate retry attempts."""
        if not 0 <= v <= 5:
            raise ValueError("max_retry_attempts must be between 0 and 5")
        return v


class SurveyResponse(BaseModel):
    """Response schema for survey data."""

    survey_id: UUID
    user_id: UUID
    form_link: str
    json_questionnaire: dict
    status: str
    voice_agent_tone: str
    voice_agent_instructions: Optional[str]
    callback_link: str
    max_call_duration: int
    max_retry_attempts: int
    created_at: datetime
    terms_and_conditions: Optional[str]

    class Config:
        from_attributes = True


class SurveyListResponse(BaseModel):
    """Response schema for list of surveys."""

    surveys: List[SurveyResponse]
    total: int
