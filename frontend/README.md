# AI Voice Survey Platform - Frontend

Modern web interface built with Python Reflex.

## Setup

1. Install dependencies:
```bash
cd frontend
pip install -r requirements.txt
```

2. Create `.env` file:
```bash
cp .env.example .env
```

3. Run the frontend:
```bash
reflex run
```

Frontend will start at: `http://localhost:3000`

## Architecture

- **State Management:** Reflex State system
- **API Client:** `httpx` for async HTTP requests
- **Backend URL:** `http://localhost:8000` (FastAPI)
- **Styling:** Chakra UI components via Reflex

## Features

### Authentication
- Google OAuth login
- Microsoft OAuth login
- JWT token management

### Dashboard
- View all surveys
- Filter by status (all/active/draft/closed)
- Quick stats overview
- Create new survey

### Survey Management
- Import from Google Forms
- Add terms and conditions
- View questionnaire structure
- Activate/deactivate surveys

### Campaign Launch
- One-click campaign launch
- Test mode (1 contact)
- Real-time status monitoring
- Auto phone provisioning
- Progress tracking

### Future Pages (To Be Built)
- Contact management and upload
- Response viewer with export
- Survey detail editor
- Settings and profile

## Project Structure

```
frontend/
├── frontend/
│   ├── components/       # Reusable UI components
│   │   ├── navbar.py
│   │   ├── card.py
│   │   └── alerts.py
│   ├── pages/           # Page components
│   │   ├── login.py
│   │   ├── dashboard.py
│   │   ├── create_survey.py
│   │   └── campaign.py
│   ├── services/        # Backend API integration
│   │   └── api_client.py
│   ├── state/           # State management
│   │   ├── auth_state.py
│   │   ├── survey_state.py
│   │   └── campaign_state.py
│   └── frontend.py      # Main app file
├── rxconfig.py          # Reflex configuration
└── requirements.txt     # Python dependencies
```

## Running

Start backend first:
```bash
cd ../
python -m app.main
```

Start frontend:
```bash
cd frontend
reflex run
```

Navigate to `http://localhost:3000`

## Notes

- Backend must be running on port 8000
- OAuth callbacks handled by backend
- JWT tokens stored in Reflex state
- All API calls are async using httpx
