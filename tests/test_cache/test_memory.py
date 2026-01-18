"""Tests for the memory cache backend."""

import asyncio

import pytest

from retro_metadata.cache.memory import MemoryCache


@pytest.fixture
def cache():
    """Create a memory cache for testing."""
    return MemoryCache(max_size=10, default_ttl=60)


class TestMemoryCache:
    """Tests for MemoryCache."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        await cache.set("key1", {"data": "value1"})
        result = await cache.get("key1")
        assert result == {"data": "value1"}

    @pytest.mark.asyncio
    async def test_get_missing_key(self, cache):
        """Test getting a missing key returns None."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test deleting a key."""
        await cache.set("key1", "value1")
        await cache.delete("key1")
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clearing all keys."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = MemoryCache(max_size=10, default_ttl=0.1)  # 100ms TTL
        await cache.set("key1", "value1")

        # Should exist immediately
        assert await cache.get("key1") == "value1"

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Should be expired
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_custom_ttl(self, cache):
        """Test setting custom TTL per key."""
        await cache.set("key1", "value1", ttl=0.1)
        await cache.set("key2", "value2", ttl=60)

        await asyncio.sleep(0.2)

        # key1 should be expired
        assert await cache.get("key1") is None
        # key2 should still exist
        assert await cache.get("key2") == "value2"

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = MemoryCache(max_size=3, default_ttl=60)

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Access key1 to make it recently used
        await cache.get("key1")

        # Add key4, should evict key2 (least recently used)
        await cache.set("key4", "value4")

        assert await cache.get("key1") is not None
        assert await cache.get("key2") is None  # Evicted
        assert await cache.get("key3") is not None
        assert await cache.get("key4") is not None

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self, cache):
        """Test overwriting an existing key."""
        await cache.set("key1", "value1")
        await cache.set("key1", "value2")
        result = await cache.get("key1")
        assert result == "value2"

    @pytest.mark.asyncio
    async def test_close(self, cache):
        """Test closing the cache."""
        await cache.set("key1", "value1")
        await cache.close()
        # Cache should be cleared after close
        assert await cache.get("key1") is None
