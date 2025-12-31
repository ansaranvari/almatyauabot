-- Add subscription features: duration, quiet hours, and safety net sessions
-- Migration: add_subscription_features
-- Created: 2025-12-27

-- Add duration and quiet hours columns to subscriptions table
ALTER TABLE subscriptions
ADD COLUMN IF NOT EXISTS expiry_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS mute_start INTEGER NOT NULL DEFAULT 23,
ADD COLUMN IF NOT EXISTS mute_end INTEGER NOT NULL DEFAULT 7;

-- Add comments for documentation
COMMENT ON COLUMN subscriptions.expiry_date IS 'Subscription expiration time (NULL = forever)';
COMMENT ON COLUMN subscriptions.mute_start IS 'Hour when quiet hours start (0-23)';
COMMENT ON COLUMN subscriptions.mute_end IS 'Hour when quiet hours end (0-23)';

-- Create safety net sessions table
CREATE TABLE IF NOT EXISTS safety_net_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    subscription_id BIGINT NOT NULL,
    start_aqi INTEGER NOT NULL,
    session_expiry TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_safety_net_user_id ON safety_net_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_safety_net_subscription_id ON safety_net_sessions(subscription_id);
CREATE INDEX IF NOT EXISTS idx_safety_net_expiry ON safety_net_sessions(session_expiry);

-- Add comment for table
COMMENT ON TABLE safety_net_sessions IS 'Temporary 3-hour sessions for reverse air quality monitoring';
