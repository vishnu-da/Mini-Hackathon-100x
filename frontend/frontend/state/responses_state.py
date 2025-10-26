"""Responses state management."""
import reflex as rx
from typing import Optional, List, Dict, Any
from frontend.services.api_client import APIClient
from frontend.models import Survey


class ResponsesState(rx.State):
    """Handle responses page state and operations."""

    survey: Optional[Survey] = None
    call_logs: List[Dict[str, Any]] = []
    loading: bool = False
    error_message: str = ""
    success_message: str = ""
    current_survey_id: str = ""

    async def load_responses(self):
        """Load survey and call logs."""
        self.loading = True
        self.error_message = ""
        self.call_logs = []

        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                self.loading = False
                return

            # Get survey_id from URL path
            url_path = self.router.page.raw_path
            survey_id = url_path.split("/responses")[0].split("/survey/")[-1] if "/survey/" in url_path else ""

            if not survey_id:
                self.error_message = "No survey ID in URL"
                self.loading = False
                return

            self.current_survey_id = survey_id
            client = APIClient(token=auth_state.token)

            # Load survey details
            survey_data = await client.get_survey(survey_id)
            self.survey = Survey(**survey_data)

            # Load call logs
            logs_data = await client.get_call_logs(survey_id)
            self.call_logs = logs_data.get("call_logs", [])

        except Exception as e:
            self.error_message = f"Failed to load responses: {str(e)}"
        finally:
            self.loading = False

    async def download_csv(self):
        """Download responses as CSV."""
        self.error_message = ""
        self.success_message = ""

        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                return

            client = APIClient(token=auth_state.token)
            csv_content = await client.export_survey_csv(self.current_survey_id)

            # Trigger download via browser
            import base64
            csv_base64 = base64.b64encode(csv_content).decode()

            # Return download info
            return rx.download(
                data=csv_base64,
                filename=f"survey_{self.current_survey_id}_responses.csv"
            )

        except Exception as e:
            self.error_message = f"Failed to download CSV: {str(e)}"
