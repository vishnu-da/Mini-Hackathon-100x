# SaaS Backend Architecture Guide

## Overview

Your AI Voice Survey platform now operates as a full Software-as-a-Service (SaaS) backend where **users never interact with Twilio or LiveKit directly**. Everything is handled automatically by the backend.

### Key Features ✨

- ✅ **Automatic phone number provisioning** - Each user gets their own dedicated Twilio number
- ✅ **Dynamic SIP trunk configuration** - Per-user LiveKit trunks created automatically
- ✅ **One-click campaign launch** - Users just click "Start" and calls begin
- ✅ **No manual configuration** - Twilio/LiveKit completely abstracted away
- ✅ **Multi-tenant architecture** - Each user isolated with their own resources

---

## Architecture Diagram

```
User Flow:
┌─────────────────────────────────────────────────────────────────┐
│  USER ACTIONS (What user sees)                                  │
├─────────────────────────────────────────────────────────────────┤
│  1. Login (Google/Microsoft OAuth)                              │
│  2. Add Google Form URL                                         │
│  3. Upload contact list (CSV)                                   │
│  4. Customize voice settings (tone, voice, instructions)        │
│  5. Click "Launch Campaign" →                                   │
│  6. See: "Calling from +1-555-123-4567" ✅                      │
│  7. Monitor: "5/10 calls completed..."                          │
│  8. View results dashboard                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND MAGIC (User never sees this)                           │
├─────────────────────────────────────────────────────────────────┤
│  Step 1: Check if user has phone number                         │
│          ├─ NO  → Buy Twilio number via API                     │
│          └─ YES → Use existing number                           │
│                                                                  │
│  Step 2: Check if user has SIP trunk                            │
│          ├─ NO  → Create LiveKit trunk                          │
│          └─ YES → Use existing trunk                            │
│                                                                  │
│  Step 3: For each contact:                                      │
│          ├─ Dispatch LiveKit agent                              │
│          ├─ Create SIP participant (dial phone)                 │
│          ├─ Conduct voice survey                                │
│          ├─ Store responses (raw + LLM-mapped)                  │
│          └─ End call gracefully                                 │
│                                                                  │
│  Step 4: Mark campaign as completed                             │
│          └─ User sees dashboard with results                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### New Tables

#### `users` (Updated)
```sql
users
├─ user_id (UUID)
├─ email
├─ name
├─ twilio_phone_number (TEXT)        -- NEW: User's dedicated number
├─ phone_number_sid (TEXT)            -- NEW: Twilio SID
├─ phone_provisioned_at (TIMESTAMP)   -- NEW: When number was assigned
└─ livekit_trunk_id (TEXT)            -- NEW: SIP trunk ID
```

#### `surveys` (Updated)
```sql
surveys
├─ survey_id (UUID)
├─ user_id (UUID)
├─ voice_agent_tone (TEXT)            -- NEW: friendly/professional/casual
├─ voice_agent_voice (TEXT)           -- NEW: celeste/orion/phoenix
└─ voice_agent_instructions (TEXT)    -- NEW: Custom LLM instructions
```

#### `phone_numbers` (New)
```sql
phone_numbers
├─ id (UUID)
├─ user_id (UUID)
├─ phone_number (TEXT)
├─ phone_number_sid (TEXT)
├─ provisioned_at (TIMESTAMP)
├─ released_at (TIMESTAMP)
└─ status (active/released/suspended)
```

#### `sip_trunks` (New)
```sql
sip_trunks
├─ id (UUID)
├─ user_id (UUID)
├─ livekit_trunk_id (TEXT)
├─ trunk_name (TEXT)
├─ sip_address (TEXT)
├─ phone_number (TEXT)
└─ last_used_at (TIMESTAMP)
```

---

## API Endpoints

### 1. Launch Campaign
**POST** `/campaigns/launch`

The main endpoint users hit to start calling.

**Request:**
```json
{
  "survey_id": "c87a4652-8e9f-4511-9b65-73a9f78ef401",
  "test_mode": false
}
```

**Response:**
```json
{
  "status": "launching",
  "campaign_id": "c87a4652-8e9f-4511-9b65-73a9f78ef401",
  "phone_number": "+14155551234",
  "total_contacts": 50,
  "estimated_duration_minutes": 150,
  "message": "Survey campaign launched! Calling from +14155551234"
}
```

**What happens behind the scenes:**
1. Checks if user has phone number → provisions if needed
2. Checks if user has SIP trunk → creates if needed
3. Fetches survey settings (voice tone, instructions)
4. Gets all contacts for the survey
5. Starts background task to call all contacts
6. Returns phone number to display to user

---

### 2. Get Campaign Status
**GET** `/campaigns/{survey_id}/status`

Real-time campaign statistics.

**Response:**
```json
{
  "campaign_id": "c87a4652-8e9f-4511-9b65-73a9f78ef401",
  "status": "in_progress",
  "phone_number": "+14155551234",
  "total_contacts": 50,
  "completed_calls": 12,
  "in_progress_calls": 3,
  "failed_calls": 1,
  "pending_calls": 34,
  "completion_percentage": 24.0
}
```

**Use case:** Frontend polls this endpoint every 10 seconds to update dashboard.

---

### 3. Get Phone Number Info
**GET** `/campaigns/phone-number`

Check if user has a phone number provisioned.

**Response:**
```json
{
  "phone_number": "+14155551234",
  "status": "provisioned",
  "provisioned_at": "2025-10-23T10:30:00Z",
  "trunk_id": "ST_d3TZzQoeU3Kv"
}
```

---

### 4. Manually Provision Number
**POST** `/campaigns/provision-number`

Pre-provision a number before launching campaign (optional).

**Response:**
```json
{
  "status": "provisioned",
  "phone_number": "+14155551234",
  "message": "Phone number successfully provisioned"
}
```

---

## How It Works: Step by Step

### Scenario: User launches their first campaign

**User Action:** Clicks "Launch Campaign" button

**Backend Flow:**

#### Step 1: Phone Number Provisioning (app/services/phone_provisioning.py)

```python
# Check if user has number
user = db.table("users").select("twilio_phone_number").eq("user_id", user_id)

if not user.data[0].get("twilio_phone_number"):
    # No number → Buy one from Twilio
    client = Client(twilio_account_sid, twilio_auth_token)
    available = client.available_phone_numbers("US").local.list(limit=10)

    purchased = client.incoming_phone_numbers.create(
        phone_number=available[0].phone_number,
        voice_url="https://yourbackend.com/webhooks/voice"
    )

    # Store in database
    db.table("users").update({
        "twilio_phone_number": purchased.phone_number,
        "phone_number_sid": purchased.sid
    }).eq("user_id", user_id)
```

**Cost:** ~$1.15/month per number

---

#### Step 2: SIP Trunk Creation (app/services/sip_trunk_provisioning.py)

```python
# Create LiveKit SIP trunk for this user
lk_api = api.LiveKitAPI(livekit_url, api_key, api_secret)

trunk = await lk_api.sip.create_sip_outbound_trunk(
    name=f"user-{user_id[:8]}-trunk",
    address="reso.pstn.twilio.com",
    numbers=[phone_number],
    auth_username=twilio_account_sid,
    auth_password=twilio_auth_token
)

# Store trunk ID
db.table("users").update({
    "livekit_trunk_id": trunk.sip_trunk_id
}).eq("user_id", user_id)
```

---

#### Step 3: Campaign Execution (app/routers/campaigns.py)

```python
# Get contacts
contacts = db.table("contact").select("*").eq("survey_id", survey_id)

# For each contact, initiate call
for contact in contacts:
    await initiate_outbound_call(
        to_phone=contact["phone_number"],
        survey_id=survey_id,
        contact_id=contact["contact_id"],
        trunk_id=user_trunk_id  # Use user's dedicated trunk
    )
```

---

#### Step 4: Call Execution (app/services/livekit_outbound.py → livekit_entrypoint.py)

```python
# Dispatch agent with metadata
metadata = {
    "survey_id": survey_id,
    "contact_id": contact_id,
    "phone_number": "+19877186205",
    "trunk_id": "ST_abc123",  # User's trunk
    "call_type": "outbound"
}

dispatch = await lk_api.agent_dispatch.create_dispatch(
    room=f"survey-{call_sid}",
    agent_name="survey-voice-agent",
    metadata=json.dumps(metadata)
)

# Worker receives job, creates SIP participant
sip_call = await lk_api.sip.create_sip_participant(
    sip_trunk_id=metadata["trunk_id"],  # User's trunk!
    sip_call_to=metadata["phone_number"],
    room_name=room_name
)

# Agent conducts survey, stores responses
```

---

## Cost Breakdown Per User

### One-Time Costs (Per User)
| Item | Cost | When |
|------|------|------|
| Twilio Phone Number | $1.15/month | On first campaign |
| LiveKit SIP Trunk | Free | On first campaign |

### Usage Costs (Per Call)
| Item | Cost | Formula |
|------|------|---------|
| Twilio Outbound Call | $0.013/min | $0.013 × call_duration |
| Deepgram STT | $0.0043/min | $0.0043 × call_duration |
| OpenAI GPT-4o-mini | ~$0.10/survey | Varies by length |
| Rime TTS | Free via LiveKit | $0 |
| **Total per 3-min call** | **~$0.15** | Very affordable! |

### Example: 1000 Users, 10 Surveys Each

**Monthly Fixed Costs:**
- 1000 numbers × $1.15 = $1,150/month

**Variable Costs (10 surveys × 3 mins each):**
- 1000 users × 10 surveys × $0.15 = $1,500/month

**Total: ~$2,650/month for 10,000 surveys**

**Revenue (if you charge $0.50/survey):**
- 10,000 surveys × $0.50 = $5,000/month

**Profit: $2,350/month (47% margin)** 💰

---

## Setup Instructions

### 1. Run Database Migration

```bash
# Apply schema changes
psql -U postgres -d your_database -f database_migrations/001_per_user_phone_numbers.sql
```

Or in Supabase dashboard:
1. Go to SQL Editor
2. Paste contents of `database_migrations/001_per_user_phone_numbers.sql`
3. Click "Run"

### 2. Update Environment Variables

No new variables needed! Existing Twilio credentials are reused.

### 3. Restart Backend

```bash
# Kill existing server
# Restart
python -m app.main

# Or with uvicorn
uvicorn app.main:app --reload
```

### 4. Restart LiveKit Worker

```bash
python -m app.services.livekit_entrypoint
```

---

## Testing the SaaS Backend

### Test Flow

1. **Login as User**
   ```bash
   POST /auth/google/callback
   # Or use existing auth
   ```

2. **Create Survey**
   ```bash
   POST /surveys
   {
     "title": "Test Survey",
     "json_questionnaire": {...},
     "voice_agent_tone": "friendly",
     "voice_agent_voice": "celeste"
   }
   ```

3. **Add Contacts**
   ```bash
   POST /surveys/{survey_id}/contacts
   {
     "contacts": [
       {"participant_name": "John", "phone_number": "+19877186205"}
     ]
   }
   ```

4. **Launch Campaign**
   ```bash
   POST /campaigns/launch
   {
     "survey_id": "...",
     "test_mode": true  # Only calls first contact
   }
   ```

5. **Check Status**
   ```bash
   GET /campaigns/{survey_id}/status
   ```

6. **View Results**
   ```bash
   GET /surveys/{survey_id}/responses
   ```

---

## Frontend Integration

### Example React Component

```jsx
function CampaignDashboard({ surveyId }) {
  const [status, setStatus] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState(null);

  // Launch campaign
  const launchCampaign = async () => {
    const response = await fetch('/campaigns/launch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ survey_id: surveyId, test_mode: false })
    });

    const data = await response.json();
    setPhoneNumber(data.phone_number);

    // Start polling for status
    pollStatus();
  };

  // Poll status every 10 seconds
  const pollStatus = () => {
    const interval = setInterval(async () => {
      const response = await fetch(`/campaigns/${surveyId}/status`);
      const data = await response.json();
      setStatus(data);

      // Stop polling when completed
      if (data.status === 'completed') {
        clearInterval(interval);
      }
    }, 10000);
  };

  return (
    <div>
      <h1>Campaign Dashboard</h1>

      {!phoneNumber && (
        <button onClick={launchCampaign}>
          🚀 Launch Campaign
        </button>
      )}

      {phoneNumber && (
        <div>
          <p>📞 Calling from: <strong>{phoneNumber}</strong></p>

          {status && (
            <div>
              <h2>Status: {status.status}</h2>
              <p>✅ Completed: {status.completed_calls}/{status.total_contacts}</p>
              <p>⏳ In Progress: {status.in_progress_calls}</p>
              <p>❌ Failed: {status.failed_calls}</p>
              <p>📊 Progress: {status.completion_percentage}%</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## Troubleshooting

### Issue: "No phone numbers available"

**Cause:** Twilio account doesn't have numbers in your region.

**Fix:**
```python
# In phone_provisioning.py, change country code
available = client.available_phone_numbers("GB").local.list()  # UK
available = client.available_phone_numbers("CA").local.list()  # Canada
```

---

### Issue: "Failed to create SIP trunk"

**Cause:** LiveKit credentials incorrect or insufficient permissions.

**Fix:**
1. Check `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` in `.env`
2. Verify LiveKit project has SIP enabled
3. Check trunk limits in LiveKit dashboard

---

### Issue: User sees "Not provisioned" for phone number

**Cause:** Phone provisioning failed silently.

**Fix:**
1. Check logs: `Failed to provision phone number`
2. Verify Twilio account balance
3. Manually provision: `POST /campaigns/provision-number`

---

## Security Considerations

### 1. Phone Number Isolation

Each user's phone number is completely isolated:
- ✅ User A cannot use User B's number
- ✅ Trunks are per-user, not shared
- ✅ Database enforces user_id foreign keys

### 2. SIP Trunk Security

- ✅ Auth credentials stored per-user
- ✅ Twilio authenticates every call
- ✅ LiveKit validates trunk ownership

### 3. API Access Control

- ✅ All endpoints require authentication (`get_current_user`)
- ✅ Survey ownership verified before campaign launch
- ✅ Users can only see their own campaigns

---

## Next Steps

### Phase 1: ✅ COMPLETE
- [x] Phone number provisioning
- [x] SIP trunk creation
- [x] Campaign launch endpoint
- [x] Per-user configuration
- [x] Database schema

### Phase 2: Recommended Enhancements

1. **Phone Number Management UI**
   - View current number
   - Release/change number
   - Number history

2. **Billing Integration**
   - Track usage per user
   - Calculate costs
   - Stripe/payment integration

3. **Advanced Features**
   - Call recording storage
   - Real-time call monitoring
   - Advanced analytics dashboard

4. **Webhooks**
   - Campaign completion webhooks
   - Call status webhooks
   - Real-time notifications

---

## Summary

You now have a **fully functional SaaS backend** where:

✅ Users get dedicated phone numbers automatically
✅ No manual Twilio/LiveKit configuration
✅ One-click campaign launches
✅ Multi-tenant isolation
✅ Scalable architecture
✅ Professional grade

**Ready to go live!** 🚀
