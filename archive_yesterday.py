#!/usr/bin/env python3
"""
Manual script to archive yesterday's analytics data

Run this to recover missing analytics data for yesterday.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.services.analytics import analytics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ALMATY_TZ = ZoneInfo("Asia/Almaty")


async def main():
    """Archive yesterday's analytics"""
    # Get yesterday's date in Almaty timezone
    now_almaty = datetime.now(ALMATY_TZ)
    yesterday_almaty = (now_almaty - timedelta(days=1)).date()

    logger.info(f"Archiving analytics for yesterday: {yesterday_almaty}")

    try:
        # Archive daily stats
        await analytics.update_daily_stats(target_date=yesterday_almaty)

        # Archive subscription stats
        await analytics.update_subscription_stats()

        logger.info("✅ Successfully archived yesterday's analytics")

        # Also archive today to ensure it's up to date
        today_almaty = now_almaty.date()
        logger.info(f"Also archiving today's analytics: {today_almaty}")
        await analytics.update_daily_stats(target_date=today_almaty)

        logger.info("✅ Successfully archived today's analytics")

    except Exception as e:
        logger.error(f"Failed to archive analytics: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
