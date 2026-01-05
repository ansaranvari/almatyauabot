#!/usr/bin/env python3
"""
Run analytics tables migration
"""
import asyncio
import asyncpg
import sys


async def run_migration(connection_string: str):
    """Execute the analytics migration SQL"""

    # Read the migration file
    with open('migrations/add_analytics_tables.sql', 'r') as f:
        sql = f.read()

    # Convert asyncpg connection string to standard postgresql
    if connection_string.startswith('postgresql+asyncpg://'):
        connection_string = connection_string.replace('postgresql+asyncpg://', 'postgresql://')

    # Replace ssl=require with sslmode=require for asyncpg
    connection_string = connection_string.replace('ssl=require', 'sslmode=require')

    print("🔄 Connecting to database...")

    try:
        # Connect to database
        conn = await asyncpg.connect(connection_string)

        print("✅ Connected successfully!")
        print("🔄 Running migration...")
        print("")

        # Execute the migration
        await conn.execute(sql)

        print("✅ Migration completed successfully!")
        print("")
        print("📊 Analytics tables created:")
        print("   ✓ daily_user_stats")
        print("   ✓ feature_usage_stats")
        print("   ✓ subscription_stats")
        print("   ✓ user_events")
        print("   ✓ user_retention")
        print("")
        print("🎉 You can now access the dashboard at: https://almatyauabot.onrender.com/admin")

        # Close connection
        await conn.close()

    except Exception as e:
        print(f"❌ Error running migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/run_analytics_migration.py '<connection_string>'")
        sys.exit(1)

    connection_string = sys.argv[1]
    asyncio.run(run_migration(connection_string))
