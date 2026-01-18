# Cache Architecture

This document covers the caching subsystem, including the abstract backend interface, concrete implementations, and the artwork-specific caching system.

## Overview

The library uses two separate caching systems:

1. **Metadata Cache** - Caches API responses from providers
2. **Artwork Cache** - Caches downloaded image files

```
┌─────────────────────────────────────────────────────────┐
│                    MetadataClient                        │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
    ┌────▼─────┐            ┌─────▼──────┐
    │ Metadata │            │  Artwork   │
    │  Cache   │            │   Cache    │
    └────┬─────┘            └─────┬──────┘
         │                        │
    ┌────▼─────────────────┐ ┌───▼────────────┐
    │ Backend Options:     │ │ SQLite-backed  │
    │ • Memory (default)   │ │ file cache     │
    │ • Redis              │ │                │
    │ • SQLite             │ │                │
    │ • None               │ │                │
    └──────────────────────┘ └────────────────┘
```

## Metadata Cache

### Cache Backend Interface (`cache/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Any

class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Retrieve a value by key.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Store a value with optional TTL.

        Args:
            key: Cache key
            value: Value to store (must be serializable)
            ttl: Time-to-live in seconds (None = use default)
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key.

        Returns:
            True if key existed and was deleted
        """

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""

    @abstractmethod
    async def clear(self) -> int:
        """Clear all entries.

        Returns:
            Number of entries cleared
        """

    # Optional batch operations (have default implementations)

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple keys at once."""
        return {k: await self.get(k) for k in keys}

    async def set_many(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Set multiple key-value pairs."""
        for key, value in items.items():
            await self.set(key, value, ttl)

    async def delete_many(self, keys: list[str]) -> int:
        """Delete multiple keys."""
        count = 0
        for key in keys:
            if await self.delete(key):
                count += 1
        return count

    async def close(self) -> None:
        """Clean up resources. Override in subclasses."""
        pass
```

### Null Cache (`cache/base.py`)

A no-op implementation for testing or disabling caching.

```python
class NullCache(CacheBackend):
    """Cache that stores nothing (passthrough)."""

    async def get(self, key: str) -> None:
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        pass

    async def delete(self, key: str) -> bool:
        return False

    async def exists(self, key: str) -> bool:
        return False

    async def clear(self) -> int:
        return 0
```

### Memory Cache (`cache/memory.py`)

In-memory LRU cache with TTL support.

```python
from collections import OrderedDict
from dataclasses import dataclass
import asyncio
import time

@dataclass
class CacheEntry:
    """Single cache entry with expiration."""
    value: Any
    expires_at: float  # Unix timestamp

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class MemoryCache(CacheBackend):
    """In-memory LRU cache with TTL support.

    Features:
    - LRU eviction when max_size reached
    - TTL-based expiration
    - Background cleanup task
    - Thread-safe with asyncio.Lock
    """

    def __init__(
        self,
        max_size: int = 10000,
        default_ttl: int = 3600,
        cleanup_interval: int = 300,
    ) -> None:
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    async def get(self, key: str) -> Any | None:
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

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        ttl = ttl or self._default_ttl
        expires_at = time.time() + ttl

        async with self._lock:
            # Remove if exists (to update position)
            if key in self._cache:
                del self._cache[key]

            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            self._cache[key] = CacheEntry(value, expires_at)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                del self._cache[key]
                return False
            return True

    async def clear(self) -> int:
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        async with self._lock:
            now = time.time()
            expired = sum(
                1 for e in self._cache.values()
                if e.expires_at < now
            )
            return {
                "total_entries": len(self._cache),
                "expired_entries": expired,
                "max_size": self._max_size,
            }

    # Background cleanup

    async def start_cleanup(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def _cleanup_loop(self) -> None:
        """Periodically remove expired entries."""
        while True:
            await asyncio.sleep(self._cleanup_interval)
            await self._cleanup_expired()

    async def _cleanup_expired(self) -> int:
        """Remove all expired entries."""
        async with self._lock:
            now = time.time()
            expired_keys = [
                k for k, e in self._cache.items()
                if e.expires_at < now
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    async def close(self) -> None:
        await self.stop_cleanup()
```

### Redis Cache (`cache/redis.py`)

Distributed cache using Redis.

```python
import json
import redis.asyncio as redis

class RedisCache(CacheBackend):
    """Redis-backed distributed cache.

    Features:
    - Native TTL support
    - Distributed across instances
    - Automatic serialization (JSON)
    - Connection pooling
    """

    def __init__(
        self,
        connection_string: str = "redis://localhost:6379",
        default_ttl: int = 3600,
        key_prefix: str = "retro_metadata:",
    ) -> None:
        self._connection_string = connection_string
        self._default_ttl = default_ttl
        self._key_prefix = key_prefix
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self._connection_string)
        return self._client

    def _make_key(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    async def get(self, key: str) -> Any | None:
        client = await self._get_client()
        data = await client.get(self._make_key(key))
        if data is None:
            return None
        return json.loads(data)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        client = await self._get_client()
        ttl = ttl or self._default_ttl
        data = json.dumps(value)
        await client.setex(self._make_key(key), ttl, data)

    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        result = await client.delete(self._make_key(key))
        return result > 0

    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        return await client.exists(self._make_key(key)) > 0

    async def clear(self) -> int:
        client = await self._get_client()
        pattern = f"{self._key_prefix}*"
        keys = await client.keys(pattern)
        if keys:
            return await client.delete(*keys)
        return 0

    # Optimized batch operations using Redis pipelines

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        client = await self._get_client()
        full_keys = [self._make_key(k) for k in keys]
        values = await client.mget(full_keys)
        return {
            keys[i]: json.loads(v) if v else None
            for i, v in enumerate(values)
        }

    async def set_many(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        client = await self._get_client()
        ttl = ttl or self._default_ttl
        pipe = client.pipeline()
        for key, value in items.items():
            data = json.dumps(value)
            pipe.setex(self._make_key(key), ttl, data)
        await pipe.execute()

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
```

### SQLite Cache (`cache/sqlite.py`)

Persistent cache using SQLite.

```python
import aiosqlite
import json
import time

class SQLiteCache(CacheBackend):
    """SQLite-backed persistent cache.

    Features:
    - Persistent across restarts
    - Single-file storage
    - SQL-based expiration
    - Thread-safe with aiosqlite
    """

    def __init__(
        self,
        db_path: str = "cache.db",
        default_ttl: int = 3600,
    ) -> None:
        self._db_path = db_path
        self._default_ttl = default_ttl
        self._db: aiosqlite.Connection | None = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self._db_path)
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            await self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)"
            )
            await self._db.commit()
        return self._db

    async def get(self, key: str) -> Any | None:
        db = await self._get_db()
        now = time.time()
        async with db.execute(
            "SELECT value FROM cache WHERE key = ? AND expires_at > ?",
            (key, now),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        db = await self._get_db()
        ttl = ttl or self._default_ttl
        expires_at = time.time() + ttl
        data = json.dumps(value)
        await db.execute(
            """
            INSERT OR REPLACE INTO cache (key, value, expires_at)
            VALUES (?, ?, ?)
            """,
            (key, data, expires_at),
        )
        await db.commit()

    async def delete(self, key: str) -> bool:
        db = await self._get_db()
        cursor = await db.execute(
            "DELETE FROM cache WHERE key = ?",
            (key,),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def exists(self, key: str) -> bool:
        db = await self._get_db()
        now = time.time()
        async with db.execute(
            "SELECT 1 FROM cache WHERE key = ? AND expires_at > ?",
            (key, now),
        ) as cursor:
            return await cursor.fetchone() is not None

    async def clear(self) -> int:
        db = await self._get_db()
        cursor = await db.execute("DELETE FROM cache")
        await db.commit()
        return cursor.rowcount

    async def clear_expired(self) -> int:
        """Remove expired entries."""
        db = await self._get_db()
        now = time.time()
        cursor = await db.execute(
            "DELETE FROM cache WHERE expires_at <= ?",
            (now,),
        )
        await db.commit()
        return cursor.rowcount

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
```

### Cache Configuration

```python
@dataclass
class CacheConfig:
    """Cache configuration."""

    backend: str = "memory"  # "memory", "redis", "sqlite", "none"
    ttl: int = 3600  # Default TTL in seconds
    max_size: int = 10000  # For memory cache
    connection_string: str = ""  # For redis/sqlite

    # Redis-specific
    key_prefix: str = "retro_metadata:"

    # SQLite-specific
    db_path: str = "cache.db"
```

### Cache Initialization in Client

```python
class MetadataClient:
    async def _initialize(self) -> None:
        # Initialize cache based on config
        match self.config.cache.backend:
            case "memory":
                self._cache = MemoryCache(
                    max_size=self.config.cache.max_size,
                    default_ttl=self.config.cache.ttl,
                )
            case "redis":
                self._cache = RedisCache(
                    connection_string=self.config.cache.connection_string,
                    default_ttl=self.config.cache.ttl,
                )
            case "sqlite":
                self._cache = SQLiteCache(
                    db_path=self.config.cache.db_path,
                    default_ttl=self.config.cache.ttl,
                )
            case "none" | _:
                self._cache = NullCache()

        # Initialize providers with cache
        self._init_providers()
```

## Artwork Cache

The artwork cache is separate from the metadata cache and specifically handles downloaded image files.

### Artwork Cache Design (`artwork/cache.py`)

```python
from dataclasses import dataclass
from pathlib import Path
import aiosqlite
import hashlib
import time

@dataclass
class CachedArtwork:
    """Cached artwork metadata."""
    url: str
    provider: str
    path: Path
    width: int | None
    height: int | None
    download_date: int  # Unix timestamp
    expires_at: int  # Unix timestamp

class ArtworkCache:
    """File-based artwork cache with SQLite index.

    Structure:
    cache_dir/
    ├── index.db          # SQLite metadata database
    ├── igdb/             # Provider subdirectories
    │   ├── abc123.jpg
    │   └── def456.png
    ├── screenscraper/
    │   └── ghi789.jpg
    └── steamgriddb/
        └── jkl012.png
    """

    def __init__(self, config: ArtworkConfig) -> None:
        self.config = config
        self._cache_dir = config.get_cache_dir()
        self._db_path = self._cache_dir / "index.db"
        self._db: aiosqlite.Connection | None = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self._db_path)
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS artwork (
                    url TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    path TEXT NOT NULL,
                    width INTEGER,
                    height INTEGER,
                    download_date INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                )
            """)
            await self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_provider ON artwork(provider)"
            )
            await self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires ON artwork(expires_at)"
            )
            await self._db.commit()
        return self._db

    def _hash_url(self, url: str) -> str:
        """Generate cache filename from URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def _get_cache_path(self, url: str, provider: str, extension: str) -> Path:
        """Get path for cached file."""
        filename = f"{self._hash_url(url)}{extension}"
        return self._cache_dir / provider / filename

    async def get(self, url: str) -> CachedArtwork | None:
        """Get cached artwork by URL."""
        db = await self._get_db()
        now = int(time.time())

        async with db.execute(
            """
            SELECT provider, path, width, height, download_date, expires_at
            FROM artwork
            WHERE url = ? AND expires_at > ?
            """,
            (url, now),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None

            path = Path(row[1])
            if not path.exists():
                # File was deleted, remove from index
                await self.delete(url)
                return None

            return CachedArtwork(
                url=url,
                provider=row[0],
                path=path,
                width=row[2],
                height=row[3],
                download_date=row[4],
                expires_at=row[5],
            )

    async def put(
        self,
        url: str,
        provider: str,
        data: bytes,
        content_type: str | None = None,
    ) -> CachedArtwork:
        """Store artwork in cache."""
        from retro_metadata.artwork.utils import (
            get_extension_from_content_type,
            get_extension_from_url,
            get_image_dimensions,
        )

        # Determine extension
        if content_type:
            extension = get_extension_from_content_type(content_type)
        else:
            extension = get_extension_from_url(url)

        # Get cache path
        cache_path = self._get_cache_path(url, provider, extension)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        cache_path.write_bytes(data)

        # Get dimensions
        width, height = get_image_dimensions(data)

        # Store in index
        db = await self._get_db()
        now = int(time.time())
        expires_at = now + self.config.cache_ttl

        await db.execute(
            """
            INSERT OR REPLACE INTO artwork
            (url, provider, path, width, height, download_date, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (url, provider, str(cache_path), width, height, now, expires_at),
        )
        await db.commit()

        return CachedArtwork(
            url=url,
            provider=provider,
            path=cache_path,
            width=width,
            height=height,
            download_date=now,
            expires_at=expires_at,
        )

    async def delete(self, url: str) -> bool:
        """Delete cached artwork."""
        db = await self._get_db()

        # Get path before deleting from index
        async with db.execute(
            "SELECT path FROM artwork WHERE url = ?",
            (url,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return False

            path = Path(row[0])
            if path.exists():
                path.unlink()

        await db.execute("DELETE FROM artwork WHERE url = ?", (url,))
        await db.commit()
        return True

    async def clear_provider(self, provider: str) -> int:
        """Clear all cached artwork for a provider."""
        db = await self._get_db()

        # Get all paths for provider
        async with db.execute(
            "SELECT path FROM artwork WHERE provider = ?",
            (provider,),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                path = Path(row[0])
                if path.exists():
                    path.unlink()

        cursor = await db.execute(
            "DELETE FROM artwork WHERE provider = ?",
            (provider,),
        )
        await db.commit()
        return cursor.rowcount

    async def clear_expired(self) -> int:
        """Remove expired cache entries."""
        db = await self._get_db()
        now = int(time.time())

        # Get expired paths
        async with db.execute(
            "SELECT path FROM artwork WHERE expires_at <= ?",
            (now,),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                path = Path(row[0])
                if path.exists():
                    path.unlink()

        cursor = await db.execute(
            "DELETE FROM artwork WHERE expires_at <= ?",
            (now,),
        )
        await db.commit()
        return cursor.rowcount

    async def clear_all(self) -> int:
        """Clear entire cache."""
        db = await self._get_db()

        # Delete all files
        for provider_dir in self._cache_dir.iterdir():
            if provider_dir.is_dir() and provider_dir.name != "index.db":
                for file in provider_dir.iterdir():
                    file.unlink()
                provider_dir.rmdir()

        cursor = await db.execute("DELETE FROM artwork")
        await db.commit()
        return cursor.rowcount

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        db = await self._get_db()
        now = int(time.time())

        # Total entries
        async with db.execute("SELECT COUNT(*) FROM artwork") as cursor:
            total = (await cursor.fetchone())[0]

        # Expired entries
        async with db.execute(
            "SELECT COUNT(*) FROM artwork WHERE expires_at <= ?",
            (now,),
        ) as cursor:
            expired = (await cursor.fetchone())[0]

        # Entries by provider
        by_provider = {}
        async with db.execute(
            "SELECT provider, COUNT(*) FROM artwork GROUP BY provider"
        ) as cursor:
            async for row in cursor:
                by_provider[row[0]] = row[1]

        # Total size
        total_size = 0
        for provider_dir in self._cache_dir.iterdir():
            if provider_dir.is_dir():
                for file in provider_dir.iterdir():
                    total_size += file.stat().st_size

        return {
            "cache_dir": str(self._cache_dir),
            "total_entries": total,
            "expired_entries": expired,
            "total_size_bytes": total_size,
            "by_provider": by_provider,
        }

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
```

## Cache Key Strategy

### Metadata Cache Keys

Provider results are cached with namespaced keys:

```
{provider}:{operation}:{params}

Examples:
igdb:search:mario:snes
screenscraper:get_by_id:1234
retroachievements:hash:abc123def456
```

### Artwork Cache Keys

Artwork uses URL-based keys with SHA256 hashing:

```
Original URL: https://images.igdb.com/igdb/image/upload/t_cover_big/abc123.jpg
Cache key: sha256(url)[:16] = "7f8a9b0c1d2e3f4a"
File path: cache_dir/igdb/7f8a9b0c1d2e3f4a.jpg
```

## Cache Invalidation

### TTL-Based Expiration

All cache entries have a TTL:
- Metadata: Configurable, default 1 hour
- Artwork: Configurable, default 30 days

### Manual Invalidation

```python
# Clear specific key
await cache.delete("igdb:search:mario:snes")

# Clear all entries for a provider
await artwork_cache.clear_provider("steamgriddb")

# Clear all expired entries
await cache.clear_expired()
await artwork_cache.clear_expired()

# Clear entire cache
await cache.clear()
await artwork_cache.clear_all()
```

## Best Practices

### 1. Choose the Right Backend

| Use Case | Recommended Backend |
|----------|---------------------|
| Single instance, ephemeral | Memory |
| Single instance, persistent | SQLite |
| Multiple instances | Redis |
| Testing / debugging | None |

### 2. Set Appropriate TTLs

```python
# Short TTL for frequently changing data
cache = MetadataConfig(
    cache=CacheConfig(ttl=300)  # 5 minutes
)

# Long TTL for stable data (artwork)
artwork_config = ArtworkConfig(
    cache_ttl=2592000  # 30 days
)
```

### 3. Handle Cache Failures Gracefully

```python
async def get_with_fallback(self, key: str) -> Any:
    try:
        cached = await self._cache.get(key)
        if cached:
            return cached
    except Exception as e:
        logger.warning("Cache error: %s", e)
        # Continue without cache

    # Fetch from provider
    result = await self._fetch_from_provider()

    try:
        await self._cache.set(key, result)
    except Exception as e:
        logger.warning("Cache write error: %s", e)

    return result
```

### 4. Monitor Cache Performance

```python
stats = await cache.get_stats()
print(f"Cache hit rate: {stats['hits'] / stats['total']:.2%}")
print(f"Expired entries: {stats['expired_entries']}")

artwork_stats = await artwork_cache.get_stats()
print(f"Cached artwork: {artwork_stats['total_entries']}")
print(f"Cache size: {artwork_stats['total_size_bytes'] / 1024 / 1024:.1f} MB")
```

## Adding Custom Cache Backends

To add a new cache backend:

1. **Create class extending `CacheBackend`**:

```python
class CustomCache(CacheBackend):
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> bool: ...
    async def exists(self, key: str) -> bool: ...
    async def clear(self) -> int: ...
```

2. **Add to cache initialization**:

```python
# core/client.py
match self.config.cache.backend:
    case "custom":
        self._cache = CustomCache(
            **self.config.cache.options
        )
```

3. **Add configuration**:

```python
config = MetadataConfig(
    cache=CacheConfig(
        backend="custom",
        options={"param1": "value1"}
    )
)
```
