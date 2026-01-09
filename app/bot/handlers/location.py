import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.enums import ChatAction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.services.air_quality import AirQualityService
from app.services.analytics import analytics
from app.core.locales import get_text
from app.bot.keyboards.reply import get_location_keyboard, get_main_menu_keyboard
from app.bot.keyboards.inline import get_air_quality_info_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.in_([
    "🔍 Проверить качество воздуха", "🔍 Ауа сапасын тексеру", "🔍 Check Air Quality"
]))
async def cmd_check_air(message: Message, lang: str, user_id: int, **kwargs):
    """
    Handle 'Check Air' button

    Shows onboarding for first-time users, then prompts to send location
    """
    # Track check air feature usage
    await analytics.track_event(user_id, "check_air_clicked")
    await analytics.increment_feature_usage("check_air", user_id)

    # Check if user has seen the onboarding and if they have favorites
    from app.db.models import User, FavoriteLocation
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalars().first()

        if user and not user.seen_check_onboarding:
            # Show onboarding message with inline keyboard only
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text(lang, "onboarding_button"),
                    callback_data="onboarding_check_done"
                )]
            ])

            await message.answer(
                get_text(lang, "onboarding_check_air"),
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return

        # Fetch user's favorite locations
        favorites_result = await db.execute(
            select(FavoriteLocation).where(FavoriteLocation.user_id == user_id)
        )
        favorites = favorites_result.scalars().all()

    # Regular flow - prompt for location
    await message.answer(
        get_text(lang, "send_location"),
        reply_markup=get_location_keyboard(lang, favorites=favorites)
    )


@router.callback_query(F.data == "onboarding_check_done")
async def handle_onboarding_check_done(callback: CallbackQuery, lang: str, user_id: int, **kwargs):
    """Mark check air onboarding as seen and show location prompt"""
    from app.db.models import User, FavoriteLocation

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalars().first()

        if user:
            user.seen_check_onboarding = True
            await db.commit()

        # Fetch user's favorite locations
        favorites_result = await db.execute(
            select(FavoriteLocation).where(FavoriteLocation.user_id == user_id)
        )
        favorites = favorites_result.scalars().all()

    # Show location prompt
    await callback.message.answer(
        get_text(lang, "send_location"),
        reply_markup=get_location_keyboard(lang, favorites=favorites)
    )
    await callback.answer()


async def process_air_quality_check(message: Message, bot: Bot, lang: str, user_id: int, latitude: float, longitude: float):
    """
    Process air quality check for given coordinates

    Called by both location handler and favorite button handler
    """

    async with AsyncSessionLocal() as db:
        # Find nearest station
        station = await AirQualityService.find_nearest_station(
            db, latitude, longitude, max_distance_km=50.0
        )

        if not station:
            # No station found within 50km - find nearest station regardless of distance
            nearest_anywhere = await AirQualityService.find_nearest_station(
                db, latitude, longitude, max_distance_km=10000.0  # Very large radius
            )

            if nearest_anywhere:
                # Calculate distance to nearest station
                from sqlalchemy import select, func
                from geoalchemy2.functions import ST_Distance, ST_MakePoint
                from geoalchemy2 import Geography
                from app.db.models import AirQualityStation

                user_point = func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
                distance_query = select(
                    ST_Distance(
                        AirQualityStation.location,
                        func.cast(user_point, Geography)
                    )
                ).where(AirQualityStation.id == nearest_anywhere.id)

                result = await db.execute(distance_query)
                distance_meters = result.scalar()
                distance_km = distance_meters / 1000.0

                # Enhanced error message with nearest coverage info
                error_msg = get_text(lang, "no_sensors_in_area", nearest_name=nearest_anywhere.name, distance_km=distance_km)
            else:
                # No stations at all in database
                error_msg = get_text(lang, "no_stations_found")

            await message.answer(
                error_msg,
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(lang)
            )

            # Log query even if no station found
            await AirQualityService.log_user_query(
                db, user_id, latitude, longitude, station_id=None
            )
            return

        # Calculate distance in kilometers
        # PostGIS ST_Distance returns meters for geography type
        from sqlalchemy import select, func
        from geoalchemy2.functions import ST_Distance, ST_MakePoint
        from geoalchemy2 import Geography
        from app.db.models import AirQualityStation

        user_point = func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        distance_query = select(
            ST_Distance(
                AirQualityStation.location,
                func.cast(user_point, Geography)
            )
        ).where(AirQualityStation.id == station.id)

        result = await db.execute(distance_query)
        distance_meters = result.scalar()
        distance_km = distance_meters / 1000.0

        # Check if user already has subscription or favorite for this location
        from app.db.models import Subscription, FavoriteLocation
        from geoalchemy2.functions import ST_DWithin
        from geoalchemy2 import Geography

        user_point = func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

        # Check for existing subscription within 100m
        existing_subscription = await db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
                ST_DWithin(
                    Subscription.location,
                    func.cast(user_point, Geography),
                    100
                )
            )
        )
        has_subscription = existing_subscription.scalars().first() is not None

        # Check for existing favorite within 100m
        existing_favorite = await db.execute(
            select(FavoriteLocation).where(
                FavoriteLocation.user_id == user_id,
                ST_DWithin(
                    FavoriteLocation.location,
                    func.cast(user_point, Geography),
                    100
                )
            )
        )
        has_favorite = existing_favorite.scalars().first() is not None

        # Format and send message with info buttons
        response_text = AirQualityService.format_air_quality_message(
            station, distance_km, lang
        )

        await message.answer(
            response_text,
            parse_mode="HTML",
            reply_markup=get_air_quality_info_keyboard(
                lang,
                station_id=station.id,
                lat=station.latitude,
                lon=station.longitude,
                user_lat=latitude if not (has_subscription and has_favorite) else None,
                user_lon=longitude if not (has_subscription and has_favorite) else None,
                show_subscribe=not has_subscription,
                show_favorite=not has_favorite
            )
        )

        # Restore main menu keyboard
        menu_text = get_text(lang, "main_menu_button")
        await message.answer(
            menu_text,
            reply_markup=get_main_menu_keyboard(lang)
        )

        # Log query
        await AirQualityService.log_user_query(
            db, user_id, latitude, longitude, station_id=station.station_id
        )

        logger.info(f"Sent air quality data for station {station.station_id} to user {user_id}")

        # Show hint occasionally (30% chance) to encourage subscriptions
        # Only show if user doesn't have any active subscriptions
        existing_subscriptions = await db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            )
        )
        has_any_subscription = existing_subscriptions.scalars().first() is not None

        import random
        if random.random() < 0.3 and not has_any_subscription:
            await message.answer(
                get_text(lang, "hint_after_check"),
                parse_mode="HTML"
            )


@router.message(
    F.text.startswith("⭐ ") &
    ~F.text.in_(["⭐ Избранные места", "⭐ Таңдаулы орындар", "⭐ Favorite Places"])
)
async def handle_favorite_button(message: Message, bot: Bot, lang: str, user_id: int, **kwargs):
    """Handle favorite location button click"""
    logger.info(f"Favorite button handler triggered with text: '{message.text}'")
    from app.db.models import FavoriteLocation

    # Extract favorite name from button text (remove "⭐ " prefix)
    favorite_name = message.text[2:].strip()
    logger.info(f"Looking for favorite with name: '{favorite_name}'")

    async with AsyncSessionLocal() as db:
        # Find the favorite location
        result = await db.execute(
            select(FavoriteLocation).where(
                FavoriteLocation.user_id == user_id,
                FavoriteLocation.name == favorite_name
            )
        )
        favorite = result.scalars().first()

        if not favorite:
            await message.answer(
                get_text(lang, "error_occurred"),
                reply_markup=get_main_menu_keyboard(lang)
            )
            return

        # Use the favorite's coordinates
        latitude = favorite.latitude
        longitude = favorite.longitude

    logger.info(f"User {user_id} selected favorite '{favorite_name}': {latitude}, {longitude}")

    # Show typing indicator (try-catch to handle potential errors)
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    except Exception as e:
        logger.warning(f"Could not send typing action: {e}")

    # Process the location (same as regular location handler)
    await process_air_quality_check(message, bot, lang, user_id, latitude, longitude)


@router.message(F.location)
async def handle_location(message: Message, bot: Bot, lang: str, user_id: int, **kwargs):
    """
    Handle user's location

    Finds nearest station and returns air quality data
    """
    location = message.location

    if not location:
        await message.answer(
            get_text(lang, "invalid_location"),
            reply_markup=get_main_menu_keyboard(lang)
        )
        return

    latitude = location.latitude
    longitude = location.longitude

    logger.info(f"User {user_id} requesting air quality for: {latitude}, {longitude}")

    # Show typing indicator
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # Process the location
    await process_air_quality_check(message, bot, lang, user_id, latitude, longitude)
