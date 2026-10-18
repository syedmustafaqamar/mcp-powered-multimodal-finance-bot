"""Interface for cache operations following Interface Segregation Principle."""

from abc import ABC, abstractmethod
from typing import  Any


class ICacheService(ABC):
    """Abstract interface for cache service operations."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Get a value from cache by key.

        Args:
            key: Cache key

        Returns:
            Cached value if exists, None otherwise
        """
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        expire: int | None = None
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
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if key didn't exist
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            key: Cache key
            seconds: Expiration time in seconds

        Returns:
            True if expiration was set, False otherwise
        """
        pass