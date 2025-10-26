"""Campaign management state."""
import reflex as rx
from typing import Optional
from frontend.services.api_client import APIClient
from frontend.models import CampaignStatus, PhoneInfo


class CampaignState(rx.State):
    """Handle campaign operations."""

    campaign_status: Optional[CampaignStatus] = None
    phone_info: Optional[PhoneInfo] = None
    loading: bool = False
    error_message: str = ""
    success_message: str = ""

    # Campaign launch in progress
    launching: bool = False

    async def launch_campaign(self, survey_id: str, test_mode: bool = False):
        """Launch a campaign."""
        self.launching = True
        self.error_message = ""
        self.success_message = ""

        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                return

            client = APIClient(token=auth_state.token)
            result = await client.launch_campaign(survey_id, test_mode)

            self.success_message = f"Campaign launched! Calling from {result.get('phone_number')}"

            # Load campaign status immediately
            await self.load_campaign_status(survey_id)

        except Exception as e:
            self.error_message = f"Failed to launch campaign: {str(e)}"
        finally:
            self.launching = False

    async def load_campaign_status(self, survey_id: str):
        """Load campaign status."""
        self.loading = True
        self.error_message = ""

        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                return

            client = APIClient(token=auth_state.token)
            status_data = await client.get_campaign_status(survey_id)
            self.campaign_status = CampaignStatus(**status_data)

        except Exception as e:
            self.error_message = f"Failed to load status: {str(e)}"
        finally:
            self.loading = False

    async def load_phone_info(self):
        """Load user's phone number info."""
        self.loading = True
        self.error_message = ""

        try:
            from frontend.state.auth_state import AuthState
            auth_state = await self.get_state(AuthState)

            if not auth_state.token:
                self.error_message = "Not authenticated"
                return

            client = APIClient(token=auth_state.token)
            info_data = await client.get_phone_number_info()
            self.phone_info = PhoneInfo(**info_data)

        except Exception as e:
            self.error_message = f"Failed to load phone info: {str(e)}"
        finally:
            self.loading = False

    async def provision_number(self):
        """Manually provision phone number."""
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
            result = await client.provision_number()

            self.success_message = f"Phone number provisioned: {result.get('phone_number')}"
            await self.load_phone_info()

        except Exception as e:
            self.error_message = f"Failed to provision number: {str(e)}"
        finally:
            self.loading = False

    def clear_messages(self):
        """Clear messages."""
        self.error_message = ""
        self.success_message = ""
