"""
Run bot in polling mode for local development/testing
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.core.config import get_settings
from app.db.database import init_db
from app.services.cache import cache
from app.services.sync import data_sync
from app.services.subscription_checker import subscription_checker
from app.bot.handlers import router
from app.bot.middlewares.i18n import I18nMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


async def main():
    """Main function to run bot in polling mode"""

    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    # Register middleware
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())

    # Register routers
    dp.include_router(router)

    try:
        # Initialize database
        logger.info("Initializing database")
        await init_db()

        # Connect to Redis
        logger.info("Connecting to Redis")
        await cache.connect()

        # Run initial sync FIRST before starting scheduler
        logger.info("Running initial data sync")
        try:
            await data_sync.run_sync()
        except Exception as e:
            logger.error(f"Initial sync failed (will retry): {e}")

        # Start data sync in background AFTER initial sync
        logger.info("Starting data sync background task")
        sync_task = asyncio.create_task(data_sync.start_scheduler())

        # Start subscription checker in background
        logger.info("Starting subscription checker background task")
        subscription_checker.set_bot(bot)
        subscription_task = asyncio.create_task(subscription_checker.start_scheduler())

        # Start polling
        logger.info("🤖 QazAirbot started in polling mode!")
        logger.info("Bot is ready to receive messages on Telegram")

        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    finally:
        # Cleanup
        if 'sync_task' in locals():
            sync_task.cancel()
            try:
                await sync_task
            except asyncio.CancelledError:
                pass

        if 'subscription_task' in locals():
            subscription_task.cancel()
            try:
                await subscription_task
            except asyncio.CancelledError:
                pass

        await cache.disconnect()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
