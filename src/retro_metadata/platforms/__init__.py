"""Platform definitions and mappings for retro-metadata."""

from retro_metadata.platforms.mappings import (
    PlatformInfo,
    get_igdb_platform_id,
    get_mobygames_platform_id,
    get_platform_info,
    get_screenscraper_platform_id,
)
from retro_metadata.platforms.slugs import UniversalPlatformSlug

__all__ = [
    "UniversalPlatformSlug",
    "get_igdb_platform_id",
    "get_mobygames_platform_id",
    "get_screenscraper_platform_id",
    "get_platform_info",
    "PlatformInfo",
]
