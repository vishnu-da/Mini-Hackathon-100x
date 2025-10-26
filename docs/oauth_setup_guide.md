# OAuth Setup Guide

Complete guide for configuring Google and Microsoft OAuth credentials for the AI Voice Survey Platform.

## Table of Contents

1. [Google OAuth Setup](#google-oauth-setup)
2. [Microsoft OAuth Setup](#microsoft-oauth-setup)
3. [Environment Configuration](#environment-configuration)
4. [Testing OAuth Flow](#testing-oauth-flow)
5. [Troubleshooting](#troubleshooting)

---

## Google OAuth Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Enter project name: "AI Voice Survey Platform"
4. Click **Create**

### Step 2: Enable Google Forms API

1. In your project, go to **APIs & Services** → **Library**
2. Search for "Google Forms API"
3. Click on **Google Forms API**
4. Click **Enable**

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** (or **Internal** if using Google Workspace)
3. Click **Create**

4. Fill in App Information:
   - **App name**: AI Voice Survey Platform
   - **User support email**: your-email@example.com
   - **Developer contact email**: your-email@example.com

5. Click **Save and Continue**

6. **Scopes**: Click **Add or Remove Scopes**
   - Add these scopes:
     - `https://www.googleapis.com/auth/forms.body.readonly`
     - `https://www.googleapis.com/auth/forms.responses.readonly`
   - Click **Update**
   - Click **Save and Continue**

7. **Test users** (for External apps):
   - Click **Add Users**
   - Add your email and test user emails
   - Click **Save and Continue**

8. Review and click **Back to Dashboard**

### Step 4: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Web application**
4. Name: "AI Voice Survey OAuth Client"

5. **Authorized redirect URIs**:
   - Click **Add URI**
   - Development: `http://localhost:8000/auth/google/callback`
   - Production: `https://yourdomain.com/auth/google/callback`

6. Click **Create**

7. **Copy your credentials**:
   - **Client ID**: `xxxxx.apps.googleusercontent.com`
   - **Client Secret**: `GOCSPX-xxxxx`

8. Save these for your `.env` file

### Step 5: Publish App (Optional)

For production use:
1. Go to **OAuth consent screen**
2. Click **Publish App**
3. Confirm publishing

**Note**: Unpublished apps have a 100-user limit and show an "unverified app" warning.

---

## Microsoft OAuth Setup

### Step 1: Azure Portal Access

1. Go to [Azure Portal](https://portal.azure.com/)
2. Sign in with your Microsoft account
3. If you don't have an Azure subscription, create a free account

### Step 2: Register Application

1. Search for **Azure Active Directory** (or **Microsoft Entra ID**)
2. Click **App registrations** in the left menu
3. Click **New registration**

4. Fill in details:
   - **Name**: AI Voice Survey Platform
   - **Supported account types**:
     - Select "Accounts in any organizational directory and personal Microsoft accounts"
   - **Redirect URI**:
     - Platform: **Web**
     - URI: `http://localhost:8000/auth/microsoft/callback`

5. Click **Register**

### Step 3: Configure Authentication

1. In your app registration, go to **Authentication**

2. Under **Redirect URIs**, click **Add URI**:
   - Add production URL: `https://yourdomain.com/auth/microsoft/callback`

3. **Front-channel logout URL**: Leave blank

4. **Implicit grant and hybrid flows**:
   - Keep all unchecked (we use authorization code flow)

5. **Allow public client flows**: No

6. Click **Save**

### Step 4: Create Client Secret

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Description: "OAuth Client Secret"
4. Expires: **24 months** (or custom)
5. Click **Add**

6. **Copy the secret value immediately** (you won't see it again!)
   - Example: `abc123~XXXXXXXXXXXXXXXXXXXXXXXXXXXX`

### Step 5: Configure API Permissions

1. Go to **API permissions**
2. Click **Add a permission**

3. Select **Microsoft Graph**

4. Select **Delegated permissions**

5. Search and add:
   - **User.Read** (should already be there)
   - **Forms.Read** or **Forms.Read.All**

6. Click **Add permissions**

7. **Admin Consent** (if required):
   - If you see "Admin consent required"
   - Click **Grant admin consent for [Your Organization]**
   - Click **Yes**

### Step 6: Get Application IDs

1. Go to **Overview**
2. Copy these values:
   - **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
   - **Directory (tenant) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (optional)

---

## Environment Configuration

### Step 1: Create .env File

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### Step 2: Add OAuth Credentials

Edit `.env` and add your credentials:

```env
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-your_google_client_secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Microsoft OAuth Configuration
MICROSOFT_OAUTH_CLIENT_ID=your_microsoft_client_id
MICROSOFT_OAUTH_CLIENT_SECRET=your_microsoft_client_secret
MICROSOFT_OAUTH_REDIRECT_URI=http://localhost:8000/auth/microsoft/callback

# OAuth Scopes (default - don't change unless needed)
GOOGLE_FORMS_SCOPE=https://www.googleapis.com/auth/forms.body.readonly https://www.googleapis.com/auth/forms.responses.readonly
MICROSOFT_FORMS_SCOPE=Forms.Read.All User.Read
```

### Step 3: Update Production URLs

For production deployment, update:

```env
GOOGLE_OAUTH_REDIRECT_URI=https://yourdomain.com/auth/google/callback
MICROSOFT_OAUTH_REDIRECT_URI=https://yourdomain.com/auth/microsoft/callback
CALLBACK_BASE_URL=https://yourdomain.com
```

And update the redirect URIs in:
- Google Cloud Console → Credentials
- Azure Portal → App Registration → Authentication

---

## Testing OAuth Flow

### 1. Start the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
# (Run SQL in Supabase Dashboard)

# Start server
python app/main.py
```

Server should start at `http://localhost:8000`

### 2. Test Google OAuth

**Option A: Using API Docs**

1. Open `http://localhost:8000/docs`
2. Find **OAuth** section
3. Expand `GET /auth/google/connect`
4. Click **Try it out** → **Execute**
5. Copy the `auth_url` from the response
6. Open the URL in a browser
7. Sign in with Google and authorize
8. You should be redirected to `/oauth/success?provider=google`

**Option B: Using cURL**

```bash
# Get auth URL
curl -X GET "http://localhost:8000/auth/google/connect" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Visit the returned auth_url in a browser
```

### 3. Test Microsoft OAuth

Same process but use `/auth/microsoft/connect`

### 4. Verify Connections

```bash
curl -X GET "http://localhost:8000/auth/connections" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Should return:
# {
#   "google": true,
#   "microsoft": false
# }
```

### 5. Test Form Fetching

After connecting Google account:

```python
from app.services.form_fetcher import fetch_form

# Fetch a Google Form
result = await fetch_form(
    user_id="your-user-uuid",
    form_url="https://docs.google.com/forms/d/YOUR_FORM_ID/edit"
)

print(result)
```

---

## Troubleshooting

### Google OAuth Errors

#### "Error 400: redirect_uri_mismatch"

**Cause**: Redirect URI doesn't match the one configured in Google Cloud Console

**Solution**:
1. Check exact URI in console (including http vs https, trailing slashes)
2. Update Google Cloud Console: APIs & Services → Credentials → Edit OAuth client
3. Add both development and production URIs

#### "Access blocked: This app's request is invalid"

**Cause**: OAuth consent screen not configured or app not published

**Solution**:
1. Configure OAuth consent screen completely
2. Add test users (for external apps)
3. Or publish the app

#### "Invalid grant" when exchanging code

**Cause**: Authorization code already used or expired

**Solution**:
- Authorization codes are single-use
- Generate a new auth URL and try again
- Codes expire after 10 minutes

### Microsoft OAuth Errors

#### "AADSTS50011: The redirect URI specified in the request does not match"

**Cause**: Redirect URI mismatch

**Solution**:
1. Azure Portal → App registrations → Your app → Authentication
2. Add exact redirect URI (case-sensitive)
3. Save changes

#### "AADSTS65001: The user or administrator has not consented"

**Cause**: Missing permissions or admin consent not granted

**Solution**:
1. Azure Portal → API permissions
2. Click "Grant admin consent"
3. Or ensure user has permissions to consent

#### "invalid_client" error

**Cause**: Wrong client ID or client secret

**Solution**:
1. Verify `MICROSOFT_OAUTH_CLIENT_ID` in `.env`
2. Create new client secret if needed (old one may have expired)
3. Update `.env` with new secret

### General OAuth Issues

#### State parameter validation fails

**Cause**: State token expired or not found

**Solution**:
- State tokens are stored in memory (lost on server restart)
- For production, use Redis or database for state storage
- Try the OAuth flow again

#### Tokens not being saved

**Cause**: Database error or RLS policy blocking

**Solution**:
1. Check Supabase logs
2. Verify migration ran successfully
3. Ensure using service_role key in backend
4. Check RLS policies allow service_role access

#### "Token expired" errors

**Cause**: Access token expired and refresh failed

**Solution**:
- System should auto-refresh tokens
- If refresh token is missing, user needs to re-authorize
- Check logs for specific error

---

## Security Best Practices

### Production Checklist

- [ ] Use HTTPS for all redirect URIs
- [ ] Store client secrets in environment variables (never in code)
- [ ] Use strong encryption key for token storage
- [ ] Implement rate limiting on OAuth endpoints
- [ ] Add PKCE to OAuth flow
- [ ] Validate state parameter properly
- [ ] Set appropriate token expiration times
- [ ] Monitor OAuth errors and failed attempts
- [ ] Rotate client secrets periodically
- [ ] Implement proper logging (without logging tokens)

### OAuth State Management

For production, replace in-memory storage with Redis:

```python
# app/routers/auth.py
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Store state
redis_client.setex(f"oauth_state:{state}", 600, user_id)  # 10 min TTL

# Validate state
user_id = redis_client.get(f"oauth_state:{state}")
redis_client.delete(f"oauth_state:{state}")
```

---

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Forms API Reference](https://developers.google.com/forms/api)
- [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [Microsoft Graph API - Forms](https://docs.microsoft.com/en-us/graph/api/resources/form)

---

## Support

If you encounter issues:

1. Check Supabase logs for database errors
2. Check backend logs for OAuth errors
3. Verify all redirect URIs match exactly
4. Ensure all API permissions are granted
5. Test with a fresh OAuth flow (new state token)

For persistent issues, check the application logs and Supabase dashboard for detailed error messages.
