#!/bin/bash
# Script to run analytics tables migration
# Usage: ./scripts/run_migration.sh <neon-connection-string>

if [ -z "$1" ]; then
    echo "Error: Please provide your Neon database connection string"
    echo "Usage: ./scripts/run_migration.sh 'postgresql://user:pass@host/db'"
    echo ""
    echo "You can find your connection string in:"
    echo "  1. Neon dashboard -> Connection Details"
    echo "  2. OR Render dashboard -> Environment -> DATABASE_URL"
    exit 1
fi

CONNECTION_STRING="$1"

echo "🔄 Running analytics tables migration..."
echo ""

psql "$CONNECTION_STRING" -f migrations/add_analytics_tables.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
    echo "📊 Analytics tables created:"
    echo "   - daily_user_stats"
    echo "   - feature_usage_stats"
    echo "   - subscription_stats"
    echo "   - user_events"
    echo "   - user_retention"
else
    echo ""
    echo "❌ Migration failed. Please check the error above."
    exit 1
fi
