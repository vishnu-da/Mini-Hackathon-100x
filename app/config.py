"""
Configuration management for the AI Voice Survey platform.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv
import os

# Explicitly load .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    supabase_service_key: str

    # Twilio Configuration
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str

    # OpenAI Configuration
    openai_api_key: str
    openai_realtime_model: str = "gpt-4o-realtime-preview-2024-10-01"  # Deprecated - using LiveKit now
    llm_choice: str = "gpt-4o-mini"  # LLM model for LiveKit agent

    # LiveKit Configuration
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    livekit_sip_domain: str  # SIP domain from LiveKit (e.g., 5fm2c0uy4wd.sip.livekit.cloud)
    livekit_outbound_trunk_id: str = "ST_d3TZzQoeU3Kv"  # Outbound SIP trunk ID for dialing via Twilio

    # Deepgram Configuration (STT for LiveKit)
    deepgram_api_key: str

    # Rime Configuration (TTS for LiveKit) - DEPRECATED, using Cartesia now
    rime_api_key: str

    # Cartesia Configuration (TTS for LiveKit)
    cartesia_api_key: str

    # Groq Configuration (Fast LLM for LiveKit)
    groq_api_key: str
    groq_llm: str = "llama-3.3-70b-versatile"  # Groq model for ultra-fast inference

    # Application Configuration
    app_env: str = "development"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    max_call_duration_minutes: int = 5
    default_retry_attempts: int = 2
    callback_base_url: str = "http://localhost:8000"

    # Google Sheets Configuration (Optional)
    google_sheets_credentials: Optional[str] = None

    # Google OAuth Configuration
    google_oauth_client_id: str
    google_oauth_client_secret: str
    google_oauth_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Microsoft OAuth Configuration
    microsoft_oauth_client_id: str
    microsoft_oauth_client_secret: str
    microsoft_oauth_redirect_uri: str = "http://localhost:8000/auth/microsoft/callback"

    # OAuth Scopes
    google_forms_scope: str = "https://www.googleapis.com/auth/forms.body.readonly https://www.googleapis.com/auth/forms.responses.readonly"
    microsoft_forms_scope: str = "Forms.Read.All User.Read"

    # Frontend URL for OAuth redirects
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()
