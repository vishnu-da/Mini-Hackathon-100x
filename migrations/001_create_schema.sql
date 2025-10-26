-- AI Voice Survey Platform - Database Schema Migration
-- Version: 001
-- Description: Initial schema creation with all core tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL UNIQUE,
    phone_number TEXT,
    name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index on email for faster lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- ============================================================================
-- VOICE AGENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS voice_agents (
    voice_agent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name TEXT NOT NULL,
    tools_functions JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_voice_agents_user_id ON voice_agents(user_id);
CREATE INDEX idx_voice_agents_model_name ON voice_agents(model_name);
CREATE INDEX idx_voice_agents_created_at ON voice_agents(created_at DESC);

-- ============================================================================
-- SPREADSHEET DESTINATIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS spreadsheet_destinations (
    destination_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    spreadsheet_type TEXT NOT NULL CHECK (spreadsheet_type IN ('google_sheets', 'excel', 'airtable', 'csv')),
    spreadsheet_id TEXT NOT NULL,
    api_credentials TEXT, -- Encrypted credentials
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_spreadsheet_destinations_user_id ON spreadsheet_destinations(user_id);
CREATE INDEX idx_spreadsheet_destinations_type ON spreadsheet_destinations(spreadsheet_type);
CREATE INDEX idx_spreadsheet_destinations_created_at ON spreadsheet_destinations(created_at DESC);

-- ============================================================================
-- SURVEYS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS surveys (
    survey_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    voice_agent_id UUID REFERENCES voice_agents(voice_agent_id) ON DELETE SET NULL,
    destination_id UUID REFERENCES spreadsheet_destinations(destination_id) ON DELETE SET NULL,
    form_link TEXT,
    json_questionnaire JSONB NOT NULL,
    terms_and_conditions TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'closed')),
    voice_agent_tone TEXT,
    voice_agent_instructions TEXT,
    callback_link TEXT,
    max_call_duration INTEGER DEFAULT 5 CHECK (max_call_duration > 0),
    max_retry_attempts INTEGER DEFAULT 2 CHECK (max_retry_attempts >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for foreign keys and common queries
CREATE INDEX idx_surveys_user_id ON surveys(user_id);
CREATE INDEX idx_surveys_voice_agent_id ON surveys(voice_agent_id);
CREATE INDEX idx_surveys_destination_id ON surveys(destination_id);
CREATE INDEX idx_surveys_status ON surveys(status);
CREATE INDEX idx_surveys_created_at ON surveys(created_at DESC);

-- ============================================================================
-- CONTACT TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS contact (
    contact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    survey_id UUID NOT NULL REFERENCES surveys(survey_id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL,
    participant_name TEXT,
    participant_email TEXT,
    participant_metadata JSONB,
    callback TEXT,
    upload_filename TEXT,
    upload_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for foreign keys and common queries
CREATE INDEX idx_contact_survey_id ON contact(survey_id);
CREATE INDEX idx_contact_phone_number ON contact(phone_number);
CREATE INDEX idx_contact_participant_email ON contact(participant_email);
CREATE INDEX idx_contact_upload_timestamp ON contact(upload_timestamp DESC);
CREATE INDEX idx_contact_created_at ON contact(created_at DESC);

-- ============================================================================
-- CALL LOGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_logs (
    twilio_call_sid TEXT PRIMARY KEY,
    contact_id UUID NOT NULL REFERENCES contact(contact_id) ON DELETE CASCADE,
    call_duration INTEGER, -- Duration in seconds
    call_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    recording_url TEXT,
    raw_transcript TEXT,
    raw_responses JSONB,
    mapped_responses JSONB,
    consent BOOLEAN DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'initiated', 'ringing', 'in_progress', 'completed', 'failed', 'busy', 'no_answer', 'canceled', 'incomplete')),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for foreign keys and common queries
CREATE INDEX idx_call_logs_contact_id ON call_logs(contact_id);
CREATE INDEX idx_call_logs_status ON call_logs(status);
CREATE INDEX idx_call_logs_consent ON call_logs(consent);
CREATE INDEX idx_call_logs_call_timestamp ON call_logs(call_timestamp DESC);
CREATE INDEX idx_call_logs_created_at ON call_logs(created_at DESC);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- ============================================================================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to all tables
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_voice_agents_updated_at
    BEFORE UPDATE ON voice_agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_spreadsheet_destinations_updated_at
    BEFORE UPDATE ON spreadsheet_destinations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_surveys_updated_at
    BEFORE UPDATE ON surveys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contact_updated_at
    BEFORE UPDATE ON contact
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_call_logs_updated_at
    BEFORE UPDATE ON call_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE spreadsheet_destinations ENABLE ROW LEVEL SECURITY;
ALTER TABLE surveys ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- USERS TABLE RLS POLICIES
-- ============================================================================

-- Users can read their own data
CREATE POLICY users_select_policy ON users
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can update their own data
CREATE POLICY users_update_policy ON users
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Service role bypass for users table
CREATE POLICY service_role_all_users ON users
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ============================================================================
-- VOICE AGENTS TABLE RLS POLICIES
-- ============================================================================

-- Users can manage their own voice agents
CREATE POLICY voice_agents_select_policy ON voice_agents
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY voice_agents_insert_policy ON voice_agents
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY voice_agents_update_policy ON voice_agents
    FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY voice_agents_delete_policy ON voice_agents
    FOR DELETE
    USING (auth.uid() = user_id);

-- Service role bypass for voice agents table
CREATE POLICY service_role_all_voice_agents ON voice_agents
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ============================================================================
-- SPREADSHEET DESTINATIONS TABLE RLS POLICIES
-- ============================================================================

-- Users can manage their own spreadsheet destinations
CREATE POLICY spreadsheet_destinations_select_policy ON spreadsheet_destinations
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY spreadsheet_destinations_insert_policy ON spreadsheet_destinations
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY spreadsheet_destinations_update_policy ON spreadsheet_destinations
    FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY spreadsheet_destinations_delete_policy ON spreadsheet_destinations
    FOR DELETE
    USING (auth.uid() = user_id);

-- Service role bypass for spreadsheet destinations table
CREATE POLICY service_role_all_spreadsheet_destinations ON spreadsheet_destinations
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ============================================================================
-- SURVEYS TABLE RLS POLICIES
-- ============================================================================

-- Users can manage their own surveys
CREATE POLICY surveys_select_policy ON surveys
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY surveys_insert_policy ON surveys
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY surveys_update_policy ON surveys
    FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY surveys_delete_policy ON surveys
    FOR DELETE
    USING (auth.uid() = user_id);

-- Service role bypass for surveys table
CREATE POLICY service_role_all_surveys ON surveys
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ============================================================================
-- CONTACT TABLE RLS POLICIES
-- ============================================================================

-- Users can manage contacts for their surveys
CREATE POLICY contact_select_policy ON contact
    FOR SELECT
    USING (survey_id IN (
        SELECT survey_id FROM surveys WHERE auth.uid() = user_id
    ));

CREATE POLICY contact_insert_policy ON contact
    FOR INSERT
    WITH CHECK (survey_id IN (
        SELECT survey_id FROM surveys WHERE auth.uid() = user_id
    ));

CREATE POLICY contact_update_policy ON contact
    FOR UPDATE
    USING (survey_id IN (
        SELECT survey_id FROM surveys WHERE auth.uid() = user_id
    ));

CREATE POLICY contact_delete_policy ON contact
    FOR DELETE
    USING (survey_id IN (
        SELECT survey_id FROM surveys WHERE auth.uid() = user_id
    ));

-- Service role bypass for contact table
CREATE POLICY service_role_all_contact ON contact
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ============================================================================
-- CALL LOGS TABLE RLS POLICIES
-- ============================================================================

-- Users can view call logs for their surveys
CREATE POLICY call_logs_select_policy ON call_logs
    FOR SELECT
    USING (contact_id IN (
        SELECT contact_id FROM contact WHERE survey_id IN (
            SELECT survey_id FROM surveys WHERE auth.uid() = user_id
        )
    ));

CREATE POLICY call_logs_insert_policy ON call_logs
    FOR INSERT
    WITH CHECK (contact_id IN (
        SELECT contact_id FROM contact WHERE survey_id IN (
            SELECT survey_id FROM surveys WHERE auth.uid() = user_id
        )
    ));

CREATE POLICY call_logs_update_policy ON call_logs
    FOR UPDATE
    USING (contact_id IN (
        SELECT contact_id FROM contact WHERE survey_id IN (
            SELECT survey_id FROM surveys WHERE auth.uid() = user_id
        )
    ));

-- Service role bypass for call logs table
CREATE POLICY service_role_all_call_logs ON call_logs
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE users IS 'Stores user account information';
COMMENT ON TABLE voice_agents IS 'Stores AI voice agent configurations';
COMMENT ON TABLE spreadsheet_destinations IS 'Stores spreadsheet export destinations';
COMMENT ON TABLE surveys IS 'Stores survey configurations and questionnaires';
COMMENT ON TABLE contact IS 'Stores contact information for survey participants';
COMMENT ON TABLE call_logs IS 'Stores detailed logs of all voice calls made';

COMMENT ON COLUMN surveys.max_call_duration IS 'Maximum call duration in minutes';
COMMENT ON COLUMN surveys.max_retry_attempts IS 'Maximum number of retry attempts for failed calls';
COMMENT ON COLUMN surveys.status IS 'Survey status: draft (not ready), active (accepting responses), closed (no longer accepting responses)';
COMMENT ON COLUMN call_logs.call_duration IS 'Call duration in seconds';
COMMENT ON COLUMN call_logs.consent IS 'Whether participant gave verbal consent at call start';
COMMENT ON COLUMN call_logs.retry_count IS 'Number of retry attempts made for this call';
