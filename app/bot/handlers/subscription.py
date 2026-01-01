"""Handlers for air quality subscriptions"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_MakePoint, ST_DWithin
from geoalchemy2 import Geography

from app.db.database import AsyncSessionLocal
from app.db.models import Subscription, SafetyNetSession
from app.core.locales import get_text
from app.bot.keyboards.reply import get_location_keyboard, get_main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)


class SubscriptionStates(StatesGroup):
    """FSM states for subscription flow"""
    waiting_for_location = State()
    choosing_duration = State()
    choosing_quiet_hours = State()
    entering_custom_hours = State()
    # Edit states
    editing_duration = State()
    editing_quiet_hours = State()
    editing_custom_hours = State()


@router.callback_query(F.data.startswith("quick_subscribe:"))
async def handle_quick_subscribe(callback: CallbackQuery, state: FSMContext, lang: str, user_id: int, **kwargs):
    """
    Handle quick subscribe from air quality check

    Shows onboarding for first-time users, then starts subscription flow with pre-filled location
    """
    try:
        # Extract coordinates from callback data
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("❌ Error", show_alert=True)
            return

        latitude = float(parts[1])
        longitude = float(parts[2])

        # Check if user has seen subscription onboarding
        from app.db.models import User
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalars().first()

            if user and not user.seen_subscribe_onboarding:
                # Store location for after onboarding
                await state.update_data(latitude=latitude, longitude=longitude)

                # Show onboarding message with inline keyboard only
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_text(lang, "onboarding_button"),
                        callback_data="onboarding_subscribe_quick_done"
                    )]
                ])

                await callback.message.answer(
                    get_text(lang, "onboarding_subscribe"),
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                await callback.answer()
                return

            # Check if subscription already exists within 100m radius
            user_point = func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

            existing_sub = await db.execute(
                select(Subscription).where(
                    Subscription.user_id == user_id,
                    Subscription.is_active == True,
                    ST_DWithin(
                        Subscription.location,
                        func.cast(user_point, Geography),
                        100  # 100 meters
                    )
                )
            )

            if existing_sub.scalars().first():
                await callback.answer(
                    get_text(lang, "subscription_exists"),
                    show_alert=True
                )
                return

        # Store location and start subscription flow
        await state.update_data(latitude=latitude, longitude=longitude)
        await state.set_state(SubscriptionStates.choosing_duration)

        # Show duration selection
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=get_text(lang, "duration_today"),
                callback_data="duration:today"
            )],
            [InlineKeyboardButton(
                text=get_text(lang, "duration_24h"),
                callback_data="duration:24h"
            )],
            [InlineKeyboardButton(
                text=get_text(lang, "duration_3d"),
                callback_data="duration:3d"
            )],
            [InlineKeyboardButton(
                text=get_text(lang, "duration_7d"),
                callback_data="duration:7d"
            )],
            [InlineKeyboardButton(
                text=get_text(lang, "duration_forever"),
                callback_data="duration:forever"
            )],
        ])

        await callback.message.answer(
            get_text(lang, "duration_prompt"),
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in quick subscribe: {e}", exc_info=True)
        await callback.answer(
            "❌ Произошла ошибка" if lang == "ru" else "❌ Қате орын алды",
            show_alert=True
        )


@router.message(F.text.in_([
    "🔔 Подписаться на чистый воздух", "🔔 Таза ауаға жазылу"
]))
async def cmd_subscribe(message: Message, state: FSMContext, lang: str, user_id: int, **kwargs):
    """
    Handle subscription button click

    Shows onboarding for first-time users, then prompts to send location
    """
    # Check if user has seen the onboarding
    from app.db.models import User
    from sqlalchemy import select
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalars().first()

        if user and not user.seen_subscribe_onboarding:
            # Show onboarding message with inline keyboard only
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text(lang, "onboarding_button"),
                    callback_data="onboarding_subscribe_done"
                )]
            ])

            await message.answer(
                get_text(lang, "onboarding_subscribe"),
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return

    # Regular flow - prompt for location
    await state.set_state(SubscriptionStates.waiting_for_location)

    await message.answer(
        get_text(lang, "subscribe_prompt"),
        reply_markup=get_location_keyboard(lang)
    )


@router.callback_query(F.data == "onboarding_subscribe_done")
async def handle_onboarding_subscribe_done(callback: CallbackQuery, state: FSMContext, lang: str, user_id: int, **kwargs):
    """Mark subscribe onboarding as seen and show location prompt"""
    from app.db.models import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalars().first()

        if user:
            user.seen_subscribe_onboarding = True
            await db.commit()

    # Set state and show location prompt
    await state.set_state(SubscriptionStates.waiting_for_location)

    await callback.message.answer(
        get_text(lang, "subscribe_prompt"),
        reply_markup=get_location_keyboard(lang)
    )
    await callback.answer()


@router.callback_query(F.data == "onboarding_subscribe_quick_done")
async def handle_onboarding_subscribe_quick_done(callback: CallbackQuery, state: FSMContext, lang: str, user_id: int, **kwargs):
    """Mark subscribe onboarding as seen and continue quick subscribe flow with stored location"""
    from app.db.models import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalars().first()

        if user:
            user.seen_subscribe_onboarding = True
            await db.commit()

    # Get stored location from state
    user_data = await state.get_data()
    latitude = user_data.get("latitude")
    longitude = user_data.get("longitude")

    if not latitude or not longitude:
        await callback.answer("❌ Error: Location not found", show_alert=True)
        return

    # Set state for duration selection
    await state.set_state(SubscriptionStates.choosing_duration)

    # Show duration selection
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_text(lang, "duration_today"),
            callback_data="duration:today"
        )],
        [InlineKeyboardButton(
            text=get_text(lang, "duration_24h"),
            callback_data="duration:24h"
        )],
        [InlineKeyboardButton(
            text=get_text(lang, "duration_3d"),
            callback_data="duration:3d"
        )],
        [InlineKeyboardButton(
            text=get_text(lang, "duration_7d"),
            callback_data="duration:7d"
        )],
        [InlineKeyboardButton(
            text=get_text(lang, "duration_forever"),
            callback_data="duration:forever"
        )],
    ])

    await callback.message.answer(
        get_text(lang, "duration_prompt"),
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(SubscriptionStates.waiting_for_location, F.location)
async def handle_subscription_location(message: Message, state: FSMContext, lang: str, user_id: int, **kwargs):
    """
    Handle location for subscription - Step A

    Stores location temporarily and moves to duration selection
    """
    location = message.location

    if not location:
        await message.answer(
            get_text(lang, "invalid_location"),
            reply_markup=get_main_menu_keyboard(lang)
        )
        await state.clear()
        return

    latitude = location.latitude
    longitude = location.longitude

    async with AsyncSessionLocal() as db:
        # Check if subscription already exists within 100m radius
        user_point = func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

        existing_sub = await db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
                ST_DWithin(
                    Subscription.location,
                    func.cast(user_point, Geography),
                    100  # 100 meters
                )
            )
        )

        if existing_sub.scalars().first():
            await message.answer(
                get_text(lang, "subscription_exists"),
                reply_markup=get_main_menu_keyboard(lang)
            )
            await state.clear()
            return

    # Store location temporarily
    await state.update_data(latitude=latitude, longitude=longitude)
    await state.set_state(SubscriptionStates.choosing_duration)

    # Show duration selection
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_text(lang, "duration_today"),
            callback_data="duration:today"
        )],
        [InlineKeyboardButton(
            text=get_text(lang, "duration_24h"),
            callback_data="duration:24h"
        )],
        [InlineKeyboardButton(
            text=get_text(lang, "duration_3d"),
            callback_data="duration:3d"
        )],
        [InlineKeyboardButton(
            text=get_text(lang, "duration_7d"),
            callback_data="duration:7d"
        )],
        [InlineKeyboardButton(
            text=get_text(lang, "duration_forever"),
            callback_data="duration:forever"
        )],
    ])

    await message.answer(
        get_text(lang, "duration_prompt"),
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("duration:"), SubscriptionStates.choosing_duration)
async def handle_duration_selection(callback: CallbackQuery, state: FSMContext, lang: str, **kwargs):
    """
    Handle duration selection - Step B

    Stores duration and moves to quiet hours configuration
    """
    from datetime import datetime, timedelta

    duration_choice = callback.data.split(":")[1]  # "today", "24h", "3d", "7d", or "forever"

    # Calculate expiry_date
    if duration_choice == "today":
        # Until end of today (23:59:59)
        now = datetime.utcnow()
        expiry_date = datetime(now.year, now.month, now.day, 23, 59, 59)
    elif duration_choice == "24h":
        expiry_date = datetime.utcnow() + timedelta(days=1)
    elif duration_choice == "3d":
        expiry_date = datetime.utcnow() + timedelta(days=3)
    elif duration_choice == "7d":
        expiry_date = datetime.utcnow() + timedelta(days=7)
    else:  # forever
        expiry_date = None

    # Store duration choice
    await state.update_data(expiry_date=expiry_date, duration_choice=duration_choice)
    await state.set_state(SubscriptionStates.choosing_quiet_hours)

    # Show quiet hours prompt
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_text(lang, "quiet_hours_yes"),
            callback_data="quiet:default"
        )],
        [InlineKeyboardButton(
            text=get_text(lang, "quiet_hours_change"),
            callback_data="quiet:custom"
        )],
    ])

    await callback.message.edit_text(
        get_text(lang, "quiet_hours_prompt"),
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("quiet:"), SubscriptionStates.choosing_quiet_hours)
async def handle_quiet_hours_selection(callback: CallbackQuery, state: FSMContext, lang: str, user_id: int, **kwargs):
    """
    Handle quiet hours selection - Step C

    Either uses default (23-07) or prompts for custom hours
    """
    quiet_choice = callback.data.split(":")[1]  # "default" or "custom"

    if quiet_choice == "default":
        # Use default quiet hours (23-07)
        await state.update_data(mute_start=23, mute_end=7)
        await create_subscription(callback.message, state, lang, user_id)
    else:
        # Ask for custom hours
        await state.set_state(SubscriptionStates.entering_custom_hours)
        await callback.message.edit_text(
            get_text(lang, "quiet_hours_custom"),
            parse_mode="HTML"
        )
    await callback.answer()


@router.message(SubscriptionStates.entering_custom_hours, F.text)
async def handle_custom_quiet_hours(message: Message, state: FSMContext, lang: str, user_id: int, **kwargs):
    """
    Handle custom quiet hours input

    Expects format: HH-HH (e.g., 22-08)
    """
    import re

    text = message.text.strip()
    match = re.match(r'^(\d{1,2})-(\d{1,2})$', text)

    if not match:
        await message.answer(
            get_text(lang, "quiet_hours_invalid"),
            parse_mode="HTML"
        )
        return

    start_hour = int(match.group(1))
    end_hour = int(match.group(2))

    # Validate hours (0-23)
    if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
        await message.answer(
            get_text(lang, "quiet_hours_invalid"),
            parse_mode="HTML"
        )
        return

    # Store custom hours
    await state.update_data(mute_start=start_hour, mute_end=end_hour)
    await create_subscription(message, state, lang, user_id)


async def create_subscription(message: Message, state: FSMContext, lang: str, user_id: int):
    """
    Create subscription with all collected data

    Final action after all steps completed
    """
    user_data = await state.get_data()
    latitude = user_data["latitude"]
    longitude = user_data["longitude"]
    expiry_date = user_data.get("expiry_date")
    duration_choice = user_data["duration_choice"]
    mute_start = user_data["mute_start"]
    mute_end = user_data["mute_end"]

    async with AsyncSessionLocal() as db:
        # Find nearest station to show name in confirmation
        from app.services.air_quality import AirQualityService

        station = await AirQualityService.find_nearest_station(
            db, latitude, longitude, max_distance_km=50.0
        )

        station_name = station.name if station else f"{latitude:.4f}, {longitude:.4f}"

        # Create new subscription
        subscription = Subscription(
            user_id=user_id,
            location=f'SRID=4326;POINT({longitude} {latitude})',
            latitude=latitude,
            longitude=longitude,
            expiry_date=expiry_date,
            mute_start=mute_start,
            mute_end=mute_end,
            is_active=True
        )

        db.add(subscription)
        await db.commit()

        logger.info(f"User {user_id} subscribed: lat={latitude}, lon={longitude}, duration={duration_choice}, quiet={mute_start}-{mute_end}")

        # Format duration for display
        duration_labels = {
            "today": get_text(lang, "duration_today_text"),
            "24h": get_text(lang, "duration_24h_text"),
            "3d": get_text(lang, "duration_3d_text"),
            "7d": get_text(lang, "duration_7d_text"),
            "forever": get_text(lang, "duration_forever_text")
        }

        # Format quiet hours for display
        quiet_hours_text = f"{mute_start:02d}:00 - {mute_end:02d}:00"

        await message.answer(
            get_text(lang, "subscription_saved").format(
                station_name=station_name,
                duration=duration_labels[duration_choice],
                quiet_hours=quiet_hours_text
            ),
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(lang)
        )

        # Show hint about subscription management
        await message.answer(
            get_text(lang, "hint_after_subscription"),
            parse_mode="HTML"
        )

    await state.clear()


@router.message(F.text.in_([
    "📋 Мои подписки", "📋 Менің жазылымдарым"
]))
async def cmd_my_subscriptions(message: Message, lang: str, user_id: int, **kwargs):
    """
    Show user's active subscriptions with delete buttons
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            )
        )
        subscriptions = result.scalars().all()

        if not subscriptions:
            await message.answer(
                get_text(lang, "no_subscriptions"),
                reply_markup=get_main_menu_keyboard(lang)
            )
            return

        # Format subscriptions list
        text = "📋 <b>" + ("Ваши подписки:" if lang == "ru" else "Сіздің жазылымдарыңыз:") + "</b>\n\n"

        # Create inline keyboard with delete buttons for each subscription
        buttons = []

        # Import AirQualityService to find nearest stations
        from app.services.air_quality import AirQualityService

        # Check if we need numbering (only for multiple subscriptions)
        show_numbers = len(subscriptions) > 1

        for i, sub in enumerate(subscriptions, 1):
            # Find nearest station to show location name
            nearest_station = await AirQualityService.find_nearest_station(
                db,
                sub.latitude,
                sub.longitude,
                max_distance_km=50.0
            )

            # Display station name or coordinates as fallback
            station_label = "Ближайший датчик качества воздуха:" if lang == "ru" else "Жақын ауа сапасы датчигі:"
            if nearest_station and nearest_station.name:
                location_text = f"📍 {station_label} {nearest_station.name}"
            else:
                location_text = f"📍 {sub.latitude:.4f}, {sub.longitude:.4f}"

            # Add number prefix only if multiple subscriptions
            if show_numbers:
                text += f"{i}. {location_text}\n"
            else:
                text += f"{location_text}\n"

            # Show duration
            if sub.expiry_date:
                from datetime import datetime
                remaining = sub.expiry_date - datetime.utcnow()
                hours_left = int(remaining.total_seconds() / 3600)
                if hours_left > 24:
                    days_left = hours_left // 24
                    duration_text = f"{days_left} дн." if lang == "ru" else f"{days_left} күн"
                else:
                    duration_text = f"{hours_left} ч." if lang == "ru" else f"{hours_left} с."
                duration_label = "⏰ Осталось:" if lang == "ru" else "⏰ Қалды:"
                text += f"{duration_label} {duration_text}\n"
            else:
                duration_label = "⏰ Срок:" if lang == "ru" else "⏰ Мерзімі:"
                forever_text = "Бессрочно" if lang == "ru" else "Мерзімсіз"
                text += f"{duration_label} {forever_text}\n"

            # Show quiet hours
            quiet_label = "🌙 Тихие часы:" if lang == "ru" else "🌙 Тыныш сағаттар:"
            text += f"{quiet_label} {sub.mute_start:02d}:00-{sub.mute_end:02d}:00\n"

            if sub.last_notified_at:
                time_str = sub.last_notified_at.strftime("%d.%m.%y %H:%M")
                notified = "🔔 Последнее уведомление:" if lang == "ru" else "🔔 Соңғы хабарландыру:"
                text += f"{notified} {time_str}\n"
            if sub.last_aqi_level:
                aqi_label = "💨 Последний AQI:" if lang == "ru" else "💨 Соңғы AQI:"
                text += f"{aqi_label} {sub.last_aqi_level}\n"
            text += "\n"

            # Add edit and delete buttons for this subscription
            edit_text = get_text(lang, "edit_subscription")
            delete_text = get_text(lang, "delete_subscription")
            show_station_text = "📍 Показать, где находится датчик" if lang == "ru" else "📍 Датчик қайда екенін көрсету"

            # Add number suffix only if multiple subscriptions
            if show_numbers:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{edit_text} #{i}",
                        callback_data=f"edit:{sub.id}"
                    ),
                    InlineKeyboardButton(
                        text=f"{delete_text} #{i}",
                        callback_data=f"unsub:{sub.id}"
                    )
                ])
                # Add show station button on separate row
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{show_station_text} #{i}",
                        callback_data=f"show_station:{sub.id}"
                    )
                ])
            else:
                buttons.append([
                    InlineKeyboardButton(
                        text=edit_text,
                        callback_data=f"edit:{sub.id}"
                    ),
                    InlineKeyboardButton(
                        text=delete_text,
                        callback_data=f"unsub:{sub.id}"
                    )
                ])
                # Add show station button on separate row
                buttons.append([
                    InlineKeyboardButton(
                        text=show_station_text,
                        callback_data=f"show_station:{sub.id}"
                    )
                ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("edit:"))
async def handle_edit_subscription(callback: CallbackQuery, state: FSMContext, lang: str, user_id: int, **kwargs):
    """
    Handle edit subscription button click

    Shows menu of what to edit
    """
    try:
        # Extract subscription ID from callback data
        subscription_id = int(callback.data.split(":")[1])

        async with AsyncSessionLocal() as db:
            # Get subscription
            result = await db.execute(
                select(Subscription).where(
                    Subscription.id == subscription_id,
                    Subscription.user_id == user_id  # Security check
                )
            )
            subscription = result.scalars().first()

            if not subscription:
                await callback.answer(
                    "❌ Подписка не найдена" if lang == "ru" else "❌ Жазылым табылмады",
                    show_alert=True
                )
                return

            # Store subscription ID in state
            await state.update_data(edit_subscription_id=subscription_id)

            # Send location map to show exactly where the subscription is
            await callback.message.answer_location(
                latitude=subscription.latitude,
                longitude=subscription.longitude
            )

            # Show edit menu
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text(lang, "edit_duration_button"),
                    callback_data=f"edit_menu:duration:{subscription_id}"
                )],
                [InlineKeyboardButton(
                    text=get_text(lang, "edit_quiet_hours_button"),
                    callback_data=f"edit_menu:quiet:{subscription_id}"
                )],
            ])

            await callback.message.answer(
                get_text(lang, "edit_menu_prompt"),
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await callback.answer()

    except Exception as e:
        logger.error(f"Error editing subscription for user {user_id}: {e}", exc_info=True)
        await callback.answer(
            "❌ Произошла ошибка" if lang == "ru" else "❌ Қате орын алды",
            show_alert=True
        )


@router.callback_query(F.data.startswith("edit_menu:"))
async def handle_edit_menu_selection(callback: CallbackQuery, state: FSMContext, lang: str, user_id: int, **kwargs):
    """
    Handle edit menu selection (duration or quiet hours)
    """
    try:
        parts = callback.data.split(":")
        edit_type = parts[1]  # "duration" or "quiet"
        subscription_id = int(parts[2])

        # Store subscription ID in state
        await state.update_data(edit_subscription_id=subscription_id)

        if edit_type == "duration":
            await state.set_state(SubscriptionStates.editing_duration)

            # Show duration selection
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text(lang, "duration_today"),
                    callback_data="edit_duration:today"
                )],
                [InlineKeyboardButton(
                    text=get_text(lang, "duration_24h"),
                    callback_data="edit_duration:24h"
                )],
                [InlineKeyboardButton(
                    text=get_text(lang, "duration_3d"),
                    callback_data="edit_duration:3d"
                )],
                [InlineKeyboardButton(
                    text=get_text(lang, "duration_7d"),
                    callback_data="edit_duration:7d"
                )],
                [InlineKeyboardButton(
                    text=get_text(lang, "duration_forever"),
                    callback_data="edit_duration:forever"
                )],
            ])

            await callback.message.edit_text(
                get_text(lang, "duration_prompt"),
                parse_mode="HTML",
                reply_markup=keyboard
            )

        elif edit_type == "quiet":
            await state.set_state(SubscriptionStates.editing_quiet_hours)

            # Show quiet hours prompt
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text(lang, "quiet_hours_yes"),
                    callback_data="edit_quiet_only:default"
                )],
                [InlineKeyboardButton(
                    text=get_text(lang, "quiet_hours_change"),
                    callback_data="edit_quiet_only:custom"
                )],
            ])

            await callback.message.edit_text(
                get_text(lang, "quiet_hours_prompt"),
                parse_mode="HTML",
                reply_markup=keyboard
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in edit menu selection: {e}", exc_info=True)
        await callback.answer(
            "❌ Произошла ошибка" if lang == "ru" else "❌ Қате орын алды",
            show_alert=True
        )


@router.callback_query(F.data.startswith("edit_duration:"), SubscriptionStates.editing_duration)
async def handle_edit_duration_selection(callback: CallbackQuery, state: FSMContext, lang: str, user_id: int, **kwargs):
    """
    Handle duration selection when editing

    Updates only the duration
    """
    from datetime import datetime, timedelta

    duration_choice = callback.data.split(":")[1]  # "today", "24h", "3d", "7d", or "forever"

    # Calculate expiry_date
    if duration_choice == "today":
        # Until end of today (23:59:59)
        now = datetime.utcnow()
        expiry_date = datetime(now.year, now.month, now.day, 23, 59, 59)
    elif duration_choice == "24h":
        expiry_date = datetime.utcnow() + timedelta(days=1)
    elif duration_choice == "3d":
        expiry_date = datetime.utcnow() + timedelta(days=3)
    elif duration_choice == "7d":
        expiry_date = datetime.utcnow() + timedelta(days=7)
    else:  # forever
        expiry_date = None

    # Update only duration
    user_data = await state.get_data()
    subscription_id = user_data["edit_subscription_id"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(
                Subscription.id == subscription_id,
                Subscription.user_id == user_id
            )
        )
        subscription = result.scalars().first()

        if not subscription:
            await callback.answer(
                "❌ Подписка не найдена" if lang == "ru" else "❌ Жазылым табылмады",
                show_alert=True
            )
            await state.clear()
            return

        # Update only expiry_date
        subscription.expiry_date = expiry_date
        await db.commit()

        logger.info(f"User {user_id} updated duration for subscription {subscription_id}: {duration_choice}")

        # Format duration for display
        duration_labels = {
            "today": get_text(lang, "duration_today_text"),
            "24h": get_text(lang, "duration_24h_text"),
            "3d": get_text(lang, "duration_3d_text"),
            "7d": get_text(lang, "duration_7d_text"),
            "forever": get_text(lang, "duration_forever_text")
        }

        await callback.message.edit_text(
            get_text(lang, "duration_updated").format(
                duration=duration_labels[duration_choice]
            ),
            parse_mode="HTML"
        )

        await callback.answer()

    await state.clear()


@router.callback_query(F.data.startswith("edit_quiet_only:"), SubscriptionStates.editing_quiet_hours)
async def handle_edit_quiet_hours_selection(callback: CallbackQuery, state: FSMContext, lang: str, user_id: int, **kwargs):
    """
    Handle quiet hours selection when editing

    Either uses default (23-07) or prompts for custom hours
    """
    quiet_choice = callback.data.split(":")[1]  # "default" or "custom"

    if quiet_choice == "default":
        # Use default quiet hours (23-07) and update immediately
        user_data = await state.get_data()
        subscription_id = user_data["edit_subscription_id"]

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.id == subscription_id,
                    Subscription.user_id == user_id
                )
            )
            subscription = result.scalars().first()

            if not subscription:
                await callback.answer(
                    "❌ Подписка не найдена" if lang == "ru" else "❌ Жазылым табылмады",
                    show_alert=True
                )
                await state.clear()
                return

            # Update only quiet hours
            subscription.mute_start = 23
            subscription.mute_end = 7
            await db.commit()

            logger.info(f"User {user_id} updated quiet hours for subscription {subscription_id}: 23-07")

            quiet_hours_text = "23:00 - 07:00"
            await callback.message.edit_text(
                get_text(lang, "quiet_hours_updated").format(
                    quiet_hours=quiet_hours_text
                ),
                parse_mode="HTML"
            )

        await state.clear()
        await callback.answer()
    else:
        # Ask for custom hours
        await state.set_state(SubscriptionStates.editing_custom_hours)
        await callback.message.edit_text(
            get_text(lang, "quiet_hours_custom"),
            parse_mode="HTML"
        )
        await callback.answer()


@router.message(SubscriptionStates.editing_custom_hours, F.text)
async def handle_edit_custom_quiet_hours(message: Message, state: FSMContext, lang: str, user_id: int, **kwargs):
    """
    Handle custom quiet hours input when editing

    Expects format: HH-HH (e.g., 22-08)
    """
    import re

    text = message.text.strip()
    match = re.match(r'^(\d{1,2})-(\d{1,2})$', text)

    if not match:
        await message.answer(
            get_text(lang, "quiet_hours_invalid"),
            parse_mode="HTML"
        )
        return

    start_hour = int(match.group(1))
    end_hour = int(match.group(2))

    # Validate hours (0-23)
    if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
        await message.answer(
            get_text(lang, "quiet_hours_invalid"),
            parse_mode="HTML"
        )
        return

    # Update only quiet hours
    user_data = await state.get_data()
    subscription_id = user_data["edit_subscription_id"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Subscription).where(
                Subscription.id == subscription_id,
                Subscription.user_id == user_id
            )
        )
        subscription = result.scalars().first()

        if not subscription:
            await message.answer(
                "❌ Подписка не найдена" if lang == "ru" else "❌ Жазылым табылмады",
                reply_markup=get_main_menu_keyboard(lang)
            )
            await state.clear()
            return

        # Update only quiet hours
        subscription.mute_start = start_hour
        subscription.mute_end = end_hour
        await db.commit()

        logger.info(f"User {user_id} updated quiet hours for subscription {subscription_id}: {start_hour}-{end_hour}")

        quiet_hours_text = f"{start_hour:02d}:00 - {end_hour:02d}:00"
        await message.answer(
            get_text(lang, "quiet_hours_updated").format(
                quiet_hours=quiet_hours_text
            ),
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(lang)
        )

    await state.clear()


@router.callback_query(F.data.startswith("safety_net:"))
async def handle_safety_net_activation(callback: CallbackQuery, lang: str, user_id: int, **kwargs):
    """
    Handle safety net button click

    Creates a temporary 3-hour session to monitor if air gets bad
    """
    from datetime import datetime, timedelta
    from app.services.air_quality import AirQualityService

    try:
        # Extract subscription ID from callback data
        subscription_id = int(callback.data.split(":")[1])

        async with AsyncSessionLocal() as db:
            # Get subscription
            result = await db.execute(
                select(Subscription).where(
                    Subscription.id == subscription_id,
                    Subscription.user_id == user_id  # Security check
                )
            )
            subscription = result.scalars().first()

            if not subscription:
                await callback.answer(
                    "❌ Подписка не найдена" if lang == "ru" else "❌ Жазылым табылмады",
                    show_alert=True
                )
                return

            # Get current AQI as baseline
            nearest_station = await AirQualityService.find_nearest_station(
                db,
                subscription.latitude,
                subscription.longitude,
                max_distance_km=50.0
            )

            if not nearest_station or nearest_station.aqi is None:
                await callback.answer(
                    "❌ Не удалось получить текущий AQI" if lang == "ru" else "❌ Ағымдағы AQI алу мүмкін болмады",
                    show_alert=True
                )
                return

            # Check if session already exists
            existing_session = await db.execute(
                select(SafetyNetSession).where(
                    SafetyNetSession.subscription_id == subscription_id,
                    SafetyNetSession.session_expiry > datetime.utcnow()
                )
            )

            if existing_session.scalars().first():
                await callback.answer(
                    "ℹ️ Мониторинг уже активирован" if lang == "ru" else "ℹ️ Мониторинг қазірдің өзінде белсенді",
                    show_alert=True
                )
                return

            # Create safety net session
            session = SafetyNetSession(
                user_id=user_id,
                subscription_id=subscription_id,
                start_aqi=nearest_station.aqi,
                session_expiry=datetime.utcnow() + timedelta(hours=3)
            )

            db.add(session)
            await db.commit()

            logger.info(f"Safety net activated for user {user_id}, subscription {subscription_id}, baseline AQI {nearest_station.aqi}")

            await callback.answer(
                get_text(lang, "safety_net_activated"),
                show_alert=True
            )

    except Exception as e:
        logger.error(f"Error activating safety net for user {user_id}: {e}", exc_info=True)
        await callback.answer(
            "❌ Произошла ошибка" if lang == "ru" else "❌ Қате орын алды",
            show_alert=True
        )


@router.callback_query(F.data.startswith("show_station:"))
async def handle_show_station(callback: CallbackQuery, lang: str, user_id: int, **kwargs):
    """
    Handle show station location callback

    Sends a map pin with the nearest station location
    """
    try:
        # Extract subscription ID from callback data
        subscription_id = int(callback.data.split(":")[1])

        async with AsyncSessionLocal() as db:
            # Find the subscription
            result = await db.execute(
                select(Subscription).where(
                    Subscription.id == subscription_id,
                    Subscription.user_id == user_id  # Security check
                )
            )
            subscription = result.scalars().first()

            if not subscription:
                await callback.answer(
                    "❌ Подписка не найдена" if lang == "ru" else "❌ Жазылым табылмады",
                    show_alert=True
                )
                return

            # Find nearest station
            from app.services.air_quality import AirQualityService

            nearest_station = await AirQualityService.find_nearest_station(
                db,
                subscription.latitude,
                subscription.longitude,
                max_distance_km=50.0
            )

            if not nearest_station:
                await callback.answer(
                    "❌ Станция не найдена" if lang == "ru" else "❌ Станция табылмады",
                    show_alert=True
                )
                return

            # Send station location on map
            await callback.message.answer_location(
                latitude=nearest_station.latitude,
                longitude=nearest_station.longitude
            )

            # Send station info
            station_info = f"📍 <b>{nearest_station.name}</b>"

            await callback.message.answer(
                station_info,
                parse_mode="HTML"
            )

            await callback.answer()

    except Exception as e:
        logger.error(f"Error showing station for user {user_id}: {e}", exc_info=True)
        await callback.answer(
            "❌ Произошла ошибка" if lang == "ru" else "❌ Қате орын алды",
            show_alert=True
        )


@router.callback_query(F.data.startswith("unsub:"))
async def handle_unsubscribe(callback: CallbackQuery, lang: str, user_id: int, **kwargs):
    """
    Handle unsubscribe callback

    Deactivates the subscription when user clicks delete button
    """
    try:
        # Extract subscription ID from callback data
        subscription_id = int(callback.data.split(":")[1])

        async with AsyncSessionLocal() as db:
            # Find the subscription
            result = await db.execute(
                select(Subscription).where(
                    Subscription.id == subscription_id,
                    Subscription.user_id == user_id  # Security: ensure it belongs to this user
                )
            )
            subscription = result.scalars().first()

            if not subscription:
                await callback.answer(
                    "❌ Подписка не найдена" if lang == "ru" else "❌ Жазылым табылмады",
                    show_alert=True
                )
                return

            # Deactivate subscription
            subscription.is_active = False
            await db.commit()

            logger.info(f"User {user_id} unsubscribed from subscription {subscription_id}")

            # Send confirmation
            await callback.message.edit_text(
                get_text(lang, "subscription_deleted"),
                parse_mode="HTML"
            )

            # Also send main menu
            await callback.message.answer(
                get_text(lang, "main_menu"),
                reply_markup=get_main_menu_keyboard(lang)
            )

            await callback.answer()

    except Exception as e:
        logger.error(f"Error unsubscribing user {user_id}: {e}", exc_info=True)
        await callback.answer(
            "❌ Произошла ошибка" if lang == "ru" else "❌ Қате орын алды",
            show_alert=True
        )
