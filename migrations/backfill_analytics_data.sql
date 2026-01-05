-- Backfill analytics data from existing records
-- Run this to populate analytics with historical data

-- Step 1: Create user_events from existing data
-- Insert user registration events
INSERT INTO user_events (user_id, event_type, event_data, timestamp)
SELECT
    id,
    'user_registered',
    json_build_object('language', language),
    created_at
FROM users
WHERE NOT EXISTS (
    SELECT 1 FROM user_events
    WHERE user_events.user_id = users.id
    AND user_events.event_type = 'user_registered'
);

-- Insert check_air events from user_queries
INSERT INTO user_events (user_id, event_type, event_data, timestamp)
SELECT
    user_id,
    'check_air',
    json_build_object(
        'latitude', latitude,
        'longitude', longitude,
        'station_id', station_id
    ),
    created_at
FROM user_queries
WHERE NOT EXISTS (
    SELECT 1 FROM user_events
    WHERE user_events.user_id = user_queries.user_id
    AND user_events.timestamp = user_queries.created_at
    AND user_events.event_type = 'check_air'
);

-- Insert subscription_created events
INSERT INTO user_events (user_id, event_type, event_data, timestamp)
SELECT
    user_id,
    'subscription_created',
    json_build_object('is_active', is_active),
    created_at
FROM subscriptions
WHERE NOT EXISTS (
    SELECT 1 FROM user_events
    WHERE user_events.user_id = subscriptions.user_id
    AND user_events.timestamp = subscriptions.created_at
    AND user_events.event_type = 'subscription_created'
);

-- Step 2: Calculate daily statistics
-- Generate date series from first user to today
WITH date_series AS (
    SELECT generate_series(
        date_trunc('day', (SELECT MIN(created_at) FROM users)),
        date_trunc('day', NOW()),
        '1 day'::interval
    )::timestamp AS day
),
daily_aggregates AS (
    SELECT
        d.day,
        -- Total users up to this date
        (SELECT COUNT(*) FROM users WHERE created_at < d.day + interval '1 day') AS total_users,
        -- New users on this date
        (SELECT COUNT(*) FROM users WHERE created_at >= d.day AND created_at < d.day + interval '1 day') AS new_users,
        -- Active users (with events on this date)
        (SELECT COUNT(DISTINCT user_id) FROM user_events WHERE timestamp >= d.day AND timestamp < d.day + interval '1 day') AS active_users,
        -- Total events on this date
        (SELECT COUNT(*) FROM user_events WHERE timestamp >= d.day AND timestamp < d.day + interval '1 day') AS total_messages
    FROM date_series d
)
INSERT INTO daily_user_stats (date, total_users, new_users, active_users, returning_users, total_messages, avg_messages_per_user)
SELECT
    day,
    total_users,
    new_users,
    active_users,
    0, -- returning_users (can't easily calculate from historical data)
    total_messages,
    CASE WHEN active_users > 0 THEN total_messages::float / active_users ELSE 0 END
FROM daily_aggregates
ON CONFLICT DO NOTHING;

-- Step 3: Calculate feature usage stats
WITH date_series AS (
    SELECT generate_series(
        date_trunc('day', (SELECT MIN(timestamp) FROM user_events)),
        date_trunc('day', NOW()),
        '1 day'::interval
    )::timestamp AS day
)
INSERT INTO feature_usage_stats (date, feature_name, usage_count, unique_users)
SELECT
    d.day,
    e.event_type,
    COUNT(*) AS usage_count,
    COUNT(DISTINCT e.user_id) AS unique_users
FROM date_series d
LEFT JOIN user_events e ON e.timestamp >= d.day AND e.timestamp < d.day + interval '1 day'
WHERE e.event_type IS NOT NULL
GROUP BY d.day, e.event_type
ON CONFLICT DO NOTHING;

-- Show summary
SELECT
    'user_events' AS table_name,
    COUNT(*) AS record_count
FROM user_events
UNION ALL
SELECT
    'daily_user_stats',
    COUNT(*)
FROM daily_user_stats
UNION ALL
SELECT
    'feature_usage_stats',
    COUNT(*)
FROM feature_usage_stats;
