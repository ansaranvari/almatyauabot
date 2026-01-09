from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.core.locales import get_text
from app.bot.keyboards.reply import get_main_menu_keyboard, get_language_keyboard
from app.services.analytics import analytics

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, lang: str, user_id: int, **kwargs):
    """
    Handle /start command

    Shows simple language selection first
    """
    # Track start command
    await analytics.track_event(user_id, "start_command")
    await analytics.increment_feature_usage("start", user_id)

    await message.answer(
        get_text(lang, "choose_language"),
        reply_markup=get_language_keyboard()
    )


@router.message(F.text.in_([
    "ℹ️ Помощь", "ℹ️ Көмек", "ℹ️ Help"
]))
async def cmd_help(message: Message, lang: str, user_id: int, **kwargs):
    """Handle help button"""
    # Track help usage
    await analytics.track_event(user_id, "help")
    await analytics.increment_feature_usage("help", user_id)

    await message.answer(
        get_text(lang, "help_text"),
        parse_mode="HTML"
    )


@router.message(F.text.in_([
    "◀️ Назад в меню", "◀️ Мәзірге оралу", "◀️ Back to Menu"
]))
async def cmd_back_to_menu(message: Message, state: FSMContext, lang: str, **kwargs):
    """
    Handle back to menu button

    Clears any FSM state and returns to main menu
    """
    # Clear any active state
    await state.clear()

    await message.answer(
        get_text(lang, "main_menu"),
        reply_markup=get_main_menu_keyboard(lang)
    )
