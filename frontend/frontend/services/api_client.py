"""API client for backend communication."""
import httpx
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")


class APIClient:
    """HTTP client for FastAPI backend."""

    def __init__(self, token: Optional[str] = None):
        self.base_url = BACKEND_URL
        self.token = token
        self.headers = {
            "Content-Type": "application/json"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to backend."""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{endpoint}"
            response = await client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    # ============================================
    # Authentication
    # ============================================

    def get_google_oauth_url(self) -> str:
        """Get Google OAuth login URL."""
        return f"{self.base_url}/auth/google/login"

    def get_microsoft_oauth_url(self) -> str:
        """Get Microsoft OAuth login URL."""
        return f"{self.base_url}/auth/microsoft/login"

    async def get_google_oauth_connect_url(self) -> Dict:
        """Get Google OAuth connection URL for forms access."""
        return await self._request("GET", "/auth/google/connect")

    async def get_microsoft_oauth_connect_url(self) -> Dict:
        """Get Microsoft OAuth connection URL for forms access."""
        return await self._request("GET", "/auth/microsoft/connect")

    async def get_oauth_connections(self) -> Dict:
        """Get list of connected OAuth providers."""
        return await self._request("GET", "/auth/connections")

    # ============================================
    # Surveys
    # ============================================

    async def fetch_form(self, form_url: str) -> Dict:
        """Fetch form structure from Google Forms or Microsoft Forms."""
        return await self._request(
            "GET",
            "/forms/fetch",
            params={"form_url": form_url}
        )

    async def create_survey(self, form_url: str, terms: Optional[str] = None) -> Dict:
        """Create survey from Google Form URL."""
        return await self._request(
            "POST",
            "/surveys",
            data={"form_url": form_url, "terms_and_conditions": terms}
        )

    async def list_surveys(self, status: Optional[str] = None) -> Dict:
        """List all surveys."""
        params = {"status": status} if status else None
        return await self._request("GET", "/surveys", params=params)

    async def get_survey(self, survey_id: str) -> Dict:
        """Get survey details."""
        return await self._request("GET", f"/surveys/{survey_id}")

    async def update_survey(self, survey_id: str, data: Dict) -> Dict:
        """Update survey configuration."""
        return await self._request("PUT", f"/surveys/{survey_id}", data=data)

    async def activate_survey(self, survey_id: str) -> Dict:
        """Activate survey."""
        return await self._request("POST", f"/surveys/{survey_id}/activate")

    async def deactivate_survey(self, survey_id: str) -> Dict:
        """Deactivate survey."""
        return await self._request("POST", f"/surveys/{survey_id}/deactivate")

    async def delete_survey(self, survey_id: str) -> Dict:
        """Delete survey."""
        return await self._request("DELETE", f"/surveys/{survey_id}")

    async def update_voice_config(self, survey_id: str, config: Dict) -> Dict:
        """Update voice agent configuration."""
        return await self._request("PUT", f"/surveys/{survey_id}/voice-config", data=config)

    async def export_survey_csv(self, survey_id: str) -> bytes:
        """Export survey responses as CSV."""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/surveys/{survey_id}/export/csv"
            response = await client.get(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            return response.content

    # ============================================
    # Campaigns
    # ============================================

    async def launch_campaign(self, survey_id: str, test_mode: bool = True) -> Dict:
        """Launch survey campaign."""
        return await self._request("POST", "/campaigns/launch", data={
            "survey_id": survey_id,
            "test_mode": test_mode
        })

    async def get_campaign_status(self, survey_id: str) -> Dict:
        """Get campaign status and statistics."""
        return await self._request("GET", f"/campaigns/{survey_id}/status")

    async def get_phone_number_info(self) -> Dict:
        """Get user's phone number information."""
        return await self._request("GET", "/campaigns/phone-number")

    async def provision_number(self) -> Dict:
        """Manually provision phone number."""
        return await self._request("POST", "/campaigns/provision-number")

    # ============================================
    # Contacts
    # ============================================

    async def upload_contacts(self, survey_id: str, csv_content: bytes) -> Dict:
        """Upload contact list CSV."""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/surveys/{survey_id}/contacts/upload"
            files = {"file": ("contacts.csv", csv_content, "text/csv")}
            response = await client.post(
                url,
                files=files,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def list_contacts(self, survey_id: str) -> List[Dict]:
        """List contacts for survey."""
        response = await self._request("GET", f"/surveys/{survey_id}/contacts")
        return response.get("contacts", [])

    # ============================================
    # Call Logs
    # ============================================

    async def get_call_logs(self, survey_id: str) -> Dict:
        """Get call logs for a survey."""
        return await self._request("GET", f"/surveys/{survey_id}/calls/logs")

    # ============================================
    # Callbacks
    # ============================================

    async def submit_callback_request(
        self,
        survey_id: str,
        name: str,
        phone: str,
        email: Optional[str],
        consent: bool
    ) -> Dict:
        """Submit callback request."""
        return await self._request(
            "POST",
            "/callbacks/request",
            data={
                "survey_id": survey_id,
                "participant_name": name,
                "phone_number": phone,
                "email": email,
                "consent": consent
            }
        )
