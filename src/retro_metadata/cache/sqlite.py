"""SQLite cache backend implementation."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from retro_metadata.cache.base import CacheBackend


class SQLiteCache(CacheBackend):
    """SQLite-based cache backend.

    This cache backend uses SQLite for persistent local caching.

    Args:
        db_path: Path to the SQLite database file
        default_ttl: Default TTL in seconds (default: 3600)
        table_name: Name of the cache table (default: "cache")

    Example:
        cache = SQLiteCache("cache.db")
        await cache.set("key", {"data": "value"})
        result = await cache.get("key")
    """

    def __init__(
        self,
        db_path: str | Path,
        default_ttl: int = 3600,
        table_name: str = "cache",
    ) -> None:
        self._db_path = str(db_path)
        self._default_ttl = default_ttl
        self._table_name = table_name
        self._connection = None

    async def _get_connection(self):
        """Get or create the database connection."""
        if self._connection is None:
            try:
                import aiosqlite
            except ImportError:
                raise ImportError(
                    "aiosqlite is required for SQLiteCache. "
                    "Install with: pip install retro-metadata[sqlite]"
                )

            self._connection = await aiosqlite.connect(self._db_path)
            await self._create_table()
        return self._connection

    async def _create_table(self) -> None:
        """Create the cache table if it doesn't exist."""
        conn = await self._get_connection()
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._table_name} (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at REAL
            )
        """)
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{self._table_name}_expires
            ON {self._table_name} (expires_at)
        """)
        await conn.commit()

    def _serialize(self, value: Any) -> str:
        """Serialize a value for storage."""
        return json.dumps(value)

    def _deserialize(self, data: str | None) -> Any | None:
        """Deserialize a stored value."""
        if data is None:
            return None
        return json.loads(data)

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache.

        Args:
            key: The cache key

        Returns:
            The cached value, or None if not found or expired
        """
        conn = await self._get_connection()
        cursor = await conn.execute(
            f"""
            SELECT value FROM {self._table_name}
            WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
            """,
            (key, time.time()),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._deserialize(row[0])

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
        serialized = self._serialize(value)

        conn = await self._get_connection()
        await conn.execute(
            f"""
            INSERT OR REPLACE INTO {self._table_name} (key, value, expires_at)
            VALUES (?, ?, ?)
            """,
            (key, serialized, expires_at),
        )
        await conn.commit()

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: The cache key

        Returns:
            True if the key was deleted, False if it didn't exist
        """
        conn = await self._get_connection()
        cursor = await conn.execute(
            f"DELETE FROM {self._table_name} WHERE key = ?",
            (key,),
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: The cache key

        Returns:
            True if the key exists and hasn't expired
        """
        conn = await self._get_connection()
        cursor = await conn.execute(
            f"""
            SELECT 1 FROM {self._table_name}
            WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
            """,
            (key, time.time()),
        )
        row = await cursor.fetchone()
        return row is not None

    async def clear(self) -> None:
        """Clear all entries from the cache."""
        conn = await self._get_connection()
        await conn.execute(f"DELETE FROM {self._table_name}")
        await conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache.

        Returns:
            Number of entries removed
        """
        conn = await self._get_connection()
        cursor = await conn.execute(
            f"DELETE FROM {self._table_name} WHERE expires_at <= ?",
            (time.time(),),
        )
        await conn.commit()
        return cursor.rowcount

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        conn = await self._get_connection()

        # Total count
        cursor = await conn.execute(f"SELECT COUNT(*) FROM {self._table_name}")
        total = (await cursor.fetchone())[0]

        # Expired count
        cursor = await conn.execute(
            f"SELECT COUNT(*) FROM {self._table_name} WHERE expires_at <= ?",
            (time.time(),),
        )
        expired = (await cursor.fetchone())[0]

        return {
            "total_entries": total,
            "expired_entries": expired,
            "valid_entries": total - expired,
            "default_ttl": self._default_ttl,
        }
