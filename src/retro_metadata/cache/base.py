"""Abstract base class for cache backends."""

from __future__ import annotations

import abc
from typing import Any


class CacheBackend(abc.ABC):
    """Abstract base class for cache backends.

    All cache backends must implement these methods to provide
    consistent caching behavior across different storage mechanisms.
    """

    @abc.abstractmethod
    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache.

        Args:
            key: The cache key

        Returns:
            The cached value, or None if not found or expired
        """

    @abc.abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in the cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl: Time-to-live in seconds (None uses default)
        """

    @abc.abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: The cache key

        Returns:
            True if the key was deleted, False if it didn't exist
        """

    @abc.abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: The cache key

        Returns:
            True if the key exists and hasn't expired
        """

    @abc.abstractmethod
    async def clear(self) -> None:
        """Clear all entries from the cache."""

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Retrieve multiple values from the cache.

        Default implementation calls get() for each key.
        Backends may override for better performance.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary mapping keys to their values (missing keys omitted)
        """
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        """Store multiple values in the cache.

        Default implementation calls set() for each item.
        Backends may override for better performance.

        Args:
            items: Dictionary mapping keys to values
            ttl: Time-to-live in seconds (None uses default)
        """
        for key, value in items.items():
            await self.set(key, value, ttl)

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple values from the cache.

        Default implementation calls delete() for each key.
        Backends may override for better performance.

        Args:
            keys: List of cache keys

        Returns:
            Number of keys that were deleted
        """
        count = 0
        for key in keys:
            if await self.delete(key):
                count += 1
        return count

    async def close(self) -> None:
        """Close any connections and clean up resources.

        Default implementation does nothing.
        Backends with connections should override.
        """


class NullCache(CacheBackend):
    """A cache backend that doesn't cache anything.

    Useful for testing or disabling caching.
    """

    async def get(self, key: str) -> Any | None:
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        pass

    async def delete(self, key: str) -> bool:
        return False

    async def exists(self, key: str) -> bool:
        return False

    async def clear(self) -> None:
        pass
