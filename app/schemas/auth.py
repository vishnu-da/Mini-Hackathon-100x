"""
Authentication and OAuth schemas.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OAuthConnectionResponse(BaseModel):
    """Response for OAuth connection initiation."""
    provider: str
    auth_url: str
    state: str
    message: str = "Please visit the auth_url to authorize"


class OAuthCallbackResponse(BaseModel):
    """Response for OAuth callback handling."""
    success: bool
    provider: str
    message: str
    redirect_url: Optional[str] = None


class ConnectedProvidersResponse(BaseModel):
    """Response showing which OAuth providers are connected."""
    google: bool
    microsoft: bool


class TokenInfo(BaseModel):
    """Information about an OAuth token."""
    provider: str
    has_token: bool
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None


class DisconnectResponse(BaseModel):
    """Response for OAuth disconnection."""
    success: bool
    provider: str
    message: str


class FormAccessValidation(BaseModel):
    """Validation result for form access."""
    has_access: bool
    provider: str
    needs_auth: bool
    auth_url: Optional[str] = None
    error: Optional[str] = None


class LoginRequest(BaseModel):
    """Request for user login."""
    email: str
    password: str


class LoginResponse(BaseModel):
    """Response for successful login."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: Optional[str] = None
