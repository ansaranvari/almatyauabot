"""
Webhook monitoring service to ensure webhook stays configured

This service periodically checks if the webhook is still set on Telegram's servers
and automatically re-sets it if it gets cleared for any reason.
"""
import asyncio
import logging
from aiogram import Bot
import httpx

logger = logging.getLogger(__name__)


class WebhookMonitor:
    """Monitor and maintain webhook configuration"""

    def __init__(self):
        self.bot: Bot = None
        self.webhook_url: str = None
        self.bot_token: str = None
        self.is_running = False

    def configure(self, bot: Bot, webhook_url: str, bot_token: str):
        """Configure the monitor with bot instance and webhook URL"""
        self.bot = bot
        self.webhook_url = webhook_url
        self.bot_token = bot_token

    async def check_and_fix_webhook(self):
        """Check if webhook is set, and fix it if not"""
        try:
            # Use direct API call to avoid caching
            verify_url = f"https://api.telegram.org/bot{self.bot_token}/getWebhookInfo"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(verify_url)
                webhook_data = response.json()
                actual_url = webhook_data.get("result", {}).get("url", "")

                if actual_url != self.webhook_url:
                    logger.warning(
                        f"⚠️ Webhook mismatch detected! Expected: {self.webhook_url}, Got: {actual_url}"
                    )
                    logger.info("Attempting to restore webhook...")

                    # Re-set the webhook
                    result = await self.bot.set_webhook(
                        url=self.webhook_url,
                        drop_pending_updates=False  # Don't drop pending updates
                    )

                    # Verify it was set
                    await asyncio.sleep(1)
                    response = await client.get(verify_url)
                    webhook_data = response.json()
                    new_url = webhook_data.get("result", {}).get("url", "")

                    if new_url == self.webhook_url:
                        logger.info(f"✅ Webhook restored successfully: {self.webhook_url}")
                    else:
                        logger.error(f"❌ Failed to restore webhook. Got: {new_url}")
                else:
                    logger.debug(f"✓ Webhook OK: {actual_url}")

        except Exception as e:
            logger.error(f"Webhook monitoring check failed: {e}", exc_info=True)

    async def start_monitor(self):
        """Start periodic webhook monitoring - checks every 5 minutes"""
        check_interval = 5 * 60  # 5 minutes
        logger.info(f"Starting webhook monitor (checks every {check_interval // 60} minutes)")
        self.is_running = True

        # Run first check immediately on startup (don't wait 5 minutes)
        logger.info("Running immediate webhook check on startup...")
        try:
            await self.check_and_fix_webhook()
        except Exception as e:
            logger.error(f"Initial webhook check failed: {e}", exc_info=True)

        while self.is_running:
            # Wait for next check
            await asyncio.sleep(check_interval)

            try:
                await self.check_and_fix_webhook()
            except Exception as e:
                logger.error(f"Webhook monitor task failed: {e}", exc_info=True)

    def stop(self):
        """Stop the monitoring loop"""
        self.is_running = False
        logger.info("Webhook monitor stopped")


# Global webhook monitor instance
webhook_monitor = WebhookMonitor()
