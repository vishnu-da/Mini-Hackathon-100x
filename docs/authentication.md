# Authentication Setup Guide

This guide explains how to set up and use Supabase Authentication with the AI Voice Survey Platform.

## Table of Contents

1. [Overview](#overview)
2. [Supabase Auth Setup](#supabase-auth-setup)
3. [Row Level Security (RLS)](#row-level-security-rls)
4. [Authentication Flow](#authentication-flow)
5. [Backend Integration](#backend-integration)
6. [Testing Authentication](#testing-authentication)
7. [Troubleshooting](#troubleshooting)

## Overview

The AI Voice Survey Platform uses Supabase Authentication combined with Row Level Security (RLS) to ensure:

- ✅ Users can only access their own data
- ✅ Backend operations use service role for full access
- ✅ No anonymous access allowed
- ✅ Secure multi-tenant data isolation

### Authentication Architecture

```
┌─────────────┐
│   Client    │
│ (Frontend)  │
└──────┬──────┘
       │
       │ JWT Token (anon key)
       │
┌──────▼──────┐
│   Supabase  │
│    Auth     │
└──────┬──────┘
       │
       │ auth.uid()
       │
┌──────▼──────┐
│  RLS        │──► Only user's own data
│  Policies   │
└─────────────┘

┌─────────────┐
│   Backend   │
│  (FastAPI)  │
└──────┬──────┘
       │
       │ Service Role Key
       │
┌──────▼──────┐
│  Supabase   │──► Full database access
│     DB      │    (bypasses RLS)
└─────────────┘
```

## Supabase Auth Setup

### Step 1: Enable Authentication

1. Log in to your [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Navigate to **Authentication** in the left sidebar
4. Authentication is enabled by default

### Step 2: Configure Auth Providers

#### Email/Password Authentication (Recommended for MVP)

1. Go to **Authentication** → **Providers**
2. **Email** provider is enabled by default
3. Configure email templates:
   - Go to **Authentication** → **Email Templates**
   - Customize confirmation, reset password, and magic link emails

#### Additional Providers (Optional)

- **Google OAuth**: Enable for Google sign-in
- **GitHub OAuth**: Enable for GitHub sign-in
- **Magic Link**: Passwordless email authentication

### Step 3: Configure Auth Settings

1. Go to **Authentication** → **Settings**
2. Configure the following:

```
Site URL: http://localhost:3000 (development)
         https://yourdomain.com (production)

Redirect URLs:
  - http://localhost:3000/**
  - https://yourdomain.com/**

JWT Expiry: 3600 (1 hour, default)

Enable Email Confirmations: Yes (recommended)
Enable Email Change Confirmations: Yes
```

### Step 4: Get Authentication Keys

1. Go to **Settings** → **API**
2. Copy the following:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: For client-side auth
   - **service_role key**: For backend operations (keep secret!)

3. Update your `.env`:

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_service_role_key_here  # Backend uses service role
SUPABASE_ANON_KEY=your_anon_key_here     # Frontend uses anon key
```

## Row Level Security (RLS)

### What is RLS?

Row Level Security ensures that users can only access rows they own. The `auth.uid()` function returns the authenticated user's UUID.

### RLS Policies Summary

All tables have RLS enabled with the following policy structure:

#### 1. Users Table
- **SELECT**: Users can read their own record (`auth.uid() = user_id`)
- **UPDATE**: Users can update their own record
- **Service Role**: Full access (bypass)

#### 2. Voice Agents Table
- **Full CRUD**: Users can manage only their own voice agents (`auth.uid() = user_id`)
- **Service Role**: Full access (bypass)

#### 3. Spreadsheet Destinations Table
- **Full CRUD**: Users can manage only their own destinations (`auth.uid() = user_id`)
- **Service Role**: Full access (bypass)

#### 4. Surveys Table
- **Full CRUD**: Users can manage only their own surveys (`auth.uid() = user_id`)
- **Service Role**: Full access (bypass)

#### 5. Contact Table
- **Full CRUD**: Users can manage contacts for surveys they own
- Access via: `survey_id IN (SELECT survey_id FROM surveys WHERE auth.uid() = user_id)`
- **Service Role**: Full access (bypass)

#### 6. Call Logs Table
- **SELECT/INSERT/UPDATE**: Users can access call logs for their contacts/surveys
- Access via nested query through contact → surveys
- **Service Role**: Full access (bypass)

### Viewing RLS Policies

Run this in Supabase SQL Editor:

```sql
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    cmd,
    qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

## Authentication Flow

### User Registration Flow

```
1. User signs up with email/password
   ↓
2. Supabase Auth creates auth.users record
   ↓
3. Create corresponding record in public.users table
   ↓
4. User receives confirmation email
   ↓
5. User confirms email and can log in
```

### User Login Flow

```
1. User submits credentials
   ↓
2. Supabase Auth validates credentials
   ↓
3. Returns JWT token with user_id
   ↓
4. Client includes JWT in subsequent requests
   ↓
5. RLS policies check auth.uid() against user_id
```

### Backend Service Flow

```
1. Backend uses service_role key
   ↓
2. Service role bypasses all RLS policies
   ↓
3. Full database access for automated operations
```

## Backend Integration

### Using Service Role in FastAPI

The backend should use the **service_role** key to bypass RLS:

```python
# In app/config.py
class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str  # This should be service_role key

# In app/database.py
supabase: Client = create_client(
    supabase_url=settings.supabase_url,
    supabase_key=settings.supabase_key  # service_role key
)
```

### Authentication Middleware

Use the helper functions in `app/auth.py`:

```python
from app.auth import get_current_user, verify_user_access
from fastapi import Depends

@router.get("/surveys")
async def get_surveys(user_id: str = Depends(get_current_user)):
    # user_id is automatically extracted from JWT
    surveys = await get_surveys_by_user(user_id)
    return surveys

@router.get("/surveys/{survey_id}")
async def get_survey(
    survey_id: str,
    user_id: str = Depends(get_current_user)
):
    # Verify user owns this survey
    await verify_user_access(user_id, survey_id, "surveys")
    survey = await get_survey_by_id(survey_id)
    return survey
```

### Creating Users on Signup

When a user signs up via Supabase Auth, create a corresponding user record:

```python
from app.database import create_user

async def on_user_signup(email: str, auth_user_id: str):
    """Called after Supabase Auth creates a user."""
    await create_user(
        user_id=auth_user_id,  # Use same UUID from auth.users
        email=email
    )
```

## Testing Authentication

### 1. Create Test User via Supabase Dashboard

1. Go to **Authentication** → **Users**
2. Click **Add User**
3. Enter email and password
4. Note the User UID

### 2. Create User Record in Database

```sql
INSERT INTO users (user_id, email, name)
VALUES (
    'the-user-uid-from-auth',
    'test@example.com',
    'Test User'
);
```

### 3. Test RLS with SQL

```sql
-- Set the authenticated user context
SET request.jwt.claims.sub = 'the-user-uid-from-auth';

-- This should return only the user's own surveys
SELECT * FROM surveys;

-- This should fail if trying to access another user's data
SELECT * FROM surveys WHERE user_id != 'the-user-uid-from-auth';
```

### 4. Test from Python

```python
from supabase import create_client

# Using anon key (simulates client)
supabase_client = create_client(
    supabase_url="your_url",
    supabase_key="your_anon_key"
)

# Sign in
auth_response = supabase_client.auth.sign_in_with_password({
    "email": "test@example.com",
    "password": "password123"
})

# Query with authentication
response = supabase_client.table("surveys").select("*").execute()
# Should only return user's own surveys
```

## Frontend Integration

### Example: React/Next.js

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)

// Sign up
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password123'
})

// Sign in
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password123'
})

// Get current user
const { data: { user } } = await supabase.auth.getUser()

// Query with RLS (automatically filtered)
const { data, error } = await supabase
  .from('surveys')
  .select('*')
// RLS ensures only user's surveys are returned

// Sign out
await supabase.auth.signOut()
```

## Security Best Practices

### 1. Key Management

- ✅ **Never expose service_role key to clients**
- ✅ Use anon key for frontend/client applications
- ✅ Use service_role key only in backend servers
- ✅ Store keys in environment variables, never in code
- ✅ Rotate keys periodically

### 2. RLS Policies

- ✅ Always enable RLS on tables containing user data
- ✅ Test policies thoroughly before production
- ✅ Use `auth.uid()` for user ownership checks
- ✅ Create service role bypass policies for backend

### 3. JWT Tokens

- ✅ Set appropriate JWT expiry times
- ✅ Implement token refresh logic in clients
- ✅ Validate tokens on every request
- ✅ Handle token expiration gracefully

### 4. Password Security

- ✅ Enforce minimum password length (8+ characters)
- ✅ Enable email confirmation
- ✅ Implement rate limiting on auth endpoints
- ✅ Use HTTPS in production

## Troubleshooting

### Error: "new row violates row-level security policy"

**Cause**: RLS policy is blocking the operation

**Solutions**:
1. Verify user is authenticated: Check `auth.uid()` is not null
2. Verify user owns the resource: Check `user_id = auth.uid()`
3. Use service role key for backend operations
4. Check policy logic is correct

```sql
-- Verify current user
SELECT auth.uid();

-- Temporarily disable RLS for testing (DEV ONLY!)
ALTER TABLE table_name DISABLE ROW LEVEL SECURITY;
```

### Error: "JWT expired"

**Cause**: Authentication token has expired

**Solution**:
```python
# Refresh the session
response = supabase.auth.refresh_session()
```

### Error: "auth.uid() returns null"

**Cause**: No authenticated user in context

**Solutions**:
1. Verify user is logged in
2. Check JWT token is being sent in request headers
3. For backend, use service_role key (bypasses auth.uid())

### Error: "Invalid API key"

**Cause**: Wrong API key being used

**Solutions**:
1. Check you're using correct key (anon vs service_role)
2. Verify key is copied correctly from Supabase dashboard
3. Check environment variables are loaded

### Testing RLS in SQL Editor

The SQL Editor uses the service role, so RLS is bypassed by default. To test RLS:

```sql
-- Create a test function that runs as the authenticated user
CREATE OR REPLACE FUNCTION test_rls_as_user(test_user_id UUID)
RETURNS TABLE(result JSONB)
SECURITY INVOKER  -- Important!
AS $$
BEGIN
  RETURN QUERY
  SELECT row_to_json(s.*)::JSONB
  FROM surveys s
  WHERE s.user_id = test_user_id;
END;
$$ LANGUAGE plpgsql;

-- Test it
SELECT * FROM test_rls_as_user('user-uuid-here');
```

## Additional Resources

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [Supabase Python Client](https://supabase.com/docs/reference/python/auth-signup)
- [JWT Tokens Explained](https://supabase.com/docs/guides/auth/jwts)

## Next Steps

1. ✅ Enable Supabase Authentication
2. ✅ Run migration with RLS policies
3. ✅ Create test users
4. ✅ Test RLS policies
5. ✅ Implement auth middleware in FastAPI
6. ✅ Add authentication to frontend
7. ✅ Test end-to-end authentication flow
