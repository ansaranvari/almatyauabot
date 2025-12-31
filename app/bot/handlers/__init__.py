"""Handlers package"""

from aiogram import Router
from app.bot.handlers import start, language, location, info, subscription, favorites

# Create main router
router = Router()

# Include sub-routers
router.include_router(start.router)
router.include_router(language.router)
router.include_router(subscription.router)
router.include_router(favorites.router)
router.include_router(location.router)
router.include_router(info.router)
