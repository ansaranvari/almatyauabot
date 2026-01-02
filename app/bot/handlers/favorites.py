"""Handlers for favorite locations"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from geoalchemy2.functions import ST_MakePoint

from app.db.database import AsyncSessionLocal
from app.db.models import FavoriteLocation
from app.core.locales import get_text
from app.bot.keyboards.reply import get_main_menu_keyboard
from app.services.air_quality import AirQualityService

router = Router()
logger = logging.getLogger(__name__)


class FavoriteStates(StatesGroup):
    """FSM states for favorite flow"""
    entering_name = State()


@router.message(F.text.in_([
    "⭐ Избранные места", "⭐ Таңдаулы орындар"
]))
async def cmd_my_favorites(message: Message, lang: str, user_id: int, **kwargs):
    """Show user's favorite locations with quick check buttons"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FavoriteLocation).where(FavoriteLocation.user_id == user_id)
        )
        favorites = result.scalars().all()

        if not favorites:
            await message.answer(
                get_text(lang, "no_favorites"),
                reply_markup=get_main_menu_keyboard(lang)
            )
            return

        # Format favorites list
        text = "⭐ <b>" + ("Избранные места:" if lang == "ru" else "Таңдаулы орындар:") + "</b>\n\n"

        buttons = []
        for i, fav in enumerate(favorites, 1):
            text += f"{i}. {fav.name}\n"

            # Quick check button
            check_text = "🔍 Проверить" if lang == "ru" else "🔍 Тексеру"
            delete_text = "🗑 Удалить" if lang == "ru" else "🗑 Өшіру"

            buttons.append([
                InlineKeyboardButton(
                    text=f"{check_text} {fav.name}",
                    callback_data=f"check_fav:{fav.id}"
                ),
                InlineKeyboardButton(
                    text=f"{delete_text}",
                    callback_data=f"del_fav:{fav.id}"
                )
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("check_fav:"))
async def handle_check_favorite(callback: CallbackQuery, lang: str, user_id: int, **kwargs):
    """Check air quality for a favorite location"""
    try:
        # Answer callback immediately to show loading indicator
        loading_text = "🔍 Загрузка..." if lang == "ru" else "🔍 Жүктеу..."
        await callback.answer(loading_text)

        favorite_id = int(callback.data.split(":")[1])

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(FavoriteLocation).where(
                    FavoriteLocation.id == favorite_id,
                    FavoriteLocation.user_id == user_id
                )
            )
            favorite = result.scalars().first()

            if not favorite:
                await callback.answer("❌ Not found", show_alert=True)
                return

            # Find nearest station
            station = await AirQualityService.find_nearest_station(
                db, favorite.latitude, favorite.longitude, max_distance_km=50.0
            )

            if not station:
                await callback.message.answer(
                    get_text(lang, "no_stations_found"),
                    reply_markup=get_main_menu_keyboard(lang)
                )
                return

            # Calculate distance
            from geoalchemy2.functions import ST_Distance
            from geoalchemy2 import Geography
            from app.db.models import AirQualityStation

            user_point = func.ST_SetSRID(ST_MakePoint(favorite.longitude, favorite.latitude), 4326)
            distance_query = select(
                ST_Distance(
                    AirQualityStation.location,
                    func.cast(user_point, Geography)
                )
            ).where(AirQualityStation.id == station.id)

            result = await db.execute(distance_query)
            distance_meters = result.scalar()
            distance_km = distance_meters / 1000.0

            # Format message with favorite name
            from app.bot.keyboards.inline import get_air_quality_info_keyboard

            response_text = f"⭐ <b>{favorite.name}</b>\n\n"
            response_text += AirQualityService.format_air_quality_message(
                station, distance_km, lang
            )

            await callback.message.answer(
                response_text,
                parse_mode="HTML",
                reply_markup=get_air_quality_info_keyboard(
                    lang,
                    station_id=station.id,
                    lat=station.latitude,
                    lon=station.longitude
                    # Don't pass user_lat/user_lon - already a favorite, no need for add/subscribe buttons
                )
            )

            # Restore main menu keyboard
            menu_text = "📋 Главное меню" if lang == "ru" else "📋 Басты мәзір"
            await callback.message.answer(
                menu_text,
                reply_markup=get_main_menu_keyboard(lang)
            )

            # Log query
            await AirQualityService.log_user_query(
                db, user_id, favorite.latitude, favorite.longitude, station_id=station.station_id
            )

    except Exception as e:
        logger.error(f"Error checking favorite: {e}", exc_info=True)
        await callback.answer("❌ Error", show_alert=True)


@router.callback_query(F.data.startswith("del_fav:"))
async def handle_delete_favorite(callback: CallbackQuery, lang: str, user_id: int, **kwargs):
    """Delete a favorite location"""
    try:
        favorite_id = int(callback.data.split(":")[1])

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(FavoriteLocation).where(
                    FavoriteLocation.id == favorite_id,
                    FavoriteLocation.user_id == user_id
                )
            )
            favorite = result.scalars().first()

            if not favorite:
                await callback.answer("❌ Not found", show_alert=True)
                return

            await db.delete(favorite)
            await db.commit()

            await callback.message.edit_text(
                get_text(lang, "favorite_deleted"),
                parse_mode="HTML"
            )
            await callback.answer()

    except Exception as e:
        logger.error(f"Error deleting favorite: {e}", exc_info=True)
        await callback.answer("❌ Error", show_alert=True)


@router.callback_query(F.data.startswith("add_favorite:"))
async def handle_add_favorite(callback: CallbackQuery, state: FSMContext, lang: str, **kwargs):
    """Start adding a favorite - ask for name"""
    try:
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("❌ Error", show_alert=True)
            return

        latitude = float(parts[1])
        longitude = float(parts[2])

        # Store location in state
        await state.update_data(fav_lat=latitude, fav_lon=longitude)
        await state.set_state(FavoriteStates.entering_name)

        await callback.message.answer(
            get_text(lang, "enter_favorite_name"),
            parse_mode="HTML"
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error starting add favorite: {e}", exc_info=True)
        await callback.answer("❌ Error", show_alert=True)


@router.message(FavoriteStates.entering_name)
async def handle_favorite_name(message: Message, state: FSMContext, lang: str, user_id: int, **kwargs):
    """Save favorite with user-provided name"""
    name = message.text.strip()

    if len(name) > 100:
        await message.answer(
            get_text(lang, "favorite_name_too_long"),
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    latitude = data.get("fav_lat")
    longitude = data.get("fav_lon")

    async with AsyncSessionLocal() as db:
        # Check if favorite already exists
        from geoalchemy2 import Geography
        user_point = func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        existing = await db.execute(
            select(FavoriteLocation).where(
                FavoriteLocation.user_id == user_id,
                func.ST_DWithin(
                    FavoriteLocation.location,
                    func.cast(user_point, Geography),
                    100  # Within 100 meters
                )
            )
        )

        if existing.scalars().first():
            await message.answer(
                get_text(lang, "favorite_already_exists"),
                reply_markup=get_main_menu_keyboard(lang)
            )
            await state.clear()
            return

        # Create favorite - use same approach as subscriptions
        favorite = FavoriteLocation(
            user_id=user_id,
            name=name,
            location=func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
            latitude=latitude,
            longitude=longitude
        )

        db.add(favorite)
        await db.commit()

        await message.answer(
            get_text(lang, "favorite_added"),
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(lang)
        )

    await state.clear()
