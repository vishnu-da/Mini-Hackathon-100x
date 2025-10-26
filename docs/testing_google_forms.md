# Testing Google Forms API Integration

Complete guide to test fetching Google Forms using OAuth and the official Google Forms API.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Manual Testing Steps](#manual-testing-steps)
5. [Testing with Python Scripts](#testing-with-python-scripts)
6. [Testing via API Endpoints](#testing-via-api-endpoints)
7. [Common Issues](#common-issues)

---

## Prerequisites

### 1. Google Cloud Project Setup

Before testing, ensure you have:

- ✅ Google Cloud Project created
- ✅ Google Forms API enabled
- ✅ OAuth 2.0 credentials created
- ✅ OAuth consent screen configured
- ✅ Redirect URI added: `http://localhost:8000/auth/google/callback`

**If not done yet, follow:** `docs/oauth_setup_guide.md` → Google OAuth Setup section

### 2. Test Google Form

Create a test form or use an existing one:

1. Go to [Google Forms](https://forms.google.com)
2. Create a new form with various question types:
   - Multiple choice
   - Checkboxes
   - Short answer
   - Paragraph
   - Linear scale
   - Dropdown

3. Make note of the form URL:
   - Edit URL: `https://docs.google.com/forms/d/YOUR_FORM_ID/edit`
   - View URL: `https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform`

---

## Environment Setup

### 1. Update .env File

Add your Google OAuth credentials to `.env`:

```bash
# Copy from .env.example if you haven't
cp .env.example .env
```

Edit `.env`:

```env
# Supabase Configuration (required)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-your_client_secret_here
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Google Forms Scope (should already be set)
GOOGLE_FORMS_SCOPE=https://www.googleapis.com/auth/forms.body.readonly https://www.googleapis.com/auth/forms.responses.readonly

# Other required settings
OPENAI_API_KEY=sk-...  # Can be dummy for form testing
TWILIO_ACCOUNT_SID=AC...  # Can be dummy for form testing
TWILIO_AUTH_TOKEN=...  # Can be dummy for form testing
TWILIO_PHONE_NUMBER=+1...  # Can be dummy for form testing
```

### 2. Install Dependencies

```bash
# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Verify Configuration

```bash
python -c "from app.config import get_settings; s = get_settings(); print(f'Google Client ID: {s.google_oauth_client_id[:20]}...')"
```

Should print your client ID (truncated).

---

## Database Setup

### 1. Run Migrations

In Supabase Dashboard → SQL Editor, run these migrations in order:

```sql
-- 1. Run migrations/001_create_schema.sql
-- 2. Run migrations/003_add_oauth_tokens.sql
```

### 2. Create Test User

You need a user account in Supabase Auth:

**Option A: Via Supabase Dashboard**
1. Go to Authentication → Users
2. Click "Add user"
3. Email: `test@example.com`
4. Password: `Test123!@#`
5. Auto-confirm user: Yes
6. Copy the User UID

**Option B: Via API**
```python
from supabase import create_client
from app.config import get_settings

settings = get_settings()
supabase = create_client(settings.supabase_url, settings.supabase_service_key)

# Create user
user = supabase.auth.admin.create_user({
    "email": "test@example.com",
    "password": "Test123!@#",
    "email_confirm": True
})
print(f"User ID: {user.user.id}")
```

### 3. Create User Record in Database

```sql
-- In Supabase SQL Editor
INSERT INTO users (user_id, email, name)
VALUES (
    'the-user-uid-from-step-2',
    'test@example.com',
    'Test User'
);
```

---

## Manual Testing Steps

### Step 1: Start the Backend Server

```bash
# Make sure you're in the project directory
python app/main.py
```

Should see:
```
INFO:     Starting AI Voice Survey Platform...
INFO:     Environment: development
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Test API Documentation

Open browser: `http://localhost:8000/docs`

You should see the FastAPI interactive documentation with OAuth endpoints.

### Step 3: Get Authentication Token

Since we're testing, we'll get a token directly:

```bash
# In a new terminal
curl -X POST "https://YOUR_SUPABASE_URL/auth/v1/token?grant_type=password" \
  -H "apikey: YOUR_SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#"
  }'
```

Save the `access_token` from the response.

Or use Python:

```python
from supabase import create_client
from app.config import get_settings

settings = get_settings()
supabase = create_client(settings.supabase_url, settings.supabase_anon_key)

# Sign in
response = supabase.auth.sign_in_with_password({
    "email": "test@example.com",
    "password": "Test123!@#"
})

access_token = response.session.access_token
print(f"Token: {access_token}")
```

### Step 4: Connect Google Account

**Option A: Via Browser (Recommended)**

1. Go to `http://localhost:8000/docs`
2. Click on `GET /auth/google/connect`
3. Click "Try it out"
4. Click "Execute"
5. Copy the `auth_url` from the response
6. Open the URL in a browser
7. Sign in with Google
8. Authorize the application
9. You'll be redirected to `/oauth/success?provider=google`

**Option B: Via cURL**

```bash
curl -X GET "http://localhost:8000/auth/google/connect" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Copy the `auth_url` and open in browser.

### Step 5: Verify Connection

```bash
curl -X GET "http://localhost:8000/auth/connections" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Should return:
```json
{
  "google": true,
  "microsoft": false
}
```

### Step 6: Test Form Fetching

Now test fetching a Google Form:

```bash
# Get your Google Form URL
FORM_URL="https://docs.google.com/forms/d/YOUR_FORM_ID/edit"

# Test via Python
python << EOF
import asyncio
from app.services.form_fetcher import fetch_form

async def test():
    result = await fetch_form(
        user_id="your-user-uuid",
        form_url="$FORM_URL"
    )
    print(result)

asyncio.run(test())
EOF
```

Expected output:
```json
{
  "title": "Your Form Title",
  "form_type": "google",
  "form_id": "YOUR_FORM_ID",
  "fetched_at": "2025-10-08T19:30:00Z",
  "questions": [
    {
      "question_id": "q1",
      "question_text": "What is your name?",
      "question_type": "short_answer",
      "options": null,
      "required": true,
      "scale_min": null,
      "scale_max": null
    }
  ]
}
```

---

## Testing with Python Scripts

### Test Script 1: Complete OAuth Flow

Create `test_oauth.py`:

```python
"""Test Google Forms OAuth integration."""
import asyncio
from app.services import oauth_service
from app.services.form_fetcher import fetch_form
from app.config import get_settings

# Replace with your user ID
USER_ID = "your-user-uuid-here"
FORM_URL = "https://docs.google.com/forms/d/YOUR_FORM_ID/edit"


async def test_oauth_flow():
    """Test complete OAuth flow."""
    print("=== Testing Google OAuth ===\n")

    # Step 1: Check if user has token
    print("1. Checking for existing token...")
    has_token = await oauth_service.has_valid_token(USER_ID, "google")
    print(f"   Has valid token: {has_token}\n")

    if not has_token:
        print("   User needs to connect Google account first!")
        print("   Visit: http://localhost:8000/docs")
        print("   Use: GET /auth/google/connect")
        return

    # Step 2: Get valid token (will auto-refresh if needed)
    print("2. Getting valid access token...")
    try:
        token = await oauth_service.get_valid_token(USER_ID, "google")
        print(f"   Token obtained: {token[:20]}...\n")
    except Exception as e:
        print(f"   Error: {e}\n")
        return

    # Step 3: Fetch a form
    print("3. Fetching Google Form...")
    result = await fetch_form(USER_ID, FORM_URL)

    if result.get('error'):
        print(f"   Error: {result['message']}")
        print(f"   Error type: {result['error_type']}")
    else:
        print(f"   ✓ Success!")
        print(f"   Form Title: {result['title']}")
        print(f"   Form Type: {result['form_type']}")
        print(f"   Questions: {len(result['questions'])}")
        print("\n   Question breakdown:")
        for q in result['questions']:
            print(f"     - {q['question_type']}: {q['question_text'][:50]}")


if __name__ == "__main__":
    asyncio.run(test_oauth_flow())
```

Run it:
```bash
python test_oauth.py
```

### Test Script 2: Test Form Parsing

Create `test_form_parsing.py`:

```python
"""Test Google Forms API client."""
import asyncio
from app.services.google_forms_client import (
    extract_form_id_from_url,
    fetch_form
)
from app.services.oauth_service import get_valid_token

USER_ID = "your-user-uuid"

# Test different URL formats
TEST_URLS = [
    "https://docs.google.com/forms/d/1FAIpQLSe.../edit",
    "https://docs.google.com/forms/d/e/1FAIpQLSe.../viewform",
]


async def test_parsing():
    print("=== Testing URL Parsing ===\n")

    for url in TEST_URLS:
        try:
            form_id = extract_form_id_from_url(url)
            print(f"✓ {url[:50]}...")
            print(f"  Form ID: {form_id}\n")
        except Exception as e:
            print(f"✗ Failed to parse: {e}\n")

    print("\n=== Testing Form Fetch ===\n")

    # Use your actual form URL
    form_url = input("Enter your Google Form URL: ")
    form_id = extract_form_id_from_url(form_url)

    # Get token
    token = await get_valid_token(USER_ID, "google")

    # Fetch form
    result = await fetch_form(form_id, token)

    print(f"\nForm Title: {result['title']}")
    print(f"Total Questions: {len(result['questions'])}\n")

    for i, q in enumerate(result['questions'], 1):
        print(f"Question {i}:")
        print(f"  Type: {q['question_type']}")
        print(f"  Text: {q['question_text']}")
        print(f"  Required: {q['required']}")
        if q['options']:
            print(f"  Options: {', '.join(q['options'][:3])}{'...' if len(q['options']) > 3 else ''}")
        if q['scale_min']:
            print(f"  Scale: {q['scale_min']} to {q['scale_max']}")
        print()


if __name__ == "__main__":
    asyncio.run(test_parsing())
```

---

## Testing via API Endpoints

### Using cURL

```bash
# Save your auth token
TOKEN="your_jwt_token_here"

# 1. Check connections
curl -X GET "http://localhost:8000/auth/connections" \
  -H "Authorization: Bearer $TOKEN"

# 2. Connect Google (if not connected)
curl -X GET "http://localhost:8000/auth/google/connect" \
  -H "Authorization: Bearer $TOKEN"

# 3. Test form fetch (you'll need to create this endpoint)
curl -X POST "http://localhost:8000/api/forms/import" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "form_url": "https://docs.google.com/forms/d/YOUR_FORM_ID/edit"
  }'
```

### Using Postman

1. **Import Collection**: Create new request collection
2. **Set Environment Variables**:
   - `base_url`: `http://localhost:8000`
   - `auth_token`: Your JWT token

3. **Test Requests**:

**Get Auth URL:**
```
GET {{base_url}}/auth/google/connect
Headers:
  Authorization: Bearer {{auth_token}}
```

**Check Connections:**
```
GET {{base_url}}/auth/connections
Headers:
  Authorization: Bearer {{auth_token}}
```

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your-jwt-token"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# Check connections
response = requests.get(f"{BASE_URL}/auth/connections", headers=headers)
print("Connections:", response.json())

# Get Google auth URL
response = requests.get(f"{BASE_URL}/auth/google/connect", headers=headers)
auth_data = response.json()
print(f"Visit this URL: {auth_data['auth_url']}")
```

---

## Common Issues

### Issue 1: "Invalid grant" Error

**Symptom**: Error when exchanging authorization code

**Causes**:
- Authorization code already used (codes are single-use)
- Code expired (10-minute lifetime)
- Wrong redirect URI

**Solution**:
- Get a fresh authorization URL
- Complete OAuth flow again
- Don't refresh the callback page

### Issue 2: "Permission denied" (403)

**Symptom**: Can't fetch form even with OAuth connected

**Causes**:
- Form is private and you don't have access
- OAuth scopes don't include Forms API
- Token doesn't have correct permissions

**Solution**:
```bash
# 1. Check your form is accessible
# Sign in to Google with the same account
# Visit the form URL - can you see it?

# 2. Verify OAuth scopes in .env
# Should include: forms.body.readonly

# 3. Reconnect OAuth with correct scopes
# Disconnect first:
curl -X DELETE "http://localhost:8000/auth/google/disconnect" \
  -H "Authorization: Bearer $TOKEN"

# Then reconnect
```

### Issue 3: "Form not found" (404)

**Symptom**: API returns 404 for form

**Causes**:
- Wrong form ID
- Form was deleted
- URL parsing error

**Solution**:
```python
# Test URL parsing
from app.services.google_forms_client import extract_form_id_from_url

url = "your-form-url"
form_id = extract_form_id_from_url(url)
print(f"Extracted ID: {form_id}")

# Verify form exists - open in browser:
print(f"https://docs.google.com/forms/d/{form_id}/edit")
```

### Issue 4: "Token expired"

**Symptom**: Token expired error when fetching form

**Causes**:
- Access token expired (1-hour lifetime)
- Refresh token missing or invalid

**Solution**:
```python
# System should auto-refresh
# If it doesn't work, manually refresh:

from app.services.oauth_service import refresh_google_token

await refresh_google_token(USER_ID)

# Or reconnect OAuth
```

### Issue 5: Rate Limit Exceeded (429)

**Symptom**: "Rate limit exceeded" error

**Causes**:
- Too many API requests
- Google Forms API quota exceeded

**Solution**:
- Wait 1 minute and try again
- Check quota in Google Cloud Console
- Implement exponential backoff

---

## Debugging Tips

### Enable Debug Logging

```python
# At the top of your test script
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Token Storage

```sql
-- In Supabase SQL Editor
SELECT
    provider,
    expires_at,
    scope,
    created_at
FROM oauth_tokens
WHERE user_id = 'your-user-uuid';
```

### Verify RLS Policies

```sql
-- Check if service role can access tokens
SELECT * FROM oauth_tokens;
-- Should return all tokens (using service_role key)
```

### Test Google Forms API Directly

```bash
# Get your access token
TOKEN="your-access-token"
FORM_ID="your-form-id"

# Test Google Forms API
curl -X GET "https://forms.googleapis.com/v1/forms/$FORM_ID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Success Checklist

- [ ] Google Cloud project set up with Forms API enabled
- [ ] OAuth credentials in `.env`
- [ ] Backend server running
- [ ] User account created in Supabase
- [ ] Google account connected via OAuth
- [ ] `GET /auth/connections` shows `google: true`
- [ ] Can extract form ID from URL
- [ ] Can fetch form successfully
- [ ] Form data parsed correctly (all question types)
- [ ] Token auto-refresh works

---

## Next Steps

After successful testing:

1. **Create Survey Router**: Build endpoint to create surveys from imported forms
2. **Add Error Handling UI**: Show user-friendly messages for OAuth errors
3. **Implement Form Caching**: Cache fetched forms to reduce API calls
4. **Add Response Syncing**: Fetch form responses periodically
5. **Build Frontend UI**: Create form import interface

---

## Additional Resources

- **Google Forms API Docs**: https://developers.google.com/forms/api
- **OAuth 2.0 Playground**: https://developers.google.com/oauthplayground
- **Supabase Auth Docs**: https://supabase.com/docs/guides/auth
- **Project Docs**: See `docs/oauth_setup_guide.md` and `docs/api_usage.md`

---

## Support

If you encounter issues:

1. Check server logs for detailed error messages
2. Verify all environment variables are set correctly
3. Ensure migrations have been run
4. Test OAuth flow in isolation first
5. Check Google Cloud Console for API errors

For persistent issues, review the implementation in:
- `app/services/oauth_service.py`
- `app/services/google_forms_client.py`
- `app/services/form_fetcher.py`
