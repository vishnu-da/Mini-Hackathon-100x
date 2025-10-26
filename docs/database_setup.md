# Database Setup Guide

This guide explains how to set up the Supabase database for the AI Voice Survey Platform.

## Prerequisites

- A Supabase account (free tier works for development)
- Access to your Supabase project dashboard
- Your Supabase URL and API keys

## Table of Contents

1. [Quick Start](#quick-start)
2. [Detailed Setup Instructions](#detailed-setup-instructions)
3. [Database Schema Overview](#database-schema-overview)
4. [Running Migrations](#running-migrations)
5. [Verifying the Setup](#verifying-the-setup)
6. [Row Level Security (RLS)](#row-level-security-rls)
7. [Troubleshooting](#troubleshooting)

## Quick Start

### Option 1: Using Supabase Dashboard (Recommended)

1. Log in to your [Supabase Dashboard](https://app.supabase.com)
2. Select your project (or create a new one)
3. Navigate to **SQL Editor** in the left sidebar
4. Click **New Query**
5. Copy the contents of `/migrations/001_create_schema.sql`
6. Paste into the SQL editor
7. Click **Run** or press `Ctrl+Enter`

### Option 2: Using Supabase CLI

```bash
# Install Supabase CLI (if not already installed)
npm install -g supabase

# Login to Supabase
supabase login

# Link your project
supabase link --project-ref your-project-ref

# Run the migration
supabase db push
```

## Detailed Setup Instructions

### Step 1: Create a Supabase Project

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Click **New Project**
3. Fill in:
   - **Project Name**: AI Voice Survey Platform
   - **Database Password**: Choose a strong password (save this!)
   - **Region**: Select closest to your users
4. Click **Create new project** and wait for provisioning

### Step 2: Get Your Credentials

1. Once the project is ready, go to **Settings** → **API**
2. Copy the following values:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon/public key** (API Key)
   - **service_role key** (for backend operations)

3. Update your `.env` file:

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_anon_key_here
```

### Step 3: Run the Schema Migration

1. In your Supabase Dashboard, navigate to **SQL Editor**
2. Click **New Query**
3. Open `/migrations/001_create_schema.sql` from this project
4. Copy and paste the entire contents
5. Click **Run** (or press `Ctrl+Enter`)
6. Wait for the success message: "Success. No rows returned"

### Step 4: Verify Tables Were Created

1. Navigate to **Table Editor** in the left sidebar
2. You should see the following tables:
   - `users`
   - `voice_agents`
   - `spreadsheet_destinations`
   - `surveys`
   - `contact`
   - `call_logs`

## Database Schema Overview

### Tables Structure

```
┌─────────────────────┐
│       users         │
│  - user_id (PK)     │
│  - email            │
│  - phone_number     │
│  - name             │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────▼──────────┐
│      surveys        │
│  - survey_id (PK)   │◄──────────┐
│  - user_id (FK)     │           │
│  - voice_agent_id   │           │
│  - destination_id   │           │
│  - json_questionnaire│          │
│  - status           │           │
└──────────┬──────────┘           │
           │                      │
           │ 1:N                  │
           │                      │
┌──────────▼──────────┐           │
│      contact        │           │
│  - contact_id (PK)  │           │
│  - survey_id (FK)   │───────────┘
│  - phone_number     │
│  - participant_name │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────▼──────────┐
│     call_logs       │
│  - twilio_call_sid  │
│  - contact_id (FK)  │
│  - recording_url    │
│  - raw_transcript   │
│  - status           │
└─────────────────────┘
```

### Key Features

- **UUID Primary Keys**: All tables use UUIDs for better scalability
- **Foreign Key Constraints**: Maintain referential integrity
- **Timestamps**: Automatic `created_at` and `updated_at` tracking
- **JSONB Columns**: Flexible storage for questionnaires and responses
- **Indexes**: Optimized queries on frequently accessed columns
- **Triggers**: Auto-update `updated_at` timestamps

### Ownership Model

**Direct User Ownership (via user_id column):**
- `users` - Users own their own records
- `surveys` - Each survey belongs to a user
- `oauth_tokens` - Each token belongs to a user

**Indirect Ownership (via relationships):**
- `voice_agents` - No direct user_id. Access controlled through surveys that reference them via RLS
- `spreadsheet_destinations` - No direct user_id. Access controlled through surveys that reference them via RLS
- `contact` - Owned via survey relationship (contact → survey → user)
- `call_logs` - Owned via contact → survey → user relationship

**Important**: `voice_agents` and `spreadsheet_destinations` are shared resources. Multiple surveys can reference the same voice agent or destination. Row Level Security (RLS) ensures users can only access these resources through their own surveys.

## Running Migrations

### Initial Migration

The `/migrations/001_create_schema.sql` file contains:

- ✅ Table creation statements
- ✅ Index creation
- ✅ Foreign key constraints
- ✅ Triggers for automatic timestamps
- ✅ Row Level Security (RLS) policies
- ✅ Table and column comments

### Future Migrations

When adding new migrations:

1. Create a new file: `/migrations/002_your_change.sql`
2. Use sequential numbering
3. Include rollback SQL in comments
4. Test locally first
5. Run in production via Supabase Dashboard

## Verifying the Setup

### 1. Check Tables Exist

Run this query in the SQL Editor:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

You should see all 6 tables listed.

### 2. Check Indexes

```sql
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

### 3. Check Foreign Keys

```sql
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name;
```

### 4. Test Insert Operations

Try creating a test user:

```sql
INSERT INTO users (email, name, phone_number)
VALUES ('test@example.com', 'Test User', '+1234567890')
RETURNING *;
```

## Row Level Security (RLS)

The schema includes RLS policies to secure data access:

### User-Level Policies

- Users can only access their own data
- Users can only manage surveys they created
- Users can only view contacts and call logs for their surveys

### Service Role Bypass

Backend operations using the `service_role` key bypass RLS policies for administrative tasks.

### Checking RLS Status

```sql
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public';
```

All tables should show `rowsecurity = true`.

### Viewing RLS Policies

```sql
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

## Database Access from Python

The `/app/database.py` file provides helper functions for all tables:

### Example Usage

```python
from app.database import create_user, create_survey, get_surveys_by_user

# Create a user
user = await create_user(
    email="user@example.com",
    name="John Doe",
    phone_number="+1234567890"
)

# Create a survey
survey = await create_survey({
    "user_id": user["user_id"],
    "json_questionnaire": {"questions": [...]},
    "status": "draft"
})

# Get all surveys for a user
surveys = await get_surveys_by_user(user["user_id"])
```

## Troubleshooting

### Error: "uuid-ossp extension does not exist"

**Solution**: The migration automatically creates this extension. If it fails:

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### Error: "permission denied for table"

**Solution**: Make sure you're using the correct API key. Use `service_role` key for backend operations.

### Error: "foreign key constraint violation"

**Solution**: Ensure parent records exist before creating child records. For example, create a user before creating a survey.

### RLS Blocking Queries

**Solution**:
- Use the `service_role` key for backend operations
- Or temporarily disable RLS for testing:

```sql
ALTER TABLE table_name DISABLE ROW LEVEL SECURITY;
```

### Migration Already Applied

If you see errors about tables already existing:

```sql
-- Drop all tables (WARNING: This deletes all data!)
DROP TABLE IF EXISTS call_logs CASCADE;
DROP TABLE IF EXISTS contact CASCADE;
DROP TABLE IF EXISTS surveys CASCADE;
DROP TABLE IF EXISTS spreadsheet_destinations CASCADE;
DROP TABLE IF EXISTS voice_agents CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Then re-run the migration
```

## Backup and Recovery

### Creating Backups

Supabase automatically creates daily backups. To create a manual backup:

1. Go to **Settings** → **Database**
2. Scroll to **Database Backups**
3. Click **Create Backup**

### Restoring from Backup

1. Go to **Settings** → **Database**
2. Find your backup in the list
3. Click **Restore**

## Performance Optimization

### Recommended Indexes (Already Included)

- Foreign key columns
- Frequently queried columns (`status`, `email`, `phone_number`)
- Timestamp columns for sorting

### Query Optimization Tips

1. Use `select("specific, columns")` instead of `select("*")`
2. Add `.limit()` to large queries
3. Use pagination with `.range()`
4. Monitor slow queries in Supabase Dashboard

## Next Steps

1. ✅ Set up your `.env` file with Supabase credentials
2. ✅ Run the migration script
3. ✅ Verify all tables are created
4. ✅ Test database connections from your FastAPI app
5. ✅ Create sample data for testing
6. ✅ Set up monitoring and logging

## Support

For issues:
- Check [Supabase Documentation](https://supabase.com/docs)
- Visit [Supabase Discord](https://discord.supabase.com)
- Review migration file: `/migrations/001_create_schema.sql`
- Check database helper functions: `/app/database.py`

## Additional Resources

- [Supabase Python Client Docs](https://supabase.com/docs/reference/python/introduction)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)
