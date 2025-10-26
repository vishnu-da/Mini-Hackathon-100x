"""Data models for frontend."""
from typing import List, Optional
from pydantic import BaseModel


class Question(BaseModel):
    """Survey question model."""
    question_id: str
    question_text: str
    question_type: str
    options: Optional[List[str]] = None
    required: bool = False


class Questionnaire(BaseModel):
    """Survey questionnaire model."""
    title: str
    description: Optional[str] = ""
    questions: List[Question] = []


class Survey(BaseModel):
    """Survey model."""
    survey_id: str
    user_id: str
    form_url: Optional[str] = ""
    status: str = "draft"
    json_questionnaire: Optional[Questionnaire] = None
    voice_agent_tone: str = "friendly"
    voice_agent_voice: str = "astra"
    voice_agent_instructions: Optional[str] = ""
    max_call_duration: int = 5
    max_retry_attempts: int = 2
    callback_link: Optional[str] = ""
    terms_and_conditions: Optional[str] = ""
    created_at: str = ""
    updated_at: str = ""


class Contact(BaseModel):
    """Contact model."""
    contact_id: str
    survey_id: str
    participant_name: Optional[str] = ""
    phone_number: str
    email: Optional[str] = ""
    consent: bool = False
    call_status: str = "pending"
    created_at: str = ""


class CampaignStatus(BaseModel):
    """Campaign status model."""
    campaign_id: str
    status: str
    phone_number: Optional[str] = ""
    total_contacts: int = 0
    completed_calls: int = 0
    in_progress_calls: int = 0
    failed_calls: int = 0
    pending_calls: int = 0
    completion_percentage: float = 0.0


class PhoneInfo(BaseModel):
    """Phone number info model."""
    phone_number: Optional[str] = None
    status: str = "not_provisioned"
    provisioned_at: Optional[str] = None
    trunk_id: Optional[str] = None
