# Deploy Analytics Fix

## Problem
Daily stats were disappearing after new day started because they were only calculated in real-time, never archived to database.

## Solution Implemented
- Created analytics scheduler that archives daily stats twice per day (23:55 and 00:05 Almaty time)
- Added air_checks and unique_air_checkers tracking to daily stats
- Scheduler runs immediately on startup to catch any missing data

## Deployment Steps

### 1. Run Database Migration

The migration adds `air_checks` and `unique_air_checkers` columns to the `daily_user_stats` table.

**On production server:**
```bash
# Connect to database container
docker exec -i qazairbot-postgres-1 psql -U qazairbot_user -d qazairbot < migrations/add_air_checks_to_daily_stats.sql
```

**Or manually via psql:**
```sql
ALTER TABLE daily_user_stats
ADD COLUMN IF NOT EXISTS air_checks INTEGER DEFAULT 0;

ALTER TABLE daily_user_stats
ADD COLUMN IF NOT EXISTS unique_air_checkers INTEGER DEFAULT 0;

UPDATE daily_user_stats
SET air_checks = 0, unique_air_checkers = 0
WHERE air_checks IS NULL OR unique_air_checkers IS NULL;
```

### 2. Deploy Code

Push to GitHub and Render will automatically deploy:
```bash
git push
```

### 3. Recover Yesterday's Data (Optional)

If you want to recover yesterday's missing data after deployment:

```bash
# On production server
docker exec qazairbot-web-1 python archive_yesterday.py
```

This will:
- Archive yesterday's complete analytics (80+ active users, new users, air checks, etc.)
- Also update today's stats to ensure they're current

The scheduler will automatically archive future days at 23:55 and 00:05 Almaty time.

### 4. Verify

Check admin dashboard after deployment - you should see:
- Yesterday's data preserved in graphs
- Today's real-time data continues to update
- Historical data no longer disappears

## What Changed

### New Files
- `app/services/analytics_scheduler.py` - Daily analytics archiving service
- `archive_yesterday.py` - Manual recovery script
- `migrations/add_air_checks_to_daily_stats.sql` - Database migration

### Modified Files
- `app/db/analytics_models.py` - Added air_checks and unique_air_checkers fields
- `app/services/analytics.py` - Added target_date parameter to update_daily_stats()
- `app/main.py` - Integrated analytics_scheduler into startup

## Architecture

```
┌─────────────────┐
│ User Events     │
│ (user_events    │
│  table)         │
└────────┬────────┘
         │
         │ Real-time queries for today
         ├────────────────────────────────► Dashboard (shows real-time)
         │
         │ Archived at 23:55 & 00:05
         ↓
┌─────────────────┐
│ Daily Stats     │
│ (daily_user_    │
│  stats table)   │
└────────┬────────┘
         │
         │ Historical queries (last 30 days)
         └────────────────────────────────► Dashboard (shows graphs)
```

## Monitoring

Check logs for successful archiving:
```bash
docker logs qazairbot-web-1 | grep "analytics"
```

You should see:
- On startup: "Starting analytics scheduler background task"
- On startup: "Running initial analytics archive on startup..."
- At 23:55/00:05 Almaty: "Archiving analytics for..."
- After archiving: "✅ Successfully archived ... analytics"
