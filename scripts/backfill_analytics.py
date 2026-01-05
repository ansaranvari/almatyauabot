#!/usr/bin/env python3
"""
Backfill analytics data from existing database records
Run this once to populate analytics for historical data
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.db.models import User, UserQuery, Subscription
from app.db.analytics_models import DailyUserStats, UserEvent
from app.services.analytics import AnalyticsService


async def backfill_user_events():
    """Create user events from existing data"""
    print("📊 Backfilling user events...")

    async with AsyncSessionLocal() as db:
        # Get all users and create "user_registered" events
        users_result = await db.execute(select(User))
        users = users_result.scalars().all()

        for user in users:
            event = UserEvent(
                user_id=user.id,
                event_type="user_registered",
                event_data={"language": user.language},
                timestamp=user.created_at
            )
            db.add(event)

        print(f"  ✓ Created {len(users)} user_registered events")

        # Get all user queries and create "check_air" events
        queries_result = await db.execute(select(UserQuery))
        queries = queries_result.scalars().all()

        for query in queries:
            event = UserEvent(
                user_id=query.user_id,
                event_type="check_air",
                event_data={
                    "latitude": query.latitude,
                    "longitude": query.longitude,
                    "station_id": query.station_id
                },
                timestamp=query.created_at
            )
            db.add(event)

        print(f"  ✓ Created {len(queries)} check_air events")

        # Get all subscriptions and create "subscription_created" events
        subs_result = await db.execute(select(Subscription))
        subscriptions = subs_result.scalars().all()

        for sub in subscriptions:
            event = UserEvent(
                user_id=sub.user_id,
                event_type="subscription_created",
                event_data={
                    "duration": "custom",
                    "is_active": sub.is_active
                },
                timestamp=sub.created_at
            )
            db.add(event)

        print(f"  ✓ Created {len(subscriptions)} subscription_created events")

        await db.commit()
        print("✅ User events backfilled successfully!\n")


async def backfill_daily_stats():
    """Aggregate daily statistics from events"""
    print("📈 Calculating daily statistics...")

    async with AsyncSessionLocal() as db:
        # Get date range
        min_date_result = await db.execute(
            select(func.min(User.created_at))
        )
        min_date = min_date_result.scalar()

        if not min_date:
            print("  ⚠️  No users found, skipping daily stats")
            return

        # Start from first user registration date
        current_date = min_date.replace(hour=0, minute=0, second=0, microsecond=0)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        days_processed = 0
        while current_date <= today:
            next_date = current_date + timedelta(days=1)

            # Count total users up to this date
            total_users_result = await db.execute(
                select(func.count(User.id)).where(User.created_at < next_date)
            )
            total_users = total_users_result.scalar() or 0

            # Count new users on this date
            new_users_result = await db.execute(
                select(func.count(User.id)).where(
                    User.created_at >= current_date,
                    User.created_at < next_date
                )
            )
            new_users = new_users_result.scalar() or 0

            # Count active users (users with events on this date)
            active_users_result = await db.execute(
                select(func.count(func.distinct(UserEvent.user_id))).where(
                    UserEvent.timestamp >= current_date,
                    UserEvent.timestamp < next_date
                )
            )
            active_users = active_users_result.scalar() or 0

            # Count total events (messages) on this date
            total_messages_result = await db.execute(
                select(func.count(UserEvent.id)).where(
                    UserEvent.timestamp >= current_date,
                    UserEvent.timestamp < next_date
                )
            )
            total_messages = total_messages_result.scalar() or 0

            # Calculate avg messages per active user
            avg_messages = total_messages / active_users if active_users > 0 else 0.0

            # Create daily stats record
            daily_stat = DailyUserStats(
                date=current_date,
                total_users=total_users,
                new_users=new_users,
                active_users=active_users,
                returning_users=0,  # We can't easily calculate this from historical data
                total_messages=total_messages,
                avg_messages_per_user=avg_messages
            )

            db.add(daily_stat)
            days_processed += 1

            current_date = next_date

        await db.commit()
        print(f"  ✓ Processed {days_processed} days of statistics")
        print("✅ Daily statistics calculated successfully!\n")


async def main():
    """Run all backfill tasks"""
    print("\n🚀 Starting analytics backfill...\n")

    try:
        # Step 1: Backfill user events
        await backfill_user_events()

        # Step 2: Aggregate daily stats
        await backfill_daily_stats()

        print("🎉 Analytics backfill complete!")
        print("\n📊 You can now view the dashboard at: https://almatyauabot.onrender.com/admin\n")

    except Exception as e:
        print(f"\n❌ Error during backfill: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
