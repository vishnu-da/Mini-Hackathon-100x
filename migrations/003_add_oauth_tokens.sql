-- AI Voice Survey Platform - OAuth Tokens Migration
-- Version: 003
-- Description: Add OAuth tokens table for Google and Microsoft Forms API access

-- ============================================================================
-- OAUTH TOKENS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS oauth_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('google', 'microsoft')),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type TEXT DEFAULT 'Bearer',
    expires_at TIMESTAMPTZ NOT NULL,
    scope TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- Add indexes for performance
CREATE INDEX idx_oauth_tokens_user_id ON oauth_tokens(user_id);
CREATE INDEX idx_oauth_tokens_provider ON oauth_tokens(user_id, provider);
CREATE INDEX idx_oauth_tokens_expires_at ON oauth_tokens(expires_at);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on oauth_tokens table
ALTER TABLE oauth_tokens ENABLE ROW LEVEL SECURITY;

-- Users can only access their own tokens
CREATE POLICY "Users manage own tokens" ON oauth_tokens
    FOR ALL
    USING (auth.uid() = user_id);

-- Service role bypass for backend operations
CREATE POLICY "Service role all access" ON oauth_tokens
    FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ============================================================================
-- TRIGGER FOR UPDATED_AT TIMESTAMP
-- ============================================================================

CREATE TRIGGER update_oauth_tokens_updated_at
    BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE oauth_tokens IS 'Stores OAuth 2.0 tokens for third-party integrations (Google Forms, Microsoft Forms)';
COMMENT ON COLUMN oauth_tokens.token_id IS 'Unique identifier for the token record';
COMMENT ON COLUMN oauth_tokens.user_id IS 'User who owns this OAuth token';
COMMENT ON COLUMN oauth_tokens.provider IS 'OAuth provider: google or microsoft';
COMMENT ON COLUMN oauth_tokens.access_token IS 'Encrypted OAuth access token';
COMMENT ON COLUMN oauth_tokens.refresh_token IS 'Encrypted OAuth refresh token for token renewal';
COMMENT ON COLUMN oauth_tokens.token_type IS 'Token type (typically Bearer)';
COMMENT ON COLUMN oauth_tokens.expires_at IS 'Timestamp when the access token expires';
COMMENT ON COLUMN oauth_tokens.scope IS 'OAuth scopes granted by the user';
