"""SQLite-based artwork cache for storing downloaded images."""

from __future__ import annotations

import asyncio
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from retro_metadata.artwork.config import ArtworkConfig
from retro_metadata.artwork.exceptions import ArtworkCacheError
from retro_metadata.artwork.utils import (
    get_extension_from_content_type,
    get_extension_from_url,
    get_image_dimensions,
    hash_url,
)


@dataclass
class CachedArtwork:
    """Represents a cached artwork entry.

    Attributes:
        url: Original artwork URL
        provider: Provider name
        path: Path to cached file
        width: Image width in pixels
        height: Image height in pixels
        download_date: Unix timestamp of download
        expires_at: Unix timestamp when cache entry expires
    """

    url: str
    provider: str
    path: Path
    width: int | None
    height: int | None
    download_date: int
    expires_at: int


class ArtworkCache:
    """SQLite-based cache for artwork files.

    Stores artwork metadata in SQLite and actual image files in a directory structure:
    cache_dir/
        index.db
        igdb/
            a1b2c3d4e5f6.png
        steamgriddb/
            b2c3d4e5f6a1.jpg
    """

    def __init__(self, config: ArtworkConfig) -> None:
        """Initialize the artwork cache.

        Args:
            config: Artwork configuration
        """
        self.config = config
        self._cache_dir = config.get_cache_dir()
        self._db_path = self._cache_dir / "index.db"
        self._conn: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()

    async def _ensure_initialized(self) -> None:
        """Ensure cache directory and database are initialized."""
        if self._conn is not None:
            return

        async with self._lock:
            if self._conn is not None:
                return

            # Create cache directory
            self._cache_dir.mkdir(parents=True, exist_ok=True)

            # Initialize database
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._create_tables()

    def _create_tables(self) -> None:
        """Create necessary database tables."""
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artwork_cache (
                url TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                path TEXT NOT NULL,
                width INTEGER,
                height INTEGER,
                download_date INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_provider ON artwork_cache(provider)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at ON artwork_cache(expires_at)
        """)
        self._conn.commit()

    async def get(self, url: str) -> CachedArtwork | None:
        """Get a cached artwork entry.

        Args:
            url: The artwork URL

        Returns:
            CachedArtwork if found and not expired, None otherwise
        """
        if not self.config.cache_enabled:
            return None

        await self._ensure_initialized()

        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM artwork_cache WHERE url = ?",
            (url,),
        )
        row = cursor.fetchone()

        if row is None:
            return None

        # Check if expired
        if row["expires_at"] < int(time.time()):
            await self.delete(url)
            return None

        # Check if file still exists
        path = Path(row["path"])
        if not path.exists():
            await self.delete(url)
            return None

        return CachedArtwork(
            url=row["url"],
            provider=row["provider"],
            path=path,
            width=row["width"],
            height=row["height"],
            download_date=row["download_date"],
            expires_at=row["expires_at"],
        )

    async def put(
        self,
        url: str,
        provider: str,
        data: bytes,
        content_type: str | None = None,
    ) -> CachedArtwork:
        """Store artwork in the cache.

        Args:
            url: The artwork URL
            provider: Provider name
            data: Image data
            content_type: Optional Content-Type header value

        Returns:
            CachedArtwork entry for the stored file
        """
        if not self.config.cache_enabled:
            raise ArtworkCacheError("put", "Cache is disabled")

        await self._ensure_initialized()

        # Determine file extension
        if content_type:
            extension = get_extension_from_content_type(content_type)
        else:
            extension = get_extension_from_url(url)

        # Generate cache filename
        url_hash = hash_url(url)
        filename = f"{url_hash}{extension}"

        # Create provider subdirectory
        provider_dir = self._cache_dir / provider
        provider_dir.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path = provider_dir / filename
        file_path.write_bytes(data)

        # Get image dimensions
        dimensions = get_image_dimensions(data)
        width = dimensions[0] if dimensions else None
        height = dimensions[1] if dimensions else None

        # Calculate timestamps
        now = int(time.time())
        expires_at = now + self.config.cache_ttl

        # Store in database
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO artwork_cache
            (url, provider, path, width, height, download_date, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (url, provider, str(file_path), width, height, now, expires_at),
        )
        self._conn.commit()

        return CachedArtwork(
            url=url,
            provider=provider,
            path=file_path,
            width=width,
            height=height,
            download_date=now,
            expires_at=expires_at,
        )

    async def delete(self, url: str) -> bool:
        """Delete a cached artwork entry.

        Args:
            url: The artwork URL

        Returns:
            True if entry was deleted, False if not found
        """
        await self._ensure_initialized()

        cursor = self._conn.cursor()

        # Get file path first
        cursor.execute("SELECT path FROM artwork_cache WHERE url = ?", (url,))
        row = cursor.fetchone()

        if row is None:
            return False

        # Delete file
        path = Path(row["path"])
        if path.exists():
            path.unlink()

        # Delete database entry
        cursor.execute("DELETE FROM artwork_cache WHERE url = ?", (url,))
        self._conn.commit()

        return True

    async def get_or_download(
        self,
        url: str,
        provider: str,
        download_func: Callable[[], bytes] | Callable[[], tuple[bytes, str | None]],
    ) -> CachedArtwork:
        """Get artwork from cache or download if not cached.

        Args:
            url: The artwork URL
            provider: Provider name
            download_func: Async function that downloads the artwork and returns
                          either bytes or (bytes, content_type)

        Returns:
            CachedArtwork entry
        """
        # Try cache first
        if self.config.cache_enabled:
            cached = await self.get(url)
            if cached is not None:
                return cached

        # Download
        result = await download_func()

        if isinstance(result, tuple):
            data, content_type = result
        else:
            data = result
            content_type = None

        # Store in cache if enabled
        if self.config.cache_enabled:
            return await self.put(url, provider, data, content_type)

        # Return uncached result
        return CachedArtwork(
            url=url,
            provider=provider,
            path=Path(""),  # No path for uncached
            width=None,
            height=None,
            download_date=int(time.time()),
            expires_at=0,
        )

    async def clear_provider(self, provider: str) -> int:
        """Clear all cached artwork for a specific provider.

        Args:
            provider: Provider name

        Returns:
            Number of entries cleared
        """
        await self._ensure_initialized()

        cursor = self._conn.cursor()

        # Get all paths for provider
        cursor.execute("SELECT path FROM artwork_cache WHERE provider = ?", (provider,))
        rows = cursor.fetchall()

        # Delete files
        for row in rows:
            path = Path(row["path"])
            if path.exists():
                path.unlink()

        # Delete provider directory if empty
        provider_dir = self._cache_dir / provider
        if provider_dir.exists() and not any(provider_dir.iterdir()):
            provider_dir.rmdir()

        # Delete database entries
        cursor.execute("DELETE FROM artwork_cache WHERE provider = ?", (provider,))
        self._conn.commit()

        return len(rows)

    async def clear_expired(self) -> int:
        """Clear all expired cache entries.

        Returns:
            Number of entries cleared
        """
        await self._ensure_initialized()

        now = int(time.time())
        cursor = self._conn.cursor()

        # Get all expired entries
        cursor.execute("SELECT path FROM artwork_cache WHERE expires_at < ?", (now,))
        rows = cursor.fetchall()

        # Delete files
        for row in rows:
            path = Path(row["path"])
            if path.exists():
                path.unlink()

        # Delete database entries
        cursor.execute("DELETE FROM artwork_cache WHERE expires_at < ?", (now,))
        self._conn.commit()

        return len(rows)

    async def clear_all(self) -> int:
        """Clear all cached artwork.

        Returns:
            Number of entries cleared
        """
        await self._ensure_initialized()

        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM artwork_cache")
        count = cursor.fetchone()[0]

        # Delete all provider directories
        for item in self._cache_dir.iterdir():
            if item.is_dir() and item.name != "index.db":
                shutil.rmtree(item)

        # Clear database
        cursor.execute("DELETE FROM artwork_cache")
        self._conn.commit()

        return count

    async def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        await self._ensure_initialized()

        cursor = self._conn.cursor()

        # Total entries
        cursor.execute("SELECT COUNT(*) FROM artwork_cache")
        total = cursor.fetchone()[0]

        # Entries by provider
        cursor.execute(
            "SELECT provider, COUNT(*) as count FROM artwork_cache GROUP BY provider"
        )
        by_provider = {row["provider"]: row["count"] for row in cursor.fetchall()}

        # Expired entries
        now = int(time.time())
        cursor.execute("SELECT COUNT(*) FROM artwork_cache WHERE expires_at < ?", (now,))
        expired = cursor.fetchone()[0]

        # Calculate total size
        total_size = 0
        cursor.execute("SELECT path FROM artwork_cache")
        for row in cursor.fetchall():
            path = Path(row["path"])
            if path.exists():
                total_size += path.stat().st_size

        return {
            "total_entries": total,
            "by_provider": by_provider,
            "expired_entries": expired,
            "total_size_bytes": total_size,
            "cache_dir": str(self._cache_dir),
        }

    async def close(self) -> None:
        """Close the cache connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
