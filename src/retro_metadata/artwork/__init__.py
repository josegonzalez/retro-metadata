"""Artwork downloading module for retro-metadata.

This module provides functionality for downloading, caching, and managing
game artwork from various metadata providers.

Example usage:
    from retro_metadata import MetadataClient, MetadataConfig
    from retro_metadata.artwork import ArtworkDownloader, ArtworkConfig

    config = MetadataConfig(...)

    async with MetadataClient(config) as client:
        artwork_config = ArtworkConfig(
            cache_enabled=True,
            artwork_types=["cover", "screenshots"],
        )

        async with ArtworkDownloader(client, artwork_config) as downloader:
            # Download artwork for a single game
            result = await client.identify("Mario.sfc", platform="snes")
            paths = await downloader.download_for_game(
                result,
                output_dir=Path("./artwork"),
            )

            # Download with cross-provider matching
            paths = await downloader.download_with_fallback(
                filename="Mario.sfc",
                platform="snes",
                output_dir=Path("./artwork"),
                identify_providers=["igdb"],
                artwork_providers=["steamgriddb"],
            )

            # Batch download
            batch_result = await downloader.download_batch(
                directory=Path("./roms/snes"),
                platform="snes",
                output_dir=Path("./artwork"),
                recursive=True,
            )
"""

from retro_metadata.artwork.cache import ArtworkCache, CachedArtwork
from retro_metadata.artwork.config import ARTWORK_TYPES, ArtworkConfig
from retro_metadata.artwork.downloader import (
    ALL_ROM_EXTENSIONS,
    ROM_EXTENSIONS,
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
    InvalidArtworkTypeError,
)
from retro_metadata.artwork.utils import (
    generate_output_filename,
    get_extension_from_content_type,
    get_extension_from_url,
    get_image_dimensions,
    hash_url,
    sanitize_filename,
    transform_url_for_size,
)

__all__ = [
    # Config
    "ArtworkConfig",
    "ARTWORK_TYPES",
    # Cache
    "ArtworkCache",
    "CachedArtwork",
    # Downloader
    "ArtworkDownloader",
    "ArtworkDownloadResult",
    "ArtworkBatchResult",
    # Exceptions
    "ArtworkError",
    "ArtworkDownloadError",
    "ArtworkCacheError",
    "ArtworkNotFoundError",
    "ArtworkTimeoutError",
    "InvalidArtworkTypeError",
    # Utilities
    "hash_url",
    "get_extension_from_url",
    "get_extension_from_content_type",
    "get_image_dimensions",
    "transform_url_for_size",
    "generate_output_filename",
    "sanitize_filename",
    # ROM Extensions
    "ROM_EXTENSIONS",
    "ALL_ROM_EXTENSIONS",
]
