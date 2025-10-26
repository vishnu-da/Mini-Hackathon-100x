"""
FastAPI application entry point for AI Voice Survey platform.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from app.config import get_settings
from app.models import HealthCheckResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Voice Survey Platform",
    description="Backend API for managing AI-powered voice surveys",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Get settings
settings = get_settings()

# Configure CORS for OAuth redirects
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend development
        "http://localhost:8000",  # Backend
        "https://yourdomain.com",  # Production (update this)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Execute on application startup."""
    logger.info("Starting AI Voice Survey Platform...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")


@app.on_event("shutdown")
async def shutdown_event():
    """Execute on application shutdown."""
    logger.info("Shutting down AI Voice Survey Platform...")


@app.get("/", response_model=HealthCheckResponse)
async def root():
    """Root endpoint - health check."""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )


# Import and include routers
from app.routers import auth, forms, surveys, contacts, calls, webhooks, campaigns, callbacks

# OAuth authentication routes
app.include_router(auth.router, prefix="/auth", tags=["oauth"])

# Form fetching routes
app.include_router(forms.router, prefix="/forms", tags=["forms"])

# Survey management routes
app.include_router(surveys.router, prefix="/surveys", tags=["surveys"])

# Contact management routes
app.include_router(contacts.router, prefix="/surveys", tags=["contacts"])

# Call management routes
app.include_router(calls.router, prefix="/surveys", tags=["calls"])

# Campaign management routes (NEW - SaaS backend)
app.include_router(campaigns.router, tags=["campaigns"])

# Callback link routes (NEW - callback functionality)
app.include_router(callbacks.router, tags=["callbacks"])

# Webhook routes (Twilio callbacks)
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
