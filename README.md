 # AI Voice Survey Platform - Backend

A FastAPI-based backend for managing AI-powered voice surveys using Twilio for voice calls, OpenAI for conversational AI, and Supabase for data persistence.

## Features

- 🚀 **FastAPI Framework** - Modern, fast, and async Python web framework
- 📞 **Twilio Integration** - Automated voice call management
- 🤖 **OpenAI Integration** - AI-powered conversational surveys
- 💾 **Supabase Database** - Real-time database and authentication
- 🎭 **Playwright Support** - Browser automation capabilities
- 🔒 **Environment Configuration** - Secure configuration management

## Project Structure

```
RESO/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration and environment variables
│   ├── database.py          # Supabase client initialization
│   ├── models.py            # Pydantic models for requests/responses
│   └── routers/             # API route handlers
│       └── __init__.py
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.9 or higher
- pip package manager
- Supabase account and project
- Twilio account with phone number
- OpenAI API key

### 2. Installation

Clone the repository and install dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (if needed)
playwright install
```

### 3. Environment Configuration

Copy the `.env.example` file to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here

# Twilio Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Application Configuration
APP_ENV=development
DEBUG=True
API_HOST=0.0.0.0
API_PORT=8000
```

### 4. Running the Application

Start the FastAPI development server:

```bash
# Using Python directly
python app/main.py

# Or using uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Health Check
- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

### Surveys (To be implemented)
- `POST /api/surveys` - Create a new survey
- `GET /api/surveys` - List all surveys
- `GET /api/surveys/{id}` - Get survey by ID
- `PUT /api/surveys/{id}` - Update survey
- `DELETE /api/surveys/{id}` - Delete survey

### Calls (To be implemented)
- `POST /api/calls` - Initiate a new call
- `GET /api/calls` - List all calls
- `GET /api/calls/{id}` - Get call details
- `PUT /api/calls/{id}` - Update call status

### Webhooks (To be implemented)
- `POST /webhooks/twilio` - Twilio webhook handler
- `POST /webhooks/openai` - OpenAI callback handler

## Data Models

### Survey Models
- **SurveyCreate** - Create new survey
- **SurveyUpdate** - Update existing survey
- **SurveyResponse** - Survey data response

### Call Models
- **CallCreate** - Initiate new call
- **CallUpdate** - Update call status
- **CallResponse** - Call data response

### Response Models
- **SurveyResponseCreate** - Submit survey responses
- **SurveyResponseData** - Survey response data

## Development

### Adding New Routes

Create a new router file in `app/routers/`:

```python
from fastapi import APIRouter, Depends
from app.database import get_db
from app.models import YourModel

router = APIRouter()

@router.get("/your-endpoint")
async def your_endpoint(db = Depends(get_db)):
    # Your logic here
    pass
```

Then include it in `app/main.py`:

```python
from app.routers import your_router
app.include_router(your_router.router, prefix="/api/your-prefix", tags=["your-tag"])
```

## Deployment

### Production Settings

For production deployment:

1. Set `APP_ENV=production` in `.env`
2. Set `DEBUG=False`
3. Use a proper CORS configuration
4. Use environment-specific settings
5. Set up proper logging and monitoring

### Docker (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Dependencies

- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **supabase** - Database client
- **twilio** - Voice call service
- **openai** - AI integration
- **playwright** - Browser automation
- **python-dotenv** - Environment management
- **pydantic** - Data validation
- **httpx** - HTTP client

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please create an issue in the repository.
