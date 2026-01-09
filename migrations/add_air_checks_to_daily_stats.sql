-- Migration: Add air quality check metrics to daily_user_stats table
-- Created: 2026-01-09
-- Description: Adds air_checks and unique_air_checkers columns to track air quality checking activity

-- Add air_checks column (total air quality checks per day)
ALTER TABLE daily_user_stats
ADD COLUMN IF NOT EXISTS air_checks INTEGER DEFAULT 0;

-- Add unique_air_checkers column (unique users who checked air quality per day)
ALTER TABLE daily_user_stats
ADD COLUMN IF NOT EXISTS unique_air_checkers INTEGER DEFAULT 0;

-- Update existing records to have 0 for these fields
UPDATE daily_user_stats
SET air_checks = 0, unique_air_checkers = 0
WHERE air_checks IS NULL OR unique_air_checkers IS NULL;

-- Add comments for documentation
COMMENT ON COLUMN daily_user_stats.air_checks IS 'Total number of air quality checks performed on this day';
COMMENT ON COLUMN daily_user_stats.unique_air_checkers IS 'Number of unique users who checked air quality on this day';
