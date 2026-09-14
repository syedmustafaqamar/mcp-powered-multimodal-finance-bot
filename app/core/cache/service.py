"""Cache service implementation following Dependency Inversion Principle."""

import json
from typing import Optional, Any
from app.core.interfaces.cache import ICacheService
from app.core.cache.connection import RedisConnection
from app.core.logger import logger


class CacheService(ICacheService):
    """Redis-based cache service implementation."""

    def __init__(self, redis_client=None):
        """
        Initialize cache service.

        Args:
            redis_client: Optional Redis client (uses RedisConnection if not provided)
        """
        self._client = redis_client or RedisConnection.get_client()

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache by key.

        Args:
            key: Cache key

        Returns:
            Cached value if exists, None otherwise
        """
        try:
            value = await self._client.get(key)
            if value is None:
                return None

            # Try to deserialize JSON, fallback to string
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {str(e)}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            expire: Optional expiration time in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize value to JSON if it's not a string
            if not isinstance(value, str):
                serialized_value = json.dumps(value)
            else:
                serialized_value = value

            if expire:
                await self._client.setex(key, expire, serialized_value)
            else:
                await self._client.set(key, serialized_value)

            return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if key didn't exist
        """
        try:
            result = await self._client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            result = await self._client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {str(e)}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            key: Cache key
            seconds: Expiration time in seconds

        Returns:
            True if expiration was set, False otherwise
        """
        try:
            result = await self._client.expire(key, seconds)
            return result
        except Exception as e:
            logger.error(f"Error setting expiration for cache key {key}: {str(e)}")
            return False

