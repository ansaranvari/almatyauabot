"""Redis client for caching"""
import redis.asyncio as aioredis
from typing import Optional
import logging
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class RedisCache:
    """Async Redis cache client"""

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None

    async def get_client(self) -> aioredis.Redis:
        """Get or create Redis client"""
        if self._redis is None:
            self._redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False  # We'll handle bytes for images
            )
        return self._redis

    async def get(self, key: str) -> Optional[bytes]:
        """Get value from cache"""
        try:
            client = await self.get_client()
            value = await client.get(key)
            return value
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: bytes, expire: int = 3600) -> bool:
        """
        Set value in cache with expiration

        Args:
            key: Cache key
            value: Value to store (bytes)
            expire: Expiration time in seconds (default 1 hour)

        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self.get_client()
            await client.set(key, value, ex=expire)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            client = await self.get_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def incr(self, key: str, expire: int = 60) -> Optional[int]:
        """
        Increment counter with expiration (for rate limiting)

        Args:
            key: Counter key
            expire: Expiration time in seconds

        Returns:
            New counter value or None on error
        """
        try:
            client = await self.get_client()
            # Use pipeline for atomic increment + expire
            async with client.pipeline() as pipe:
                await pipe.incr(key)
                await pipe.expire(key, expire)
                result = await pipe.execute()
                return result[0]  # Return incremented value
        except Exception as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return None

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()


# Global cache instance
redis_cache = RedisCache()
