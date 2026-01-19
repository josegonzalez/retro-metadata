"""In-memory cache backend implementation."""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from retro_metadata.cache.base import CacheBackend


@dataclass
class CacheEntry:
    """A single cache entry with expiration."""

    value: Any
    expires_at: float | None = None

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class MemoryCache(CacheBackend):
    """In-memory LRU cache with TTL support.

    This cache implementation uses an OrderedDict to maintain LRU order
    and supports automatic expiration of entries.

    Args:
        max_size: Maximum number of entries to store (default: 10000)
        default_ttl: Default TTL in seconds (default: 3600)
        cleanup_interval: Interval for expired entry cleanup in seconds (default: 60)

    Example:
        cache = MemoryCache(max_size=1000, default_ttl=300)
        await cache.set("key", "value")
        result = await cache.get("key")
    """

    def __init__(
        self,
        max_size: int = 10000,
        default_ttl: int = 3600,
        cleanup_interval: int = 60,
    ) -> None:
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def _start_cleanup_task(self) -> None:
        """Start the background cleanup task if not running."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self) -> None:
        """Background task to periodically clean up expired entries."""
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
        except asyncio.CancelledError:
            pass

    async def _cleanup_expired(self) -> None:
        """Remove all expired entries from the cache."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache is at capacity."""
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache.

        Args:
            key: The cache key

        Returns:
            The cached value, or None if not found or expired
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            if entry.is_expired():
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return entry.value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in the cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl: Time-to-live in seconds (None uses default)
        """
        if ttl is None:
            ttl = self._default_ttl

        expires_at = time.time() + ttl if ttl > 0 else None

        async with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            else:
                self._evict_if_needed()

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

        # Start cleanup task if not running
        await self._start_cleanup_task()

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: The cache key

        Returns:
            True if the key was deleted, False if it didn't exist
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: The cache key

        Returns:
            True if the key exists and hasn't expired
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False

            if entry.is_expired():
                del self._cache[key]
                return False

            return True

    async def clear(self) -> None:
        """Clear all entries from the cache."""
        async with self._lock:
            self._cache.clear()

    async def close(self) -> None:
        """Cancel the cleanup task and clear the cache."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None
        await self.clear()

    @property
    def size(self) -> int:
        """Get the current number of entries in the cache."""
        return len(self._cache)

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        async with self._lock:
            expired_count = sum(1 for e in self._cache.values() if e.is_expired())
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "expired_count": expired_count,
                "default_ttl": self._default_ttl,
            }
