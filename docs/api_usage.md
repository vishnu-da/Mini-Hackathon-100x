# API Usage Guide

Examples and best practices for integrating OAuth and form fetching into your application.

## Table of Contents

1. [Authentication Flow](#authentication-flow)
2. [Connecting OAuth Providers](#connecting-oauth-providers)
3. [Fetching Forms](#fetching-forms)
4. [Error Handling](#error-handling)
5. [Frontend Integration](#frontend-integration)
6. [Backend Integration](#backend-integration)

---

## Authentication Flow

### Complete User Journey

```
1. User creates account (Supabase Auth)
   ↓
2. User wants to import a Google Form
   ↓
3. System detects no Google OAuth connection
   ↓
4. User clicks "Connect Google Account"
   ↓
5. System redirects to Google OAuth
   ↓
6. User authorizes
   ↓
7. System stores tokens
   ↓
8. User can now import Google Forms
```

---

## Connecting OAuth Providers

### Step 1: Check Current Connections

**Endpoint**: `GET /auth/connections`

```python
import httpx

async def check_connections(user_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/auth/connections",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        data = response.json()
        print(f"Google connected: {data['google']}")
        print(f"Microsoft connected: {data['microsoft']}")
        return data
```

**Response**:
```json
{
  "google": false,
  "microsoft": false
}
```

### Step 2: Connect Google Account

**Endpoint**: `GET /auth/google/connect`

```python
async def connect_google(user_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/auth/google/connect",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        data = response.json()

        # Redirect user to this URL
        auth_url = data['auth_url']
        print(f"Visit this URL: {auth_url}")

        # Store state for validation (optional)
        state = data['state']

        return auth_url
```

**Response**:
```json
{
  "provider": "google",
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
  "state": "abc123...",
  "message": "Please visit the auth_url to authorize Google Forms access"
}
```

### Step 3: Handle OAuth Callback

The callback is handled automatically by the backend. Users are redirected to:

- Success: `/oauth/success?provider=google`
- Error: `/oauth/error?provider=google&error=...`

Your frontend should have routes for these pages.

### Step 4: Connect Microsoft Account

Same process but use `/auth/microsoft/connect`

```python
async def connect_microsoft(user_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/auth/microsoft/connect",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        return response.json()['auth_url']
```

---

## Fetching Forms

### Using the Form Fetcher Service

```python
from app.services.form_fetcher import fetch_form, validate_form_access

# Example 1: Check if user can access a form
async def check_form_access_example():
    user_id = "user-uuid-here"
    form_url = "https://docs.google.com/forms/d/abc123/edit"

    validation = await validate_form_access(user_id, form_url)

    if validation['has_access']:
        print("User can access this form!")
    elif validation['needs_auth']:
        print(f"User needs to connect {validation['provider']}")
        print(f"Auth URL: {validation['auth_url']}")


# Example 2: Fetch a form
async def fetch_form_example():
    user_id = "user-uuid-here"
    form_url = "https://docs.google.com/forms/d/abc123/edit"

    result = await fetch_form(user_id, form_url)

    if result.get('error'):
        # Handle error
        print(f"Error: {result['message']}")
        if result.get('action_required'):
            print(f"Action needed: {result['action_required']}")
    else:
        # Success! Process the form
        print(f"Form Title: {result['title']}")
        print(f"Questions: {len(result['questions'])}")
        for q in result['questions']:
            print(f"  - {q['question_text']}")
```

### Google Forms Example

```python
from app.services.google_forms_client import fetch_form as fetch_google_form

async def fetch_google_form_example():
    form_id = "1FAIpQLSe..."  # Extract from URL
    access_token = "ya29.a0..."  # Get from OAuth service

    try:
        questionnaire = await fetch_google_form(form_id, access_token)

        # questionnaire structure:
        # {
        #   "title": "Customer Feedback Survey",
        #   "form_type": "google",
        #   "form_id": "1FAIpQLSe...",
        #   "fetched_at": "2025-10-08T18:30:00Z",
        #   "questions": [...]
        # }

        return questionnaire

    except GoogleFormsError as e:
        print(f"Error: {e}")
```

### Microsoft Forms Example

```python
from app.services.microsoft_forms_client import fetch_form as fetch_microsoft_form

async def fetch_microsoft_form_example():
    form_id = "u/d/..."  # Extract from URL
    access_token = "EwCAA8l6..."  # Get from OAuth service

    try:
        questionnaire = await fetch_microsoft_form(form_id, access_token)
        return questionnaire

    except MicrosoftFormsError as e:
        print(f"Error: {e}")
```

---

## Error Handling

### Error Response Format

```json
{
  "error": true,
  "error_type": "not_authorized",
  "message": "Please connect your Google account to import forms.",
  "action_required": "connect_google",
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

### Error Types

| Error Type | Description | Action Required |
|------------|-------------|----------------|
| `not_authorized` | User hasn't connected OAuth account | Show connect button |
| `form_not_found` | Form ID is invalid or doesn't exist | Ask for valid URL |
| `permission_denied` | User doesn't have access to form | Check form sharing settings |
| `rate_limit` | API rate limit exceeded | Retry after delay |
| `invalid_url` | Unsupported form URL | Support only Google/Microsoft |
| `api_error` | Generic API error | Show error message |

### Handling Different Errors

```python
async def handle_form_fetch(user_id: str, form_url: str):
    result = await fetch_form(user_id, form_url)

    if not result.get('error'):
        # Success - process the form
        return process_questionnaire(result)

    error_type = result['error_type']

    if error_type == 'not_authorized':
        # User needs to connect OAuth
        return {
            "status": "needs_auth",
            "provider": result.get('action_required').replace('connect_', ''),
            "auth_url": result.get('auth_url')
        }

    elif error_type == 'form_not_found':
        return {
            "status": "error",
            "message": "Form not found. Please check the URL."
        }

    elif error_type == 'permission_denied':
        return {
            "status": "error",
            "message": "You don't have permission to access this form."
        }

    elif error_type == 'rate_limit':
        return {
            "status": "error",
            "message": "Too many requests. Please try again in a minute."
        }

    else:
        return {
            "status": "error",
            "message": result['message']
        }
```

---

## Frontend Integration

### React Example

```typescript
// hooks/useOAuth.ts
import { useState } from 'react';

export function useOAuth() {
  const [loading, setLoading] = useState(false);

  const connectGoogle = async () => {
    setLoading(true);
    try {
      const response = await fetch('/auth/google/connect', {
        headers: {
          'Authorization': `Bearer ${getUserToken()}`
        }
      });
      const data = await response.json();

      // Redirect to OAuth page
      window.location.href = data.auth_url;
    } catch (error) {
      console.error('Error connecting Google:', error);
    } finally {
      setLoading(false);
    }
  };

  const connectMicrosoft = async () => {
    // Similar implementation
  };

  const checkConnections = async () => {
    const response = await fetch('/auth/connections', {
      headers: {
        'Authorization': `Bearer ${getUserToken()}`
      }
    });
    return response.json();
  };

  return { connectGoogle, connectMicrosoft, checkConnections, loading };
}

// components/OAuthButton.tsx
export function OAuthButton({ provider }: { provider: 'google' | 'microsoft' }) {
  const { connectGoogle, connectMicrosoft, loading } = useOAuth();

  const handleConnect = provider === 'google' ? connectGoogle : connectMicrosoft;

  return (
    <button
      onClick={handleConnect}
      disabled={loading}
      className="oauth-button"
    >
      {loading ? 'Connecting...' : `Connect ${provider}`}
    </button>
  );
}

// pages/oauth-success.tsx
export function OAuthSuccessPage() {
  const searchParams = useSearchParams();
  const provider = searchParams.get('provider');

  return (
    <div>
      <h1>Successfully Connected!</h1>
      <p>You can now import {provider} forms.</p>
      <button onClick={() => router.push('/surveys/create')}>
        Create Survey
      </button>
    </div>
  );
}
```

### Form Import Component

```typescript
// components/FormImporter.tsx
import { useState } from 'react';

export function FormImporter() {
  const [formUrl, setFormUrl] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [questionnaire, setQuestionnaire] = useState(null);
  const [error, setError] = useState(null);

  const handleImport = async () => {
    setStatus('loading');

    try {
      // First, validate access
      const validateResponse = await fetch(
        `/api/forms/validate?url=${encodeURIComponent(formUrl)}`,
        {
          headers: { 'Authorization': `Bearer ${getUserToken()}` }
        }
      );
      const validation = await validateResponse.json();

      if (validation.needs_auth) {
        // Show OAuth connection button
        setError({
          type: 'needs_auth',
          provider: validation.provider,
          authUrl: validation.auth_url
        });
        setStatus('error');
        return;
      }

      // Fetch the form
      const fetchResponse = await fetch('/api/forms/fetch', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getUserToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ form_url: formUrl })
      });

      const result = await fetchResponse.json();

      if (result.error) {
        setError(result);
        setStatus('error');
      } else {
        setQuestionnaire(result);
        setStatus('success');
      }

    } catch (err) {
      setError({ message: 'An unexpected error occurred' });
      setStatus('error');
    }
  };

  return (
    <div>
      <input
        type="url"
        placeholder="Paste Google Forms or Microsoft Forms URL"
        value={formUrl}
        onChange={(e) => setFormUrl(e.target.value)}
      />

      <button onClick={handleImport} disabled={status === 'loading'}>
        {status === 'loading' ? 'Importing...' : 'Import Form'}
      </button>

      {error && error.type === 'needs_auth' && (
        <div className="oauth-prompt">
          <p>Please connect your {error.provider} account first.</p>
          <button onClick={() => window.location.href = error.authUrl}>
            Connect {error.provider}
          </button>
        </div>
      )}

      {error && error.type !== 'needs_auth' && (
        <div className="error">
          {error.message}
        </div>
      )}

      {status === 'success' && questionnaire && (
        <div className="questionnaire">
          <h2>{questionnaire.title}</h2>
          <p>{questionnaire.questions.length} questions imported</p>
          {/* Display questions */}
        </div>
      )}
    </div>
  );
}
```

---

## Backend Integration

### Creating a Survey with Form Import

```python
from app.services.form_fetcher import fetch_form
from app.database import create_survey

async def create_survey_from_form(user_id: str, form_url: str, survey_name: str):
    """
    Create a survey by importing a Google or Microsoft Form.
    """
    # Fetch the form
    result = await fetch_form(user_id, form_url)

    if result.get('error'):
        # Return error to user
        return {
            "success": False,
            "error": result
        }

    # Create survey in database
    survey_data = {
        "user_id": user_id,
        "name": survey_name,
        "form_link": form_url,
        "json_questionnaire": result,  # Store the full questionnaire
        "status": "draft",
    }

    survey = await create_survey(survey_data)

    return {
        "success": True,
        "survey": survey,
        "questionnaire": result
    }
```

### API Endpoint Example

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth import get_current_user_id
from app.services.form_fetcher import fetch_form

router = APIRouter()

class FormImportRequest(BaseModel):
    form_url: str
    survey_name: str

@router.post("/api/surveys/import")
async def import_form_as_survey(
    request: FormImportRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Import a form and create a survey."""
    result = await create_survey_from_form(
        user_id=user_id,
        form_url=request.form_url,
        survey_name=request.survey_name
    )

    if not result['success']:
        error = result['error']
        if error['error_type'] == 'not_authorized':
            raise HTTPException(
                status_code=401,
                detail={
                    "message": error['message'],
                    "action_required": error['action_required'],
                    "auth_url": error.get('auth_url')
                }
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=error['message']
            )

    return result['survey']
```

---

## Best Practices

### 1. Token Management

```python
# Always use the unified form_fetcher
# It handles token refresh automatically
from app.services.form_fetcher import fetch_form

# DON'T manually manage tokens
# DO use the service layer
```

### 2. Error Handling

```python
# Provide helpful error messages to users
# Guide them to the next action

if error_type == 'not_authorized':
    return "Please connect your Google account in Settings"

if error_type == 'permission_denied':
    return "This form is private. Please check sharing settings."
```

### 3. State Management

```python
# For production, use Redis for OAuth state
# Don't rely on in-memory storage

# Good
redis.setex(f"oauth_state:{state}", 600, user_id)

# Bad (current implementation)
oauth_states[state] = user_id  # Lost on restart
```

### 4. Rate Limiting

```python
# Implement rate limiting to avoid API quotas

from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@router.post("/import", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def import_form(...):
    # Limited to 10 requests per minute per user
    pass
```

---

## Testing

### Manual Testing Script

```python
import asyncio
from app.services.form_fetcher import fetch_form

async def test_form_import():
    # Test Google Form
    google_result = await fetch_form(
        user_id="test-user-uuid",
        form_url="https://docs.google.com/forms/d/abc123/edit"
    )
    print("Google Form:", google_result)

    # Test Microsoft Form
    microsoft_result = await fetch_form(
        user_id="test-user-uuid",
        form_url="https://forms.office.com/Pages/ResponsePage.aspx?id=xyz789"
    )
    print("Microsoft Form:", microsoft_result)

if __name__ == "__main__":
    asyncio.run(test_form_import())
```

---

## Common Patterns

### Pattern 1: Progressive Enhancement

```python
# Check if user has OAuth, if not, prompt them
async def get_or_prompt_oauth(user_id: str, provider: str):
    has_token = await has_valid_token(user_id, provider)

    if has_token:
        return {"status": "ready"}
    else:
        auth_url = get_google_auth_url(...)
        return {
            "status": "needs_auth",
            "auth_url": auth_url
        }
```

### Pattern 2: Background Sync

```python
# After importing, periodically sync form responses
from celery import task

@task
async def sync_form_responses(survey_id: str):
    survey = await get_survey_by_id(survey_id)

    # Fetch latest responses from Google Forms API
    responses = await fetch_form_responses(survey.form_link)

    # Store in database
    await store_responses(survey_id, responses)
```

---

## Summary

1. **Check connections**: `GET /auth/connections`
2. **Connect provider**: `GET /auth/{provider}/connect`
3. **User authorizes**: Via OAuth redirect
4. **Fetch forms**: Use `form_fetcher.fetch_form()`
5. **Handle errors**: Guide users to correct action

For complete examples, see the test files and API documentation.
