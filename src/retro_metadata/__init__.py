"""
retro-metadata: A comprehensive metadata scraping library for retro video games.

This library provides a unified interface for fetching game metadata from multiple
sources including IGDB, MobyGames, ScreenScraper, RetroAchievements, SteamGridDB,
and more.

Example usage:
    from retro_metadata import MetadataClient, MetadataConfig

    config = MetadataConfig(
        igdb=ProviderConfig(
            enabled=True,
            credentials={"client_id": "...", "client_secret": "..."}
        )
    )

    async with MetadataClient(config) as client:
        results = await client.search("Super Mario World", platform="snes")
        for result in results:
            print(result.name, result.provider)
"""

from retro_metadata.artwork.config import ArtworkConfig
from retro_metadata.artwork.downloader import (
    ArtworkBatchResult,
    ArtworkDownloader,
    ArtworkDownloadResult,
)
from retro_metadata.artwork.exceptions import (
    ArtworkCacheError,
    ArtworkDownloadError,
    ArtworkError,
    ArtworkNotFoundError,
    ArtworkTimeoutError,
)
from retro_metadata.core.client import MetadataClient
from retro_metadata.core.config import CacheConfig, MetadataConfig, ProviderConfig
from retro_metadata.core.exceptions import (
    MetadataError,
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderNotFoundError,
    ProviderRateLimitError,
)
from retro_metadata.core.matching import find_best_match, normalize_search_term
from retro_metadata.platforms.slugs import UniversalPlatformSlug
from retro_metadata.types.common import GameResult, SearchResult

__version__ = "1.0.0"

__all__ = [
    # Core
    "CacheConfig",
    "MetadataClient",
    "MetadataConfig",
    "ProviderConfig",
    # Artwork
    "ArtworkConfig",
    "ArtworkDownloader",
    "ArtworkDownloadResult",
    "ArtworkBatchResult",
    # Exceptions
    "MetadataError",
    "ProviderAuthenticationError",
    "ProviderConnectionError",
    "ProviderNotFoundError",
    "ProviderRateLimitError",
    "ArtworkError",
    "ArtworkDownloadError",
    "ArtworkCacheError",
    "ArtworkNotFoundError",
    "ArtworkTimeoutError",
    # Utilities
    "find_best_match",
    "normalize_search_term",
    # Types
    "GameResult",
    "SearchResult",
    "UniversalPlatformSlug",
]
