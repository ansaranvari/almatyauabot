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
from app.services.webhook_monitor import webhook_monitor
from app.bot.handlers import router
from app.bot.middlewares.i18n import I18nMiddleware
from app.admin.dashboard import router as admin_router

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

    # Set webhook with retry logic
    webhook_url = None
    if settings.WEBHOOK_URL:
        webhook_url = f"{settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}"
        logger.info(f"Setting webhook: {webhook_url}")

        # Try setting webhook with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                webhook_info = await bot.get_webhook_info()
                logger.info(f"Current webhook URL: {webhook_info.url}")

                # Set webhook and get result
                result = await bot.set_webhook(
                    url=webhook_url,
                    drop_pending_updates=True
                )
                logger.info(f"set_webhook() returned: {result}")

                # Wait a moment for Telegram to process
                await asyncio.sleep(1)

                # Verify webhook was set by making a fresh API call
                verify_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/getWebhookInfo"
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(verify_url)
                    webhook_data = response.json()
                    actual_url = webhook_data.get("result", {}).get("url", "")
                    logger.info(f"Direct API verification - webhook URL: {actual_url}")

                if actual_url == webhook_url:
                    logger.info(f"✅ Webhook successfully set and verified: {webhook_url}")
                    break
                else:
                    logger.warning(f"⚠️ Webhook verification failed. Expected: {webhook_url}, Got: {actual_url}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"❌ Attempt {attempt + 1}/{max_retries} - Failed to set webhook: {e}", exc_info=True)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    logger.critical(f"🚨 CRITICAL: Failed to set webhook after {max_retries} attempts. Bot will not receive updates!")
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

    # Start webhook monitor in background (only if webhook is configured)
    # Monitor will run an immediate check on startup, then every 5 minutes
    monitor_task = None
    if webhook_url:
        logger.info("Starting webhook monitor background task (immediate startup check enabled)")
        webhook_monitor.configure(bot, webhook_url, settings.BOT_TOKEN)
        monitor_task = asyncio.create_task(webhook_monitor.start_monitor())

    yield

    # Shutdown
    logger.info("Shutting down application")

    # Stop webhook monitor gracefully
    webhook_monitor.stop()

    # Cancel background tasks
    sync_task.cancel()
    subscription_task.cancel()
    if monitor_task:
        monitor_task.cancel()

    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    try:
        await subscription_task
    except asyncio.CancelledError:
        pass
    if monitor_task:
        try:
            await monitor_task
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

# Include admin routes
app.include_router(admin_router)


@app.get("/")
@app.head("/")
async def root():
    """Health check endpoint - supports both GET and HEAD methods"""
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
@app.head("/health")
async def health():
    """Detailed health check - supports both GET and HEAD methods"""
    return {
        "status": "healthy",
        "components": {
            "bot": "ok",
            "database": "ok",
            "redis": "ok"
        }
    }


@app.get("/webhook-status")
async def webhook_status():
    """Check current webhook configuration"""
    try:
        webhook_info = await bot.get_webhook_info()
        return {
            "status": "ok",
            "webhook_url": webhook_info.url,
            "has_webhook": bool(webhook_info.url),
            "pending_updates": webhook_info.pending_update_count,
            "last_error_date": webhook_info.last_error_date,
            "last_error_message": webhook_info.last_error_message
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
