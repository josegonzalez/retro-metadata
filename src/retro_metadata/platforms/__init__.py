"""Platform definitions and mappings for retro-metadata."""

from retro_metadata.platforms.slugs import UniversalPlatformSlug
from retro_metadata.platforms.mappings import (
    get_igdb_platform_id,
    get_mobygames_platform_id,
    get_screenscraper_platform_id,
    get_platform_info,
    PlatformInfo,
)

__all__ = [
    "UniversalPlatformSlug",
    "get_igdb_platform_id",
    "get_mobygames_platform_id",
    "get_screenscraper_platform_id",
    "get_platform_info",
    "PlatformInfo",
]
