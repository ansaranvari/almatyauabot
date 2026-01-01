from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User as DBUser
from app.db.database import AsyncSessionLocal
from app.services.cache import cache
from app.core.config import get_settings

settings = get_settings()


class I18nMiddleware(BaseMiddleware):
    """
    Middleware for injecting user's language preference into handlers

    This middleware:
    1. Checks Redis cache for user's language
    2. Falls back to database if not in cache
    3. Creates new user record if needed
    4. Injects language code into handler's data dict
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Process middleware"""

        # Get user from event
        user: User = data.get("event_from_user")

        if not user:
            # No user in event, use default language
            data["lang"] = settings.DEFAULT_LANGUAGE
            return await handler(event, data)

        user_id = user.id

        # Try to get language from Redis cache
        lang = await cache.get_user_language(user_id)

        if lang:
            # Found in cache
            data["lang"] = lang
            data["user_id"] = user_id
            return await handler(event, data)

        # Not in cache, check database
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(DBUser).where(DBUser.id == user_id)
            )
            db_user = result.scalars().first()  # Use first() to handle duplicate rows gracefully

            if db_user:
                # User exists in database
                lang = db_user.language_code
                # Cache it
                await cache.set_user_language(user_id, lang)
            else:
                # New user - use Telegram's language_code or default
                lang = user.language_code if user.language_code in settings.SUPPORTED_LANGUAGES else settings.DEFAULT_LANGUAGE

                # Create user record
                db_user = DBUser(
                    id=user_id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language_code=lang,
                    seen_check_onboarding=False,
                    seen_subscribe_onboarding=False,
                )
                db.add(db_user)
                await db.commit()

                # Cache it
                await cache.set_user_language(user_id, lang)

        data["lang"] = lang
        data["user_id"] = user_id

        return await handler(event, data)
