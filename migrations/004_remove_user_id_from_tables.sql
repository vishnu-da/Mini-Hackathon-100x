-- Remove user_id from voice_agents and spreadsheet_destinations
-- This enforces that ownership is derived through surveys relationship

-- Drop existing RLS policies that reference user_id
DROP POLICY IF EXISTS voice_agents_select_policy ON voice_agents;
DROP POLICY IF EXISTS voice_agents_insert_policy ON voice_agents;
DROP POLICY IF EXISTS voice_agents_update_policy ON voice_agents;
DROP POLICY IF EXISTS voice_agents_delete_policy ON voice_agents;

DROP POLICY IF EXISTS spreadsheet_destinations_select_policy ON spreadsheet_destinations;
DROP POLICY IF EXISTS spreadsheet_destinations_insert_policy ON spreadsheet_destinations;
DROP POLICY IF EXISTS spreadsheet_destinations_update_policy ON spreadsheet_destinations;
DROP POLICY IF EXISTS spreadsheet_destinations_delete_policy ON spreadsheet_destinations;

-- Remove user_id columns
ALTER TABLE voice_agents DROP COLUMN IF EXISTS user_id;
ALTER TABLE spreadsheet_destinations DROP COLUMN IF EXISTS user_id;

-- Create new RLS policies based on surveys relationship

-- Voice Agents: Access through surveys
CREATE POLICY voice_agents_select_policy ON voice_agents
    FOR SELECT
    USING (voice_agent_id IN (
        SELECT voice_agent_id FROM surveys WHERE auth.uid() = user_id
    ));

CREATE POLICY voice_agents_insert_policy ON voice_agents
    FOR INSERT
    WITH CHECK (true); -- Anyone can create voice agents

CREATE POLICY voice_agents_update_policy ON voice_agents
    FOR UPDATE
    USING (voice_agent_id IN (
        SELECT voice_agent_id FROM surveys WHERE auth.uid() = user_id
    ));

CREATE POLICY voice_agents_delete_policy ON voice_agents
    FOR DELETE
    USING (voice_agent_id IN (
        SELECT voice_agent_id FROM surveys WHERE auth.uid() = user_id
    ));

-- Spreadsheet Destinations: Access through surveys
CREATE POLICY spreadsheet_destinations_select_policy ON spreadsheet_destinations
    FOR SELECT
    USING (destination_id IN (
        SELECT destination_id FROM surveys WHERE auth.uid() = user_id
    ));

CREATE POLICY spreadsheet_destinations_insert_policy ON spreadsheet_destinations
    FOR INSERT
    WITH CHECK (true); -- Anyone can create destinations, ownership via survey

CREATE POLICY spreadsheet_destinations_update_policy ON spreadsheet_destinations
    FOR UPDATE
    USING (destination_id IN (
        SELECT destination_id FROM surveys WHERE auth.uid() = user_id
    ));

CREATE POLICY spreadsheet_destinations_delete_policy ON spreadsheet_destinations
    FOR DELETE
    USING (destination_id IN (
        SELECT destination_id FROM surveys WHERE auth.uid() = user_id
    ));

-- Create indexes to optimize RLS policy JOINs
CREATE INDEX IF NOT EXISTS idx_surveys_voice_agent_id ON surveys(voice_agent_id);
CREATE INDEX IF NOT EXISTS idx_surveys_destination_id ON surveys(destination_id);

COMMENT ON TABLE voice_agents IS 'Voice agents are reusable across surveys. Access controlled via surveys relationship.';
COMMENT ON TABLE spreadsheet_destinations IS 'Spreadsheet destinations are linked to surveys. Access controlled via surveys relationship.';