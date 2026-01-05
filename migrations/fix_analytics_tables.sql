-- Fix analytics tables to match SQLAlchemy models
-- Migration: fix_analytics_tables
-- Created: 2026-01-02

-- Add missing session_id column to user_events
ALTER TABLE user_events ADD COLUMN IF NOT EXISTS session_id VARCHAR(50);

-- Create index for session_id
CREATE INDEX IF NOT EXISTS idx_user_events_session_id ON user_events(session_id);

-- Fix user_retention table structure
-- Drop old structure if exists
DROP TABLE IF EXISTS user_retention;

-- Create with correct structure matching the model
CREATE TABLE IF NOT EXISTS user_retention (
    id BIGSERIAL PRIMARY KEY,
    cohort_date TIMESTAMP NOT NULL,
    day_number INTEGER NOT NULL,
    cohort_size INTEGER DEFAULT 0,
    retained_users INTEGER DEFAULT 0,
    retention_rate FLOAT DEFAULT 0.0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for user_retention
CREATE INDEX IF NOT EXISTS idx_user_retention_cohort_date ON user_retention(cohort_date);
CREATE INDEX IF NOT EXISTS idx_retention_cohort_day ON user_retention(cohort_date, day_number);

-- Add missing updated_at columns to tables that need them
ALTER TABLE daily_user_stats ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE feature_usage_stats ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE subscription_stats ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Add missing columns to subscription_stats to match model
ALTER TABLE subscription_stats ADD COLUMN IF NOT EXISTS total_subscriptions INTEGER DEFAULT 0;
ALTER TABLE subscription_stats ADD COLUMN IF NOT EXISTS expired_subscriptions INTEGER DEFAULT 0;
ALTER TABLE subscription_stats ADD COLUMN IF NOT EXISTS subscription_views INTEGER DEFAULT 0;
ALTER TABLE subscription_stats ADD COLUMN IF NOT EXISTS subscription_conversions INTEGER DEFAULT 0;
ALTER TABLE subscription_stats ADD COLUMN IF NOT EXISTS notifications_delivered INTEGER DEFAULT 0;

-- Add comment
COMMENT ON TABLE user_retention IS 'User retention cohort analysis with flexible day tracking';
