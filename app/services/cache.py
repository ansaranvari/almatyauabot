import json
from typing import Optional, Any
import redis.asyncio as aioredis
from app.core.config import get_settings

settings = get_settings()


class RedisCache:
    """Redis cache manager for user language preferences and API data"""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        self.redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()

    async def get_user_language(self, user_id: int) -> Optional[str]:
        """
        Get user's language preference from cache

        Args:
            user_id: Telegram user ID

        Returns:
            Language code (ru/kk) or None
        """
        key = f"user:{user_id}:lang"
        return await self.redis.get(key)

    async def set_user_language(self, user_id: int, language: str, ttl: int = 86400 * 30):
        """
        Cache user's language preference

        Args:
            user_id: Telegram user ID
            language: Language code (ru/kk)
            ttl: Time to live in seconds (default: 30 days)
        """
        key = f"user:{user_id}:lang"
        await self.redis.setex(key, ttl, language)

    async def get_station_data(self, station_id: str) -> Optional[dict]:
        """
        Get cached station data

        Args:
            station_id: Station identifier

        Returns:
            Station data dictionary or None
        """
        key = f"station:{station_id}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_station_data(self, station_id: str, data: dict, ttl: int = 900):
        """
        Cache station data

        Args:
            station_id: Station identifier
            data: Station data dictionary
            ttl: Time to live in seconds (default: 15 minutes)
        """
        key = f"station:{station_id}"
        await self.redis.setex(key, ttl, json.dumps(data))

    async def get(self, key: str) -> Optional[Any]:
        """Generic get from cache"""
        return await self.redis.get(key)

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Generic set to cache"""
        await self.redis.setex(key, ttl, value)

    async def delete(self, key: str):
        """Delete key from cache"""
        await self.redis.delete(key)


# Global cache instance
cache = RedisCache()
