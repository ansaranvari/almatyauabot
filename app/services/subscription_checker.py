"""Background service for checking subscriptions and sending notifications"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_Distance
from geoalchemy2 import Geography
from aiogram import Bot

from app.db.database import AsyncSessionLocal
from app.db.models import Subscription, AirQualityStation, User, SafetyNetSession
from app.core.locales import get_text

logger = logging.getLogger(__name__)


class SubscriptionCheckerService:
    """Background service for checking subscriptions and sending notifications"""

    def __init__(self):
        self.bot = None

    def set_bot(self, bot: Bot):
        """Set bot instance for sending notifications"""
        self.bot = bot

    async def check_all_subscriptions(self):
        """Check all active subscriptions and send notifications"""
        if not self.bot:
            logger.error("Bot not set for subscription checker")
            return

        await check_subscriptions(self.bot)

    async def start_scheduler(self):
        """Start periodic subscription checker - runs every 15 minutes"""
        check_interval = 15 * 60  # 15 minutes for production
        logger.info(f"Starting subscription checker (runs every {check_interval // 60} minute(s))")

        while True:
            try:
                await self.check_all_subscriptions()
            except Exception as e:
                logger.error(f"Subscription check task failed: {e}", exc_info=True)

            # Wait for next check
            await asyncio.sleep(check_interval)


# Global subscription checker instance
subscription_checker = SubscriptionCheckerService()


async def check_subscriptions(bot: Bot):
    """
    Background task to check all active subscriptions and safety net sessions

    Runs every 15 minutes to check:
    1. Main subscriptions (good air transitions)
    2. Safety net sessions (bad air alerts)

    Args:
        bot: Telegram Bot instance for sending messages
    """
    logger.info("Starting subscription check...")

    async with AsyncSessionLocal() as db:
        try:
            # Check main subscriptions
            result = await db.execute(
                select(Subscription).where(Subscription.is_active == True)
            )
            subscriptions = result.scalars().all()

            logger.info(f"Found {len(subscriptions)} active subscriptions")

            for subscription in subscriptions:
                await process_subscription(db, bot, subscription)

            # Check safety net sessions
            session_result = await db.execute(
                select(SafetyNetSession).where(
                    SafetyNetSession.session_expiry > datetime.utcnow()
                )
            )
            safety_sessions = session_result.scalars().all()

            logger.info(f"Found {len(safety_sessions)} active safety net sessions")

            for session in safety_sessions:
                await process_safety_net_session(db, bot, session)

            await db.commit()
            logger.info("Subscription check completed")

        except Exception as e:
            logger.error(f"Error in subscription check: {e}", exc_info=True)
            await db.rollback()


async def process_subscription(db: AsyncSession, bot: Bot, subscription: Subscription):
    """
    Process a single subscription using Phase 1-3 logic

    Phase 1 (Filters):
        1. Expiration Check
        2. Quiet Hours Check
        3. Cooldown Check (4 hours anti-spam)

    Phase 2 (Decision):
        - Only notify if: previous_aqi > 50 AND current_aqi <= 50

    Phase 3 (Action):
        - Send clean air notification
        - Update tracking

    Args:
        db: Database session
        bot: Telegram Bot instance
        subscription: Subscription object
    """
    try:
        # PHASE 1: FILTERS (Stop immediately if...)

        # Filter 1: Expiration Check
        if subscription.expiry_date and datetime.utcnow() > subscription.expiry_date:
            logger.info(f"Subscription {subscription.id} expired")
            await send_expiration_notification(db, bot, subscription)
            subscription.is_active = False
            return

        # Filter 2: Quiet Hours Check
        current_hour = datetime.utcnow().hour
        mute_start = subscription.mute_start
        mute_end = subscription.mute_end

        # Handle wrapping hours (e.g., 23-07 means 23:00 to 07:00)
        if mute_start > mute_end:
            # Wraps around midnight
            is_quiet_time = current_hour >= mute_start or current_hour < mute_end
        else:
            # Normal range
            is_quiet_time = mute_start <= current_hour < mute_end

        if is_quiet_time:
            logger.debug(f"Subscription {subscription.id} in quiet hours (current: {current_hour}, range: {mute_start}-{mute_end})")
            return

        # Filter 3: Cooldown Check (4 hours anti-spam)
        if subscription.last_notified_at:
            hours_since_notification = (datetime.utcnow() - subscription.last_notified_at).total_seconds() / 3600
            if hours_since_notification < 4:
                logger.debug(f"Subscription {subscription.id} in cooldown (last notified {hours_since_notification:.1f}h ago)")
                return

        # PHASE 2: THE DECISION (Send or Not?)

        # Find nearest station with fresh data
        from app.services.air_quality import AirQualityService

        nearest_station = await AirQualityService.find_nearest_station(
            db,
            subscription.latitude,
            subscription.longitude,
            max_distance_km=50.0
        )

        if not nearest_station:
            logger.debug(f"No station found for subscription {subscription.id}")
            return

        current_aqi = nearest_station.aqi

        if current_aqi is None:
            logger.debug(f"Station {nearest_station.station_id} has no AQI data")
            return

        previous_aqi = subscription.last_aqi_level

        # The Condition: Was Bad/Moderate (>50) AND Is Now Good (<=50)
        if previous_aqi is not None and previous_aqi > 50 and current_aqi <= 50:
            # PHASE 3: ACTION
            logger.info(f"Good air transition for subscription {subscription.id}: {previous_aqi} -> {current_aqi}")
            await send_clean_air_notification(db, bot, subscription, nearest_station)

            # State Update
            subscription.last_notified_at = datetime.utcnow()
            subscription.last_aqi_level = current_aqi
        else:
            # No significant change -> just update previous_aqi
            subscription.last_aqi_level = current_aqi
            logger.debug(f"Subscription {subscription.id}: No transition (prev={previous_aqi}, curr={current_aqi})")

    except Exception as e:
        logger.error(f"Error processing subscription {subscription.id}: {e}", exc_info=True)


async def send_expiration_notification(db: AsyncSession, bot: Bot, subscription: Subscription):
    """
    Send expiration notification to user and deactivate subscription

    Args:
        db: Database session
        bot: Telegram Bot instance
        subscription: Subscription object
    """
    try:
        # Get user's language preference
        user_result = await db.execute(
            select(User).where(User.id == subscription.user_id)
        )
        user = user_result.scalars().first()

        if not user:
            logger.warning(f"User {subscription.user_id} not found")
            return

        lang = user.language_code or "ru"

        # Format location
        location_text = f"{subscription.latitude:.4f}, {subscription.longitude:.4f}"

        # Get notification message
        message_text = get_text(
            lang,
            "subscription_expired",
            location=location_text
        )

        # Create inline keyboard with resubscribe button
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=get_text(lang, "resubscribe_button"),
                callback_data=f"quick_subscribe:{subscription.latitude}:{subscription.longitude}"
            )]
        ])

        # Send notification
        await bot.send_message(
            chat_id=subscription.user_id,
            text=message_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        logger.info(f"Sent expiration notification to user {subscription.user_id} for subscription {subscription.id}")

    except Exception as e:
        logger.error(f"Error sending expiration notification to user {subscription.user_id}: {e}", exc_info=True)


async def send_clean_air_notification(
    db: AsyncSession,
    bot: Bot,
    subscription: Subscription,
    station: AirQualityStation
):
    """
    Send clean air notification to user with safety net button

    Args:
        db: Database session
        bot: Telegram Bot instance
        subscription: Subscription object
        station: Nearest air quality station
    """
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        # Get user's language preference
        user_result = await db.execute(
            select(User).where(User.id == subscription.user_id)
        )
        user = user_result.scalars().first()

        if not user:
            logger.warning(f"User {subscription.user_id} not found")
            return

        lang = user.language_code or "ru"

        # Format location name
        location_name = station.name if station.name else f"{subscription.latitude:.4f}, {subscription.longitude:.4f}"

        # Get notification message
        message_text = get_text(
            lang,
            "clean_air_notification",
            aqi=station.aqi,
            location=location_name
        )

        # Send notification (no button needed anymore)
        await bot.send_message(
            chat_id=subscription.user_id,
            text=message_text,
            parse_mode="HTML"
        )

        logger.info(f"Sent clean air notification to user {subscription.user_id}")

        # Auto-create 4h safety net if enabled
        if subscription.auto_safety_net:
            from datetime import datetime, timedelta

            # Check if safety net session already exists
            existing_session = await db.execute(
                select(SafetyNetSession).where(
                    SafetyNetSession.subscription_id == subscription.id,
                    SafetyNetSession.session_expiry > datetime.utcnow()
                )
            )
            if existing_session.scalars().first():
                logger.info(f"Safety net already active for subscription {subscription.id}")
            else:
                # Create new 4h safety net session
                safety_net = SafetyNetSession(
                    user_id=subscription.user_id,
                    subscription_id=subscription.id,
                    start_aqi=station.aqi,
                    session_expiry=datetime.utcnow() + timedelta(hours=4)
                )
                db.add(safety_net)
                await db.commit()
                logger.info(f"Auto-created 4h safety net for subscription {subscription.id}")

    except Exception as e:
        logger.error(f"Error sending notification to user {subscription.user_id}: {e}", exc_info=True)


async def send_bad_air_notification(
    db: AsyncSession,
    bot: Bot,
    subscription: Subscription,
    station: AirQualityStation
):
    """
    Send bad air quality notification to user

    Args:
        db: Database session
        bot: Telegram Bot instance
        subscription: Subscription object
        station: Nearest air quality station
    """
    try:
        # Get user's language preference
        user_result = await db.execute(
            select(User).where(User.id == subscription.user_id)
        )
        user = user_result.scalars().first()

        if not user:
            logger.warning(f"User {subscription.user_id} not found")
            return

        lang = user.language_code or "ru"

        # Format location name
        location_name = station.name if station.name else f"{subscription.latitude:.4f}, {subscription.longitude:.4f}"

        # Get notification message
        message_text = get_text(
            lang,
            "bad_air_notification",
            aqi=station.aqi,
            location=location_name
        )

        # Send notification
        await bot.send_message(
            chat_id=subscription.user_id,
            text=message_text,
            parse_mode="HTML"
        )

        logger.info(f"Sent bad air notification to user {subscription.user_id}")

    except Exception as e:
        logger.error(f"Error sending bad air notification to user {subscription.user_id}: {e}", exc_info=True)


async def process_safety_net_session(db: AsyncSession, bot: Bot, session: SafetyNetSession):
    """
    Process a safety net session - check if air has gotten bad

    Logic:
    1. Check if expired -> delete silently
    2. Check if current_aqi > 75 OR current_aqi > (start_aqi + 40)
    3. If yes, send alert and delete session

    Args:
        db: Database session
        bot: Telegram Bot instance
        session: SafetyNetSession object
    """
    try:
        # Filter 1: Expiration Check
        if datetime.utcnow() > session.session_expiry:
            logger.debug(f"Safety net session {session.id} expired, deleting silently")
            await db.delete(session)
            return

        # Get subscription to find location
        sub_result = await db.execute(
            select(Subscription).where(Subscription.id == session.subscription_id)
        )
        subscription = sub_result.scalars().first()

        if not subscription:
            logger.warning(f"Subscription {session.subscription_id} not found for safety net session {session.id}")
            await db.delete(session)
            return

        # Find nearest station with fresh data
        from app.services.air_quality import AirQualityService

        nearest_station = await AirQualityService.find_nearest_station(
            db,
            subscription.latitude,
            subscription.longitude,
            max_distance_km=50.0
        )

        if not nearest_station:
            logger.debug(f"No station found for safety net session {session.id}")
            return

        current_aqi = nearest_station.aqi

        if current_aqi is None:
            logger.debug(f"Station {nearest_station.station_id} has no AQI data")
            return

        # Filter 2: Worsening Check
        threshold_unhealthy = 75
        spike_threshold = session.start_aqi + 40

        if current_aqi > threshold_unhealthy or current_aqi > spike_threshold:
            # ALERT! Air has gotten bad
            logger.info(f"Safety net triggered for session {session.id}: start={session.start_aqi}, current={current_aqi}")
            await send_bad_air_alert(db, bot, session, subscription, nearest_station)

            # Delete session immediately (do not alert twice)
            await db.delete(session)
        else:
            logger.debug(f"Safety net session {session.id}: AQI {current_aqi} (start={session.start_aqi}, threshold={max(threshold_unhealthy, spike_threshold)})")

    except Exception as e:
        logger.error(f"Error processing safety net session {session.id}: {e}", exc_info=True)


async def send_bad_air_alert(
    db: AsyncSession,
    bot: Bot,
    session: SafetyNetSession,
    subscription: Subscription,
    station: AirQualityStation
):
    """
    Send bad air alert to user (safety net notification)

    Args:
        db: Database session
        bot: Telegram Bot instance
        session: SafetyNetSession object
        subscription: Subscription object
        station: Nearest air quality station
    """
    try:
        # Get user's language preference
        user_result = await db.execute(
            select(User).where(User.id == session.user_id)
        )
        user = user_result.scalars().first()

        if not user:
            logger.warning(f"User {session.user_id} not found")
            return

        lang = user.language_code or "ru"

        # Format location name
        location_name = station.name if station.name else f"{subscription.latitude:.4f}, {subscription.longitude:.4f}"

        # Get notification message
        message_text = get_text(
            lang,
            "bad_air_notification",
            aqi=station.aqi,
            location=location_name
        )

        # Send priority alert
        await bot.send_message(
            chat_id=session.user_id,
            text=message_text,
            parse_mode="HTML"
        )

        logger.info(f"Sent bad air alert to user {session.user_id} (AQI {station.aqi})")

    except Exception as e:
        logger.error(f"Error sending bad air alert to user {session.user_id}: {e}", exc_info=True)
