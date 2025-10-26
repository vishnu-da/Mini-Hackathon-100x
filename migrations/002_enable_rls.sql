-- AI Voice Survey Platform - RLS Policies Migration
-- Version: 002
-- Description: Comprehensive Row Level Security (RLS) policies for all tables
-- Note: This migration is for reference. RLS policies are already included in 001_create_schema.sql

-- This file can be used to re-apply RLS policies if they need to be updated or reset

-- ============================================================================
-- DROP EXISTING POLICIES (if re-applying)
-- ============================================================================

-- Users table policies
DROP POLICY IF EXISTS users_select_policy ON users;
DROP POLICY IF EXISTS users_update_policy ON users;
DROP POLICY IF EXISTS service_role_all_users ON users;

-- Voice agents table policies
DROP POLICY IF EXISTS voice_agents_select_policy ON voice_agents;
DROP POLICY IF EXISTS voice_agents_insert_policy ON voice_agents;
DROP POLICY IF EXISTS voice_agents_update_policy ON voice_agents;
DROP POLICY IF EXISTS voice_agents_delete_policy ON voice_agents;
DROP POLICY IF EXISTS service_role_all_voice_agents ON voice_agents;

-- Spreadsheet destinations table policies
DROP POLICY IF EXISTS spreadsheet_destinations_select_policy ON spreadsheet_destinations;
DROP POLICY IF EXISTS spreadsheet_destinations_insert_policy ON spreadsheet_destinations;
DROP POLICY IF EXISTS spreadsheet_destinations_update_policy ON spreadsheet_destinations;
DROP POLICY IF EXISTS spreadsheet_destinations_delete_policy ON spreadsheet_destinations;
DROP POLICY IF EXISTS service_role_all_spreadsheet_destinations ON spreadsheet_destinations;

-- Surveys table policies
DROP POLICY IF EXISTS surveys_select_policy ON surveys;
DROP POLICY IF EXISTS surveys_insert_policy ON surveys;
DROP POLICY IF EXISTS surveys_update_policy ON surveys;
DROP POLICY IF EXISTS surveys_delete_policy ON surveys;
DROP POLICY IF EXISTS service_role_all_surveys ON surveys;

-- Contact table policies
DROP POLICY IF EXISTS contact_select_policy ON contact;
DROP POLICY IF EXISTS contact_insert_policy ON contact;
DROP POLICY IF EXISTS contact_update_policy ON contact;
DROP POLICY IF EXISTS contact_delete_policy ON contact;
DROP POLICY IF EXISTS service_role_all_contact ON contact;

-- Call logs table policies
DROP POLICY IF EXISTS call_logs_select_policy ON call_logs;
DROP POLICY IF EXISTS call_logs_insert_policy ON call_logs;
DROP POLICY IF EXISTS call_logs_update_policy ON call_logs;
DROP POLICY IF EXISTS service_role_all_call_logs ON call_logs;

-- ============================================================================
-- ENABLE RLS ON ALL TABLES
-- ============================================================================

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
-- VERIFICATION QUERIES
-- ============================================================================

-- Check RLS is enabled on all tables
-- SELECT schemaname, tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY tablename;

-- View all RLS policies
-- SELECT schemaname, tablename, policyname, permissive, roles, cmd
-- FROM pg_policies
-- WHERE schemaname = 'public'
-- ORDER BY tablename, policyname;
