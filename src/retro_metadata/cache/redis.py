"""Redis cache backend implementation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from retro_metadata.cache.base import CacheBackend

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RedisCache(CacheBackend):
    """Redis-based cache backend.

    This cache backend uses Redis for distributed caching with automatic
    TTL support.

    Args:
        client: An async Redis client instance
        default_ttl: Default TTL in seconds (default: 3600)
        prefix: Key prefix for namespacing (default: "retro_metadata:")

    Example:
        from redis.asyncio import Redis

        redis = Redis.from_url("redis://localhost:6379")
        cache = RedisCache(redis)
        await cache.set("key", {"data": "value"})
        result = await cache.get("key")
    """

    def __init__(
        self,
        client: Redis,
        default_ttl: int = 3600,
        prefix: str = "retro_metadata:",
    ) -> None:
        self._client = client
        self._default_ttl = default_ttl
        self._prefix = prefix

    def _make_key(self, key: str) -> str:
        """Create a prefixed key."""
        return f"{self._prefix}{key}"

    def _serialize(self, value: Any) -> str:
        """Serialize a value for storage."""
        return json.dumps(value)

    def _deserialize(self, data: str | bytes | None) -> Any | None:
        """Deserialize a stored value."""
        if data is None:
            return None
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return json.loads(data)

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache.

        Args:
            key: The cache key

        Returns:
            The cached value, or None if not found
        """
        data = await self._client.get(self._make_key(key))
        return self._deserialize(data)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in the cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl: Time-to-live in seconds (None uses default)
        """
        if ttl is None:
            ttl = self._default_ttl

        serialized = self._serialize(value)

        if ttl > 0:
            await self._client.setex(self._make_key(key), ttl, serialized)
        else:
            await self._client.set(self._make_key(key), serialized)

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: The cache key

        Returns:
            True if the key was deleted, False if it didn't exist
        """
        result = await self._client.delete(self._make_key(key))
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: The cache key

        Returns:
            True if the key exists
        """
        return await self._client.exists(self._make_key(key)) > 0

    async def clear(self) -> None:
        """Clear all entries with our prefix from the cache.

        Note: This uses SCAN to find keys, which is safe for production.
        """
        cursor = 0
        while True:
            cursor, keys = await self._client.scan(
                cursor, match=f"{self._prefix}*", count=100
            )
            if keys:
                await self._client.delete(*keys)
            if cursor == 0:
                break

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Retrieve multiple values from the cache.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary mapping keys to their values (missing keys omitted)
        """
        if not keys:
            return {}

        prefixed_keys = [self._make_key(k) for k in keys]
        values = await self._client.mget(prefixed_keys)

        result = {}
        for key, value in zip(keys, values, strict=False):
            if value is not None:
                result[key] = self._deserialize(value)
        return result

    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        """Store multiple values in the cache.

        Args:
            items: Dictionary mapping keys to values
            ttl: Time-to-live in seconds (None uses default)
        """
        if not items:
            return

        if ttl is None:
            ttl = self._default_ttl

        # Use pipeline for efficiency
        pipe = self._client.pipeline()
        for key, value in items.items():
            prefixed_key = self._make_key(key)
            serialized = self._serialize(value)
            if ttl > 0:
                pipe.setex(prefixed_key, ttl, serialized)
            else:
                pipe.set(prefixed_key, serialized)
        await pipe.execute()

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._client.close()

    async def hget(self, name: str, key: str) -> Any | None:
        """Get a field from a hash.

        Args:
            name: Hash name
            key: Field key

        Returns:
            Field value or None
        """
        data = await self._client.hget(self._make_key(name), key)
        return self._deserialize(data)

    async def hset(self, name: str, key: str, value: Any) -> None:
        """Set a field in a hash.

        Args:
            name: Hash name
            key: Field key
            value: Field value
        """
        serialized = self._serialize(value)
        await self._client.hset(self._make_key(name), key, serialized)

    async def hgetall(self, name: str) -> dict[str, Any]:
        """Get all fields from a hash.

        Args:
            name: Hash name

        Returns:
            Dictionary of all fields
        """
        data = await self._client.hgetall(self._make_key(name))
        return {
            k.decode("utf-8") if isinstance(k, bytes) else k: self._deserialize(v)
            for k, v in data.items()
        }
