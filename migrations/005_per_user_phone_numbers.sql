-- Migration: Per-User Phone Numbers and SIP Configuration
-- Date: 2025-10-23
-- Description: Add columns to support dedicated phone numbers per user

-- ============================================
-- 1. Update users table
-- ============================================

-- Add phone number fields to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS twilio_phone_number TEXT,
ADD COLUMN IF NOT EXISTS phone_number_sid TEXT,
ADD COLUMN IF NOT EXISTS phone_provisioned_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS livekit_trunk_id TEXT;

-- Add indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_phone_number
ON users(twilio_phone_number);

CREATE INDEX IF NOT EXISTS idx_users_phone_sid
ON users(phone_number_sid);

-- ============================================
-- 2. Update surveys table
-- ============================================

-- Add voice customization fields
ALTER TABLE surveys
ADD COLUMN IF NOT EXISTS voice_agent_tone TEXT DEFAULT 'friendly',
ADD COLUMN IF NOT EXISTS voice_agent_voice TEXT DEFAULT 'celeste',
ADD COLUMN IF NOT EXISTS voice_agent_instructions TEXT;

-- Add comments for clarity
COMMENT ON COLUMN surveys.voice_agent_tone IS 'Voice agent personality: friendly, professional, casual, enthusiastic';
COMMENT ON COLUMN surveys.voice_agent_voice IS 'Rime voice ID: celeste, orion, phoenix, nova, andromeda, zenith';
COMMENT ON COLUMN surveys.voice_agent_instructions IS 'Custom instructions for the voice agent';

-- ============================================
-- 3. Create phone_numbers table (optional)
-- ============================================
-- Track all provisioned numbers and their history

CREATE TABLE IF NOT EXISTS phone_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL UNIQUE,
    phone_number_sid TEXT NOT NULL UNIQUE,
    twilio_account_sid TEXT,
    provisioned_at TIMESTAMP DEFAULT NOW(),
    released_at TIMESTAMP,
    status TEXT DEFAULT 'active', -- active, released, suspended
    country_code TEXT DEFAULT 'US',
    monthly_cost DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_phone_numbers_user_id ON phone_numbers(user_id);
CREATE INDEX IF NOT EXISTS idx_phone_numbers_status ON phone_numbers(status);

-- ============================================
-- 4. Create sip_trunks table
-- ============================================
-- Track LiveKit SIP trunks for each user

CREATE TABLE IF NOT EXISTS sip_trunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    livekit_trunk_id TEXT NOT NULL UNIQUE,
    trunk_name TEXT,
    sip_address TEXT, -- e.g., reso.pstn.twilio.com
    phone_number TEXT,
    auth_username TEXT,
    auth_password_encrypted TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sip_trunks_user_id ON sip_trunks(user_id);
CREATE INDEX IF NOT EXISTS idx_sip_trunks_livekit_id ON sip_trunks(livekit_trunk_id);

-- ============================================
-- 5. Update existing data (if needed)
-- ============================================

-- Set default voice settings for existing surveys
UPDATE surveys
SET
    voice_agent_tone = 'friendly',
    voice_agent_voice = 'celeste'
WHERE
    voice_agent_tone IS NULL
    OR voice_agent_voice IS NULL;

-- ============================================
-- 6. Add constraints
-- ============================================

-- Ensure phone numbers are in E.164 format
ALTER TABLE users
ADD CONSTRAINT check_phone_e164
CHECK (twilio_phone_number IS NULL OR twilio_phone_number ~ '^\+[1-9]\d{1,14}$');

-- ============================================
-- 7. Create helper function
-- ============================================

-- Function to get user's active phone number
CREATE OR REPLACE FUNCTION get_user_phone_number(p_user_id UUID)
RETURNS TEXT AS $$
BEGIN
    RETURN (
        SELECT twilio_phone_number
        FROM users
        WHERE user_id = p_user_id
        AND twilio_phone_number IS NOT NULL
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 8. Comments
-- ============================================

COMMENT ON TABLE phone_numbers IS 'Track all Twilio phone numbers provisioned for users';
COMMENT ON TABLE sip_trunks IS 'Track LiveKit SIP trunks for outbound calling';
COMMENT ON COLUMN users.twilio_phone_number IS 'User''s dedicated Twilio phone number in E.164 format';
COMMENT ON COLUMN users.phone_number_sid IS 'Twilio phone number SID for API operations';
COMMENT ON COLUMN users.livekit_trunk_id IS 'LiveKit SIP trunk ID for outbound calls';
