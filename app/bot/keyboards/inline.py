"""Inline keyboards for air quality info"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.core.locales import get_text


def get_air_quality_info_keyboard(lang: str, station_id: int = None, lat: float = None, lon: float = None, user_lat: float = None, user_lon: float = None, show_subscribe: bool = True, show_favorite: bool = True) -> InlineKeyboardMarkup:
    """
    Get inline keyboard with info buttons for pollutants

    Args:
        lang: Language code (ru/kk)
        station_id: Station ID for show location button
        lat: Station latitude
        lon: Station longitude
        user_lat: User's latitude (for subscribe/favorite buttons)
        user_lon: User's longitude (for subscribe/favorite buttons)
        show_subscribe: Whether to show subscribe button
        show_favorite: Whether to show favorite button

    Returns:
        InlineKeyboardMarkup with info buttons
    """
    # Compact button layout - feels more integrated with the message
    # Include station_id in callback data for return functionality
    station_param = f":{station_id}" if station_id else ""
    buttons = [
        [
            InlineKeyboardButton(
                text="ℹ️ PM2.5",
                callback_data=f"info:pm25{station_param}"
            ),
            InlineKeyboardButton(
                text="ℹ️ PM10",
                callback_data=f"info:pm10{station_param}"
            ),
            InlineKeyboardButton(
                text="ℹ️ PM1.0",
                callback_data=f"info:pm1{station_param}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="ℹ️ AQI",
                callback_data=f"info:aqi{station_param}"
            ),
            InlineKeyboardButton(
                text={"ru": "📊 График 24ч", "kk": "📊 24с график", "en": "📊 24h Chart"}.get(lang, "📊 24h Chart"),
                callback_data=f"chart:24h{station_param}"
            ),
        ]
    ]

    # Add subscribe to this location button if user location is provided and not already subscribed
    if user_lat and user_lon and show_subscribe:
        subscribe_texts = {
            "ru": "🔔 Подписаться на это место",
            "kk": "🔔 Бұл жерге жазылу",
            "en": "🔔 Subscribe to this location"
        }
        subscribe_text = subscribe_texts.get(lang, subscribe_texts["en"])
        buttons.append([
            InlineKeyboardButton(
                text=subscribe_text,
                callback_data=f"quick_subscribe:{user_lat}:{user_lon}"
            )
        ])

    # Add favorite button if user location is provided and not already favorited
    if user_lat and user_lon and show_favorite:
        add_fav_texts = {
            "ru": "⭐ Добавить в избранное",
            "kk": "⭐ Таңдаулыға қосу",
            "en": "⭐ Add to Favorites"
        }
        add_fav_text = add_fav_texts.get(lang, add_fav_texts["en"])
        buttons.append([
            InlineKeyboardButton(
                text=add_fav_text,
                callback_data=f"add_favorite:{user_lat}:{user_lon}"
            )
        ])

    # Add show station location button if station info is provided
    if station_id and lat and lon:
        show_station_texts = {
            "ru": "📍 Показать, где находится датчик",
            "kk": "📍 Датчик қайда екенін көрсету",
            "en": "📍 Show station location"
        }
        show_station_text = show_station_texts.get(lang, show_station_texts["en"])
        buttons.append([
            InlineKeyboardButton(
                text=show_station_text,
                callback_data=f"show_station_loc:{station_id}:{lat}:{lon}"
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
