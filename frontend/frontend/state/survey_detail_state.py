"""Survey detail state management."""
import reflex as rx
from typing import Optional, List
import csv
import io
from frontend.services.api_client import APIClient
from frontend.models import Survey


class UploadFile:
    """Helper to store upload file data."""
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.content = content


class SurveyDetailState(rx.State):
    """Handle survey detail page state and operations."""

    # Note: survey_id is automatically created by Reflex from route [survey_id]
    # Don't declare it here - it's injected automatically
    survey: Optional[Survey] = None
    loading: bool = False
    error_message: str = ""
    success_message: str = ""
    current_survey_id: str = ""  # Store the survey_id manually

    # CSV upload
    csv_uploaded: bool = False
    csv_filename: str = ""
    contacts_count: int = 0
    contacts_data: List[dict] = []

    # Voice configuration
    voice_tone: str = "friendly"
    voice_model: str = "astra"
    custom_instructions: str = ""
    max_duration: int = 5

    async def load_survey(self):
        """Load survey details."""
        self.loading = True
        self.error_message = ""

        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                self.loading = False
                return

            # Get survey_id from URL path
            url_path = self.router.page.raw_path
            survey_id = url_path.split("/survey/")[-1] if "/survey/" in url_path else ""

            if not survey_id:
                self.error_message = "No survey ID in URL"
                self.loading = False
                return

            self.current_survey_id = survey_id  # Store it
            client = APIClient(token=auth_state.token)
            survey_data = await client.get_survey(survey_id)

            self.survey = Survey(**survey_data)

            # Load existing configuration
            self.voice_tone = self.survey.voice_agent_tone or "friendly"
            self.custom_instructions = self.survey.voice_agent_instructions or ""
            self.max_duration = self.survey.max_call_duration or 5

        except Exception as e:
            self.error_message = f"Failed to load survey: {str(e)}"
        finally:
            self.loading = False

    def set_voice_tone(self, value: str):
        """Set voice tone."""
        self.voice_tone = value

    def set_voice_model(self, value: str):
        """Set voice model."""
        self.voice_model = value

    def set_custom_instructions(self, value: str):
        """Set custom instructions."""
        self.custom_instructions = value

    def set_max_duration(self, value: int):
        """Set max call duration."""
        self.max_duration = value

    async def handle_upload(self, files: List[rx.UploadFile]):
        """Handle CSV file upload - sends to backend."""
        if not files:
            return

        file = files[0]
        self.csv_filename = file.filename
        self.error_message = ""
        self.success_message = ""

        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                return

            if not self.current_survey_id:
                self.error_message = "No survey loaded"
                return

            # Read file content
            content = await file.read()

            # Upload to backend using the proper endpoint
            client = APIClient(token=auth_state.token)
            response = await client.upload_contacts(self.current_survey_id, content)

            self.contacts_count = response.get("contacts_added", 0)
            self.csv_uploaded = True
            self.error_message = ""
            self.success_message = f"Successfully uploaded {self.contacts_count} contacts to database!"

        except Exception as e:
            self.error_message = f"Failed to upload CSV: {str(e)}"
            self.csv_uploaded = False

    def clear_csv(self):
        """Clear uploaded CSV."""
        self.csv_uploaded = False
        self.csv_filename = ""
        self.contacts_count = 0
        self.contacts_data = []
        self.success_message = ""

    async def save_configuration(self):
        """Save voice agent configuration."""
        self.loading = True
        self.error_message = ""
        self.success_message = ""

        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                return

            client = APIClient(token=auth_state.token)

            # Use stored survey_id
            if not self.current_survey_id:
                self.error_message = "No survey ID available"
                self.loading = False
                return

            # Update voice configuration
            await client.update_voice_config(
                self.current_survey_id,
                {
                    "voice_agent_tone": self.voice_tone,
                    "voice_agent_instructions": self.custom_instructions if self.custom_instructions else None,
                    "max_call_duration": self.max_duration,
                    "max_retry_attempts": 2  # Default retry attempts
                }
            )

            self.success_message = "Configuration saved successfully!"

        except Exception as e:
            self.error_message = f"Failed to save configuration: {str(e)}"
        finally:
            self.loading = False

    async def launch_campaign(self):
        """Launch campaign with uploaded contacts."""
        if not self.csv_uploaded:
            self.error_message = "Please upload contacts CSV first"
            return

        self.loading = True
        self.error_message = ""
        self.success_message = ""

        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                return

            client = APIClient(token=auth_state.token)

            # Use stored survey_id
            if not self.current_survey_id:
                self.error_message = "No survey ID available"
                self.loading = False
                return

            # Launch campaign with test_mode=True
            campaign_data = await client.launch_campaign(
                self.current_survey_id,
                test_mode=True
            )

            self.success_message = f"Campaign launched successfully in test mode!"

            # Clear CSV after successful launch
            self.clear_csv()

        except Exception as e:
            self.error_message = f"Failed to launch campaign: {str(e)}"
        finally:
            self.loading = False
