"""Redis connection manager following Single Responsibility Principle."""

import redis.asyncio as aioredis
from typing import Optional
from app.core.config import settings
from app.core.logger import logger


class RedisConnection:
    """Singleton Redis connection manager with connection pooling."""

    _client: aioredis.Redis | None = None
    _connection_pool: aioredis.ConnectionPool | None = None

    @classmethod
    def get_client(cls) -> aioredis.Redis:
        """
        Get or create Redis client instance.

        Returns:
            Redis client instance
        """
        if cls._client is None:
            cls._initialize()

        return cls._client

    @classmethod
    def _initialize(cls) -> None:
        """Initialize Redis connection pool and client."""
        try:
            # Build Redis URL
            redis_url = cls._build_redis_url()

            # Create connection pool
            cls._connection_pool = aioredis.ConnectionPool.from_url(
                redis_url,
                max_connections=20,
                decode_responses=True
            )

            # Create Redis client
            cls._client = aioredis.Redis(connection_pool=cls._connection_pool)

            logger.info(f"Redis connection initialized: {redis_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {str(e)}")
            raise

    @classmethod
    def _build_redis_url(cls) -> str:
        """Build Redis connection URL from settings."""
        # password_part = f":{settings.REDIS_PASSWORD}@" if settings.REDIS_PASSWORD else ""
        # return f"redis://{password_part}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        return settings.REDIS_URL

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection and connection pool."""
        if cls._client:
            try:
                await cls._client.aclose()
                logger.info("Redis client closed")
            except Exception as e:
                logger.error(f"Error closing Redis client: {str(e)}")
            finally:
                cls._client = None

        if cls._connection_pool:
            try:
                await cls._connection_pool.aclose()
                logger.info("Redis connection pool closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection pool: {str(e)}")
            finally:
                cls._connection_pool = None

    @classmethod
    async def ping(cls) -> bool:
        """
        Check if Redis connection is alive.

        Returns:
            True if connection is alive, False otherwise
        """
        try:
            client = cls.get_client()
            result = await client.ping()
            return result
        except Exception as e:
            logger.error(f"Redis ping failed: {str(e)}")
            return False