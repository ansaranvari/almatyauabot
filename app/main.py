import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager

    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting QazAirbot application")

    # Initialize database
    logger.info("Initializing database")
    await init_db()

    # Connect to Redis
    logger.info("Connecting to Redis")
    await cache.connect()

    # Set webhook
    if settings.WEBHOOK_URL:
        webhook_url = f"{settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}"
        logger.info(f"Setting webhook: {webhook_url}")
        await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True
        )
    else:
        logger.warning("WEBHOOK_URL not set, webhook not configured")

    # Start data sync in background
    logger.info("Starting data sync background task")
    sync_task = asyncio.create_task(data_sync.start_scheduler())

    # Run initial sync
    logger.info("Running initial data sync")
    try:
        await data_sync.run_sync()
    except Exception as e:
        logger.error(f"Initial sync failed: {e}")

    # Start subscription checker in background
    logger.info("Starting subscription checker background task")
    subscription_checker.set_bot(bot)
    subscription_task = asyncio.create_task(subscription_checker.start_scheduler())

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Cancel background tasks
    sync_task.cancel()
    subscription_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    try:
        await subscription_task
    except asyncio.CancelledError:
        pass

    # Delete webhook
    await bot.delete_webhook(drop_pending_updates=True)

    # Disconnect from Redis
    await cache.disconnect()

    # Close bot session
    await bot.session.close()

    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="QazAirbot",
    description="Multi-language Air Quality Monitoring Telegram Bot",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "QazAirbot",
        "version": "0.1.0"
    }


@app.post(settings.WEBHOOK_PATH)
async def webhook(request: Request) -> Response:
    """
    Webhook endpoint for receiving Telegram updates

    Args:
        request: FastAPI request object

    Returns:
        Response with status 200
    """
    try:
        # Parse update
        update_data = await request.json()
        update = Update(**update_data)

        # Process update
        await dp.feed_update(bot, update)

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Error processing webhook update: {e}")
        return Response(status_code=500)


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "components": {
            "bot": "ok",
            "database": "ok",
            "redis": "ok"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
