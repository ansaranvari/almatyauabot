-- Add onboarding flags to track first-time feature usage
-- Migration: add_user_onboarding_flags
-- Created: 2025-12-30

-- Add onboarding columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS seen_check_onboarding BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS seen_subscribe_onboarding BOOLEAN NOT NULL DEFAULT FALSE;

-- Add comments for documentation
COMMENT ON COLUMN users.seen_check_onboarding IS 'Whether user has seen the air quality check onboarding';
COMMENT ON COLUMN users.seen_subscribe_onboarding IS 'Whether user has seen the subscription onboarding';
