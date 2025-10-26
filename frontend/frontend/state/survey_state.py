"""Survey management state."""
import reflex as rx
from typing import List, Optional
from frontend.services.api_client import APIClient
from frontend.models import Survey


class SurveyState(rx.State):
    """Handle survey-related state and operations."""

    surveys: List[Survey] = []
    current_survey: Optional[Survey] = None
    loading: bool = False
    error_message: str = ""
    success_message: str = ""

    # OAuth connection status
    google_connected: bool = False
    microsoft_connected: bool = False
    checking_oauth: bool = False
    google_oauth_url: str = ""
    microsoft_oauth_url: str = ""

    # OAuth dialog control
    show_oauth_dialog: bool = False

    # OAuth connection link when needed
    oauth_auth_url: str = ""
    needs_oauth: bool = False
    oauth_provider: str = ""  # "google" or "microsoft"

    # Form fields for creating survey
    form_url: str = ""
    terms_and_conditions: str = ""

    # Filter
    status_filter: str = "all"

    @rx.var
    def total_surveys(self) -> int:
        """Total number of surveys."""
        return len(self.surveys)

    @rx.var
    def active_surveys(self) -> int:
        """Number of active surveys."""
        return len([s for s in self.surveys if s.status == "active"])

    @rx.var
    def draft_surveys(self) -> int:
        """Number of draft surveys."""
        return len([s for s in self.surveys if s.status == "draft"])

    @rx.var
    def has_surveys(self) -> bool:
        """Check if user has any surveys."""
        return len(self.surveys) > 0

    def set_form_url(self, value: str):
        """Set form URL."""
        self.form_url = value

    def set_terms_and_conditions(self, value: str):
        """Set terms and conditions."""
        self.terms_and_conditions = value

    def open_oauth_dialog(self):
        """Open OAuth connection dialog."""
        self.show_oauth_dialog = True

    def close_oauth_dialog(self):
        """Close OAuth connection dialog."""
        self.show_oauth_dialog = False

    def set_show_oauth_dialog(self, value: bool):
        """Set OAuth dialog visibility."""
        self.show_oauth_dialog = value

    async def check_oauth_connections(self):
        """Check which OAuth providers are connected."""
        self.checking_oauth = True
        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                print("No auth token found")
                return

            client = APIClient(token=auth_state.token)

            # Get connection status
            try:
                connections = await client.get_oauth_connections()
                self.google_connected = connections.get("google", False)
                self.microsoft_connected = connections.get("microsoft", False)
                print(f"OAuth connections: Google={self.google_connected}, Microsoft={self.microsoft_connected}")
            except Exception as e:
                print(f"Error getting connections: {e}")
                self.google_connected = False
                self.microsoft_connected = False

            # Get OAuth URLs if not connected
            if not self.google_connected:
                try:
                    google_oauth = await client.get_google_oauth_connect_url()
                    self.google_oauth_url = google_oauth.get("auth_url", "")
                    print(f"Got Google OAuth URL: {self.google_oauth_url[:50]}...")
                except Exception as e:
                    print(f"Error getting Google OAuth URL: {e}")
                    self.google_oauth_url = ""

        except Exception as e:
            print(f"Error in check_oauth_connections: {e}")
        finally:
            self.checking_oauth = False

    async def load_surveys(self):
        """Load all surveys for user."""
        self.loading = True
        self.error_message = ""
        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                return

            client = APIClient(token=auth_state.token)
            status = None if self.status_filter == "all" else self.status_filter
            result = await client.list_surveys(status=status)
            surveys_data = result.get("surveys", [])
            self.surveys = [Survey(**s) for s in surveys_data]
        except Exception as e:
            self.error_message = f"Failed to load surveys: {str(e)}"
        finally:
            self.loading = False

    async def create_survey(self):
        """Fetch and create new survey from Google Form."""
        if not self.form_url:
            self.error_message = "Please enter a form URL"
            return

        # Check which provider is needed based on URL
        form_url_lower = self.form_url.lower()
        is_google = "docs.google.com/forms" in form_url_lower
        is_microsoft = "forms.office.com" in form_url_lower or "forms.microsoft.com" in form_url_lower

        # Check if appropriate provider is connected
        if is_google and not self.google_connected:
            self.error_message = "Please connect your Google account first (see Step 1 above)"
            return
        elif is_microsoft and not self.microsoft_connected:
            self.error_message = "Please connect your Microsoft account first (see Step 1 above)"
            return
        elif not is_google and not is_microsoft:
            self.error_message = "Please enter a valid Google Forms or Microsoft Forms URL"
            return

        self.loading = True
        self.error_message = ""
        self.success_message = ""

        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                self.loading = False
                return

            client = APIClient(token=auth_state.token)

            # First, fetch the form to validate and get structure
            try:
                form_data = await client.fetch_form(self.form_url)

                # Check if form was fetched successfully
                if form_data.get("error"):
                    error_type = form_data.get("error_type", "")
                    action_required = form_data.get("action_required", "")

                    # Check if OAuth connection is needed
                    if action_required in ["connect_google", "connect_microsoft"]:
                        self.needs_oauth = True
                        self.oauth_provider = "Google" if "google" in action_required else "Microsoft"
                        self.oauth_auth_url = form_data.get("auth_url", "")
                        self.error_message = f"Please connect your {self.oauth_provider} account to fetch forms. Click the 'Connect {self.oauth_provider}' button below."
                    else:
                        self.error_message = f"Failed to fetch form: {form_data.get('message', 'Unknown error')}"

                    self.loading = False
                    return

                # Show success message about form fetch
                form_title = form_data.get("title", "Untitled Form")
                num_questions = len(form_data.get("questions", []))
                self.success_message = f"Form fetched successfully! Title: '{form_title}' with {num_questions} questions."
                self.needs_oauth = False
                self.oauth_auth_url = ""

            except Exception as fetch_error:
                error_str = str(fetch_error)
                # Check if it's an HTTP error with OAuth requirement
                if "400" in error_str or "401" in error_str:
                    # Try to get OAuth connect URL
                    try:
                        provider = "google" if "google" in self.form_url.lower() else "microsoft"
                        if provider == "google":
                            oauth_data = await client.get_google_oauth_connect_url()
                        else:
                            oauth_data = await client.get_microsoft_oauth_connect_url()

                        self.needs_oauth = True
                        self.oauth_provider = provider.title()
                        self.oauth_auth_url = oauth_data.get("auth_url", "")
                        self.error_message = f"Please connect your {self.oauth_provider} account to fetch forms."
                    except:
                        self.error_message = f"Failed to fetch form: {error_str}"
                else:
                    self.error_message = f"Failed to fetch form: {error_str}"
                self.loading = False
                return

            # Now create the survey with the fetched form
            survey = await client.create_survey(
                form_url=self.form_url,
                terms=self.terms_and_conditions or None
            )

            self.success_message = f"Survey created successfully! Survey ID: {survey.get('survey_id')}"
            self.form_url = ""
            self.terms_and_conditions = ""

            # Reload surveys
            await self.load_surveys()

        except Exception as e:
            self.error_message = f"Failed to create survey: {str(e)}"
        finally:
            self.loading = False

    async def load_survey(self, survey_id: str):
        """Load specific survey details."""
        self.loading = True
        self.error_message = ""

        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                return

            client = APIClient(token=auth_state.token)
            survey_data = await client.get_survey(survey_id)
            self.current_survey = Survey(**survey_data)

        except Exception as e:
            self.error_message = f"Failed to load survey: {str(e)}"
        finally:
            self.loading = False

    async def activate_survey(self, survey_id: str):
        """Activate a survey."""
        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            client = APIClient(token=auth_state.token)
            await client.activate_survey(survey_id)
            self.success_message = "Survey activated"
            await self.load_surveys()

        except Exception as e:
            self.error_message = f"Failed to activate survey: {str(e)}"

    async def deactivate_survey(self, survey_id: str):
        """Deactivate a survey."""
        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            client = APIClient(token=auth_state.token)
            await client.deactivate_survey(survey_id)
            self.success_message = "Survey deactivated"
            await self.load_surveys()

        except Exception as e:
            self.error_message = f"Failed to deactivate survey: {str(e)}"

    async def delete_survey(self, survey_id: str):
        """Delete a survey."""
        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            client = APIClient(token=auth_state.token)
            await client.delete_survey(survey_id)
            self.success_message = "Survey deleted"
            await self.load_surveys()

        except Exception as e:
            self.error_message = f"Failed to delete survey: {str(e)}"

    def set_status_filter(self, status: str):
        """Set status filter."""
        self.status_filter = status

    def clear_messages(self):
        """Clear success/error messages."""
        self.error_message = ""
        self.success_message = ""
