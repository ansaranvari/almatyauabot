#!/usr/bin/env python3
"""
Production migration script - adds missing columns to daily_user_stats
Run this via Render shell: python migrate_production.py
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.db.database import AsyncSessionLocal


async def main():
    print("🔧 Running production migration...")
    print("Adding air_checks and unique_air_checkers columns to daily_user_stats")

    try:
        async with AsyncSessionLocal() as db:
            # Add air_checks column
            print("  → Adding air_checks column...")
            await db.execute(text(
                "ALTER TABLE daily_user_stats ADD COLUMN IF NOT EXISTS air_checks INTEGER DEFAULT 0"
            ))

            # Add unique_air_checkers column
            print("  → Adding unique_air_checkers column...")
            await db.execute(text(
                "ALTER TABLE daily_user_stats ADD COLUMN IF NOT EXISTS unique_air_checkers INTEGER DEFAULT 0"
            ))

            # Update existing records
            print("  → Updating existing records...")
            await db.execute(text(
                "UPDATE daily_user_stats SET air_checks = 0, unique_air_checkers = 0 "
                "WHERE air_checks IS NULL OR unique_air_checkers IS NULL"
            ))

            await db.commit()
            print("✅ Migration completed successfully!")
            return 0

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
