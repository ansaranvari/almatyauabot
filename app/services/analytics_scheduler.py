"""
Daily analytics scheduler - archives daily stats at end of each day
"""
import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.services.analytics import analytics

logger = logging.getLogger(__name__)

# Almaty timezone
ALMATY_TZ = ZoneInfo("Asia/Almaty")


class AnalyticsScheduler:
    """Scheduler for archiving daily analytics"""

    def __init__(self):
        self.is_running = False

    async def start_scheduler(self):
        """
        Start periodic analytics archiving

        Runs twice per day:
        - At 23:55 Almaty time (archive today's data before midnight)
        - At 00:05 Almaty time (archive yesterday's data after midnight transition)
        """
        logger.info("Starting analytics scheduler (archives at 23:55 and 00:05 Almaty time)")
        self.is_running = True

        # Run immediately on startup to archive any missing data
        logger.info("Running initial analytics archive on startup...")
        try:
            await self._archive_yesterday()
            await self._archive_today()
        except Exception as e:
            logger.error(f"Initial analytics archive failed: {e}", exc_info=True)

        while self.is_running:
            try:
                # Get current time in Almaty
                now_almaty = datetime.now(ALMATY_TZ)
                current_hour = now_almaty.hour
                current_minute = now_almaty.minute

                # Determine next archive time
                if current_hour < 0 or (current_hour == 0 and current_minute < 5):
                    # Before 00:05 - wait until 00:05
                    next_run = now_almaty.replace(hour=0, minute=5, second=0, microsecond=0)
                    if next_run < now_almaty:
                        next_run += timedelta(days=1)
                    archive_yesterday = True
                elif current_hour < 23 or (current_hour == 23 and current_minute < 55):
                    # Before 23:55 - wait until 23:55
                    next_run = now_almaty.replace(hour=23, minute=55, second=0, microsecond=0)
                    if next_run < now_almaty:
                        next_run += timedelta(days=1)
                    archive_yesterday = False
                else:
                    # After 23:55 - wait until 00:05 tomorrow
                    next_run = now_almaty.replace(hour=0, minute=5, second=0, microsecond=0) + timedelta(days=1)
                    archive_yesterday = True

                # Calculate wait time
                wait_seconds = (next_run - now_almaty).total_seconds()
                logger.info(f"Next analytics archive at {next_run.strftime('%H:%M')} Almaty time (in {wait_seconds/60:.1f} minutes)")

                await asyncio.sleep(wait_seconds)

                # Run archive
                if archive_yesterday:
                    logger.info("Running analytics archive for yesterday...")
                    await self._archive_yesterday()
                else:
                    logger.info("Running analytics archive for today...")
                    await self._archive_today()

            except Exception as e:
                logger.error(f"Analytics scheduler task failed: {e}", exc_info=True)
                # Wait 5 minutes before retrying on error
                await asyncio.sleep(300)

    async def _archive_yesterday(self):
        """Archive analytics for yesterday"""
        try:
            # Get yesterday's date in Almaty timezone
            now_almaty = datetime.now(ALMATY_TZ)
            yesterday_almaty = (now_almaty - timedelta(days=1)).date()

            logger.info(f"Archiving analytics for yesterday: {yesterday_almaty.strftime('%Y-%m-%d')}")

            # Update daily stats (pass yesterday's date)
            await analytics.update_daily_stats(target_date=yesterday_almaty)

            # Update subscription stats
            await analytics.update_subscription_stats()

            logger.info("✅ Successfully archived yesterday's analytics")
        except Exception as e:
            logger.error(f"Failed to archive yesterday's analytics: {e}", exc_info=True)

    async def _archive_today(self):
        """Archive analytics for today (in case of gaps)"""
        try:
            now_almaty = datetime.now(ALMATY_TZ)
            today_almaty = now_almaty.date()

            logger.info(f"Archiving analytics for today: {today_almaty.strftime('%Y-%m-%d')}")

            # Update daily stats (pass today's date)
            await analytics.update_daily_stats(target_date=today_almaty)

            # Update subscription stats
            await analytics.update_subscription_stats()

            logger.info("✅ Successfully archived today's analytics")
        except Exception as e:
            logger.error(f"Failed to archive today's analytics: {e}", exc_info=True)

    def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        logger.info("Analytics scheduler stopped")


# Global analytics scheduler instance
analytics_scheduler = AnalyticsScheduler()
