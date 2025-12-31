from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app.core.locales import get_text


def get_language_keyboard() -> InlineKeyboardMarkup:
    """
    Get inline keyboard for language selection

    Returns:
        InlineKeyboardMarkup with language options
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Қазақша", callback_data="lang:kk"),
            InlineKeyboardButton(text="Русский", callback_data="lang:ru"),
        ]
    ])
    return keyboard


def get_main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """
    Get main menu keyboard with localized buttons

    Args:
        lang: Language code (ru/kk)

    Returns:
        ReplyKeyboardMarkup with main menu options
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, "check_air_button"))],
            [KeyboardButton(text=get_text(lang, "subscribe_button"))],
            [KeyboardButton(text=get_text(lang, "my_subscriptions_button"))],
            [KeyboardButton(text=get_text(lang, "my_favorites_button"))],
            [
                KeyboardButton(text=get_text(lang, "change_language_button")),
                KeyboardButton(text=get_text(lang, "help_button")),
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder=get_text(lang, "main_menu")
    )
    return keyboard


def get_location_keyboard(lang: str, favorites: list = None) -> ReplyKeyboardMarkup:
    """
    Get keyboard with location sharing button and back button

    Args:
        lang: Language code (ru/kk)
        favorites: List of favorite locations to show as buttons

    Returns:
        ReplyKeyboardMarkup with location and back buttons
    """
    buttons = [
        [KeyboardButton(text=get_text(lang, "location_button"), request_location=True)],
    ]

    # Add individual favorite buttons if user has favorites
    if favorites:
        for favorite in favorites:
            buttons.append([KeyboardButton(text=f"⭐ {favorite.name}")])

    buttons.append([KeyboardButton(text=get_text(lang, "back_to_menu"))])

    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard
