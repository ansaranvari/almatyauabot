-- Add analytics and metrics tracking
-- Migration: add_analytics_tables
-- Created: 2026-01-02

-- Create daily_user_stats table
CREATE TABLE IF NOT EXISTS daily_user_stats (
    id BIGSERIAL PRIMARY KEY,
    date TIMESTAMP NOT NULL,
    total_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    returning_users INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    avg_messages_per_user FLOAT DEFAULT 0.0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for daily_user_stats
CREATE INDEX IF NOT EXISTS idx_daily_user_stats_date ON daily_user_stats(date);

-- Add comment
COMMENT ON TABLE daily_user_stats IS 'Daily aggregated user statistics for tracking growth and engagement';


-- Create feature_usage_stats table
CREATE TABLE IF NOT EXISTS feature_usage_stats (
    id BIGSERIAL PRIMARY KEY,
    date TIMESTAMP NOT NULL,
    feature_name VARCHAR(100) NOT NULL,
    usage_count INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for feature_usage_stats
CREATE INDEX IF NOT EXISTS idx_feature_usage_stats_date ON feature_usage_stats(date);
CREATE INDEX IF NOT EXISTS idx_feature_usage_stats_feature ON feature_usage_stats(feature_name);
CREATE INDEX IF NOT EXISTS idx_feature_usage_stats_date_feature ON feature_usage_stats(date, feature_name);

-- Add comment
COMMENT ON TABLE feature_usage_stats IS 'Track usage of different bot features (check_air, subscriptions, favorites, etc.)';


-- Create subscription_stats table
CREATE TABLE IF NOT EXISTS subscription_stats (
    id BIGSERIAL PRIMARY KEY,
    date TIMESTAMP NOT NULL,
    new_subscriptions INTEGER DEFAULT 0,
    cancelled_subscriptions INTEGER DEFAULT 0,
    active_subscriptions INTEGER DEFAULT 0,
    conversion_rate FLOAT DEFAULT 0.0,
    notifications_sent INTEGER DEFAULT 0,
    notifications_failed INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for subscription_stats
CREATE INDEX IF NOT EXISTS idx_subscription_stats_date ON subscription_stats(date);

-- Add comment
COMMENT ON TABLE subscription_stats IS 'Daily subscription metrics and notification delivery stats';


-- Create user_events table
CREATE TABLE IF NOT EXISTS user_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for user_events
CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_events_event_type ON user_events(event_type);
CREATE INDEX IF NOT EXISTS idx_user_events_timestamp ON user_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_events_user_timestamp ON user_events(user_id, timestamp DESC);

-- Add comment
COMMENT ON TABLE user_events IS 'Individual user event tracking for detailed analytics';


-- Create user_retention table
CREATE TABLE IF NOT EXISTS user_retention (
    id BIGSERIAL PRIMARY KEY,
    cohort_date TIMESTAMP NOT NULL,
    cohort_size INTEGER DEFAULT 0,
    day_1_retained INTEGER DEFAULT 0,
    day_7_retained INTEGER DEFAULT 0,
    day_14_retained INTEGER DEFAULT 0,
    day_30_retained INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for user_retention
CREATE INDEX IF NOT EXISTS idx_user_retention_cohort_date ON user_retention(cohort_date);

-- Add comment
COMMENT ON TABLE user_retention IS 'User retention cohort analysis to track long-term engagement';
