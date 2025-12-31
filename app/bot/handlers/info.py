"""Handlers for air quality info callbacks"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from app.core.locales import get_text
from app.db.database import AsyncSessionLocal
from app.db.models import AirQualityStation
from app.services.chart_generator import chart_generator
from app.utils.redis_client import redis_cache
from sqlalchemy import select

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("info:pm25"))
async def info_pm25_callback(callback: CallbackQuery, lang: str, **kwargs):
    """Handle PM2.5 info request"""
    title = get_text(lang, "pm25_info_title")
    description = get_text(lang, "pm25_info_description")
    ranges = get_text(lang, "pm25_info_ranges")

    message = f"{title}\n\n{description}\n{ranges}"

    # Extract station_id from callback data if present
    parts = callback.data.split(":")
    station_id = parts[2] if len(parts) > 2 else None

    # Add return button with station_id
    return_button_text = "⬇️ Вернуться к отчету о воздухе" if lang == "ru" else "⬇️ Ауа есебіне оралу"
    callback_data = f"return_to_report:{station_id}" if station_id else "return_to_report"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=return_button_text,
            callback_data=callback_data
        )]
    ])

    await callback.message.answer(message, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("info:pm10"))
async def info_pm10_callback(callback: CallbackQuery, lang: str, **kwargs):
    """Handle PM10 info request"""
    title = get_text(lang, "pm10_info_title")
    description = get_text(lang, "pm10_info_description")
    ranges = get_text(lang, "pm10_info_ranges")

    message = f"{title}\n\n{description}\n{ranges}"

    # Extract station_id from callback data if present
    parts = callback.data.split(":")
    station_id = parts[2] if len(parts) > 2 else None

    # Add return button with station_id
    return_button_text = "⬇️ Вернуться к отчету о воздухе" if lang == "ru" else "⬇️ Ауа есебіне оралу"
    callback_data = f"return_to_report:{station_id}" if station_id else "return_to_report"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=return_button_text,
            callback_data=callback_data
        )]
    ])

    await callback.message.answer(message, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("info:pm1"))
async def info_pm1_callback(callback: CallbackQuery, lang: str, **kwargs):
    """Handle PM1.0 info request"""
    title = get_text(lang, "pm1_info_title")
    description = get_text(lang, "pm1_info_description")
    ranges = get_text(lang, "pm1_info_ranges")

    message = f"{title}\n\n{description}\n{ranges}"

    # Extract station_id from callback data if present
    parts = callback.data.split(":")
    station_id = parts[2] if len(parts) > 2 else None

    # Add return button with station_id
    return_button_text = "⬇️ Вернуться к отчету о воздухе" if lang == "ru" else "⬇️ Ауа есебіне оралу"
    callback_data = f"return_to_report:{station_id}" if station_id else "return_to_report"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=return_button_text,
            callback_data=callback_data
        )]
    ])

    await callback.message.answer(message, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("info:aqi"))
async def info_aqi_callback(callback: CallbackQuery, lang: str, **kwargs):
    """Handle AQI info request"""
    title = get_text(lang, "aqi_info_title")
    description = get_text(lang, "aqi_info_description")
    ranges = get_text(lang, "aqi_info_ranges")

    message = f"{title}\n\n{description}\n{ranges}"

    # Extract station_id from callback data if present
    parts = callback.data.split(":")
    station_id = parts[2] if len(parts) > 2 else None

    # Add return button with station_id
    return_button_text = "⬇️ Вернуться к отчету о воздухе" if lang == "ru" else "⬇️ Ауа есебіне оралу"
    callback_data = f"return_to_report:{station_id}" if station_id else "return_to_report"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=return_button_text,
            callback_data=callback_data
        )]
    ])

    await callback.message.answer(message, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("return_to_report"))
async def return_to_report_callback(callback: CallbackQuery, lang: str, user_id: int, **kwargs):
    """Handle return to report button click - re-send air quality report"""
    try:
        # Extract station_id from callback data
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer("❌ Error", show_alert=True)
            return

        station_id = int(parts[1])

        # Fetch station from database
        from app.db.database import AsyncSessionLocal
        from app.db.models import AirQualityStation
        from app.services.air_quality import AirQualityService
        from app.bot.keyboards.inline import get_air_quality_info_keyboard
        from sqlalchemy import select, func

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AirQualityStation).where(AirQualityStation.id == station_id)
            )
            station = result.scalar_one_or_none()

            if not station:
                await callback.answer("❌ Станция не найдена", show_alert=True)
                return

            # Check if user already has subscription or favorite for this location
            from app.db.models import Subscription, FavoriteLocation
            from geoalchemy2.functions import ST_DWithin, ST_MakePoint
            from geoalchemy2 import Geography

            user_point = func.ST_SetSRID(ST_MakePoint(station.longitude, station.latitude), 4326)

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
            has_subscription = existing_subscription.scalar_one_or_none() is not None

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
            has_favorite = existing_favorite.scalar_one_or_none() is not None

            # Format and send air quality message (same as original)
            response_text = AirQualityService.format_air_quality_message(
                station, 0, lang  # distance is 0 since we're just re-displaying
            )

            await callback.message.answer(
                response_text,
                parse_mode="HTML",
                reply_markup=get_air_quality_info_keyboard(
                    lang,
                    station_id=station.id,
                    lat=station.latitude,
                    lon=station.longitude,
                    user_lat=station.latitude if not (has_subscription and has_favorite) else None,
                    user_lon=station.longitude if not (has_subscription and has_favorite) else None,
                    show_subscribe=not has_subscription,
                    show_favorite=not has_favorite
                )
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error returning to report: {e}", exc_info=True)
        await callback.answer(
            "❌ Произошла ошибка" if lang == "ru" else "❌ Қате орын алды",
            show_alert=True
        )


@router.callback_query(F.data.startswith("show_station_loc:"))
async def show_station_location_callback(callback: CallbackQuery, lang: str, **kwargs):
    """Handle show station location request from air quality check"""
    try:
        # Extract station coordinates from callback data
        # Format: show_station_loc:station_id:lat:lon
        parts = callback.data.split(":")
        if len(parts) != 4:
            await callback.answer("❌ Error", show_alert=True)
            return

        station_id = int(parts[1])
        lat = float(parts[2])
        lon = float(parts[3])

        # Send station location on map
        await callback.message.answer_location(
            latitude=lat,
            longitude=lon
        )

        # Fetch station info from database to show name and current AQI
        from app.db.database import AsyncSessionLocal
        from app.db.models import AirQualityStation
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AirQualityStation).where(AirQualityStation.id == station_id)
            )
            station = result.scalar_one_or_none()

            if station:
                station_info = f"📍 <b>{station.name}</b>"

                await callback.message.answer(
                    station_info,
                    parse_mode="HTML"
                )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing station location: {e}", exc_info=True)
        await callback.answer(
            "❌ Произошла ошибка" if lang == "ru" else "❌ Қате орын алды",
            show_alert=True
        )


@router.callback_query(F.data.startswith("chart:24h"))
async def chart_24h_callback(callback: CallbackQuery, lang: str, user_id: int, **kwargs):
    """Handle 24-hour chart request"""
    try:
        # Rate limiting: 3 chart requests per minute per user
        rate_limit_key = f"rate_limit:chart:{user_id}"
        request_count = await redis_cache.incr(rate_limit_key, expire=60)

        if request_count and request_count > 3:
            await callback.answer(
                "⏱ Слишком много запросов. Пожалуйста, подождите минуту."
                if lang == "ru"
                else "⏱ Тым көп сұраныс. Бір минут күтіңіз.",
                show_alert=True
            )
            return

        # Extract station_id from callback data
        parts = callback.data.split(":")
        if len(parts) < 3:
            await callback.answer("❌ Error", show_alert=True)
            return

        station_id = int(parts[2])

        # Show "generating" message
        await callback.answer(
            "📊 Генерирую график..." if lang == "ru" else "📊 График құрамын...",
            show_alert=False
        )

        # Fetch station info
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AirQualityStation).where(AirQualityStation.id == station_id)
            )
            station = result.scalar_one_or_none()

            if not station:
                await callback.message.answer(
                    "❌ Станция не найдена" if lang == "ru" else "❌ Станция табылмады"
                )
                return

            # Generate chart
            chart_bytes = await chart_generator.generate_24h_chart(
                db, station.station_id, station.name, lang
            )

            if chart_bytes:
                # Send chart as photo
                photo = BufferedInputFile(chart_bytes, filename=f"chart_{station.station_id}.png")
                caption = (
                    f"📊 График качества воздуха за 24 часа\n📍 {station.name}"
                    if lang == "ru"
                    else f"📊 Ауа сапасының 24 сағаттық графигі\n📍 {station.name}"
                )
                await callback.message.answer_photo(
                    photo=photo,
                    caption=caption
                )
            else:
                # Not enough data
                await callback.message.answer(
                    "❌ Недостаточно данных для построения графика. Попробуйте позже."
                    if lang == "ru"
                    else "❌ Графикті құру үшін деректер жеткіліксіз. Кейінірек қайталап көріңіз."
                )

    except Exception as e:
        logger.error(f"Error generating 24h chart: {e}", exc_info=True)
        await callback.answer(
            "❌ Ошибка при создании графика" if lang == "ru" else "❌ График жасауда қате",
            show_alert=True
        )
