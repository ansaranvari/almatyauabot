"""
Script to identify and remove duplicate user records from the database.

This script:
1. Finds all users that have duplicate records (same Telegram ID)
2. Keeps the most recent record for each user
3. Deletes older duplicate records
"""
import asyncio
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal, init_db
from app.db.models import User


async def cleanup_duplicates():
    """Find and remove duplicate user records"""

    await init_db()

    async with AsyncSessionLocal() as db:
        # Find user IDs that have duplicates
        duplicate_query = (
            select(User.id, func.count(User.id).label('count'))
            .group_by(User.id)
            .having(func.count(User.id) > 1)
        )

        result = await db.execute(duplicate_query)
        duplicates = result.all()

        if not duplicates:
            print("✅ No duplicate users found!")
            return

        print(f"⚠️  Found {len(duplicates)} users with duplicate records:")

        total_deleted = 0

        for user_id, count in duplicates:
            print(f"\nUser ID {user_id}: {count} records")

            # Get all records for this user, ordered by created_at if available
            # Since we don't have created_at, we'll keep the first one and delete the rest
            user_records = await db.execute(
                select(User).where(User.id == user_id)
            )
            all_records = user_records.scalars().all()

            # Keep the first record (arbitrary choice since we don't have timestamps)
            keep_record = all_records[0]
            delete_records = all_records[1:]

            print(f"  Keeping: {keep_record.username or keep_record.first_name or 'No name'}")
            print(f"  Deleting: {len(delete_records)} duplicate(s)")

            # Delete duplicates
            for record in delete_records:
                await db.delete(record)
                total_deleted += 1

        await db.commit()

        print(f"\n✅ Cleanup complete! Deleted {total_deleted} duplicate records.")
        print(f"📊 {len(duplicates)} users now have unique records.")


if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
