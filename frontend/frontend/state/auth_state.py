"""Authentication state management with Supabase."""
import reflex as rx
from typing import Optional
import os
import httpx


class AuthState(rx.State):
    """Handle authentication state with Supabase."""

    # Form fields
    email: str = ""
    password: str = ""

    # Auth state
    token: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    is_authenticated: bool = False

    # UI state
    loading: bool = False
    error_message: str = ""

    def set_email(self, value: str):
        """Set email field."""
        self.email = value
        self.error_message = ""  # Clear error when user types

    def set_password(self, value: str):
        """Set password field."""
        self.password = value
        self.error_message = ""  # Clear error when user types

    async def login_with_supabase(self):
        """Login via backend endpoint."""
        self.loading = True
        self.error_message = ""

        try:
            # Validate inputs
            if not self.email or not self.password:
                self.error_message = "Please enter email and password"
                self.loading = False
                return

            # Call backend /auth/login endpoint
            backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{backend_url}/auth/login",
                    json={
                        "email": self.email,
                        "password": self.password
                    },
                    headers={
                        "Content-Type": "application/json"
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()

                    # Extract token and user info from backend response
                    self.token = data.get("access_token")
                    self.user_id = data.get("user_id")
                    self.user_email = data.get("email")
                    self.user_name = data.get("name", "")
                    self.is_authenticated = True

                    # Clear form
                    self.email = ""
                    self.password = ""
                    self.loading = False

                    # Redirect to dashboard
                    return rx.redirect("/dashboard")
                else:
                    error_data = response.json()
                    self.error_message = error_data.get("detail", "Login failed")
                    self.loading = False

        except httpx.TimeoutException:
            self.error_message = "Connection timeout. Please try again."
            self.loading = False
        except httpx.RequestError:
            self.error_message = "Cannot connect to server. Please check your connection."
            self.loading = False
        except Exception as e:
            self.error_message = f"Login error: {str(e)}"
            self.loading = False

    def check_auth(self):
        """Check if user is authenticated, redirect to login if not."""
        if not self.is_authenticated:
            return rx.redirect("/login")

    def set_token(self, token: str):
        """Set authentication token."""
        self.token = token
        self.is_authenticated = True

    def set_user_info(self, user_id: str, email: str, name: str):
        """Set user information."""
        self.user_id = user_id
        self.user_email = email
        self.user_name = name

    def logout(self):
        """Clear authentication state."""
        self.token = None
        self.user_id = None
        self.user_email = None
        self.user_name = None
        self.is_authenticated = False
        self.email = ""
        self.password = ""
        self.error_message = ""
        return rx.redirect("/login")

    @rx.var
    def user_display_name(self) -> str:
        """Get display name for user."""
        return self.user_name or self.user_email or "User"
