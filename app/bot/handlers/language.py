from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from app.db.models import User
from app.db.database import AsyncSessionLocal
from app.services.cache import cache
from app.core.locales import get_text
from app.bot.keyboards.reply import get_main_menu_keyboard, get_language_keyboard

router = Router()


@router.callback_query(F.data.startswith("lang:"))
async def callback_language_select(callback: CallbackQuery, lang: str, user_id: int, **kwargs):
    """
    Handle language selection from inline keyboard

    Callback data format: lang:ru or lang:kk
    """
    # Extract selected language from callback data
    selected_lang = callback.data.split(":")[1]

    if selected_lang not in ["ru", "kk", "en"]:
        await callback.answer("Invalid language")
        return

    # Update database
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalars().first()

        if user:
            user.language_code = selected_lang
            await db.commit()

    # Update cache
    await cache.set_user_language(user_id, selected_lang)

    # Show welcome message with bot description
    await callback.message.edit_text(
        get_text(selected_lang, "welcome"),
        parse_mode="HTML"
    )

    # Show main menu keyboard with next step prompt
    await callback.message.answer(
        get_text(selected_lang, "ready_prompt"),
        reply_markup=get_main_menu_keyboard(selected_lang)
    )

    await callback.answer()


@router.message(F.text.in_([
    "🗣️ Изменить язык", "🗣️ Тілді өзгерту", "🗣️ Change Language"
]))
async def cmd_change_language(message: Message, lang: str, **kwargs):
    """Handle change language button"""
    await message.answer(
        get_text(lang, "choose_language"),
        reply_markup=get_language_keyboard()
    )
