"""Platform ID mappings for different metadata providers.

This module provides mappings between UniversalPlatformSlug and
provider-specific platform IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from retro_metadata.platforms.slugs import UniversalPlatformSlug as UPS


@dataclass
class PlatformInfo:
    """Information about a platform across multiple providers.

    Attributes:
        slug: Universal platform slug
        name: Human-readable platform name
        igdb_id: IGDB platform ID (if available)
        mobygames_id: MobyGames platform ID (if available)
        screenscraper_id: ScreenScraper platform ID (if available)
        retroachievements_id: RetroAchievements console ID (if available)
        category: Platform category (Console, Computer, Arcade, etc.)
        generation: Console generation number (-1 for non-console)
        family: Platform family name (Nintendo, Sega, etc.)
    """

    slug: str
    name: str
    igdb_id: int | None = None
    mobygames_id: int | None = None
    screenscraper_id: int | None = None
    retroachievements_id: int | None = None
    category: str = ""
    generation: int = -1
    family: str = ""


class IGDBPlatformData(TypedDict):
    """IGDB platform data structure."""

    id: int
    slug: str
    name: str
    category: str
    generation: int
    family_name: str
    family_slug: str
    url: str
    url_logo: str


class MobyGamesPlatformData(TypedDict):
    """MobyGames platform data structure."""

    id: int
    name: str
    slug: str


# Core platform mappings - commonly used platforms
# Full mappings should be loaded from a configuration file or extracted from RomM
IGDB_PLATFORM_MAP: dict[UPS, int] = {
    UPS._3DO: 50,
    UPS.N3DS: 37,
    UPS.N64: 4,
    UPS.N64DD: 416,
    UPS.ARCADE: 52,
    UPS.ATARI2600: 59,
    UPS.ATARI5200: 66,
    UPS.ATARI7800: 60,
    UPS.C64: 15,
    UPS.DC: 23,
    UPS.DOS: 13,
    UPS.FAMICOM: 99,
    UPS.FDS: 51,
    UPS.GB: 33,
    UPS.GBA: 24,
    UPS.GBC: 22,
    UPS.GENESIS: 29,
    UPS.GAMEGEAR: 35,
    UPS.JAGUAR: 62,
    UPS.LYNX: 61,
    UPS.MAC: 14,
    UPS.MSX: 27,
    UPS.MSX2: 53,
    UPS.NDS: 20,
    UPS.NEO_GEO_CD: 136,
    UPS.NEO_GEO_POCKET: 119,
    UPS.NEO_GEO_POCKET_COLOR: 120,
    UPS.NEOGEOAES: 80,
    UPS.NEOGEOMVS: 79,
    UPS.NES: 18,
    UPS.NGC: 21,
    UPS.PC_FX: 274,
    UPS.PS2: 8,
    UPS.PS3: 9,
    UPS.PS4: 48,
    UPS.PS5: 167,
    UPS.PSP: 38,
    UPS.PSVITA: 46,
    UPS.PSX: 7,
    UPS.SATURN: 32,
    UPS.SEGA32: 30,
    UPS.SEGACD: 78,
    UPS.SFAM: 58,
    UPS.SG1000: 84,
    UPS.SMS: 64,
    UPS.SNES: 19,
    UPS.SUPERGRAFX: 128,
    UPS.SWITCH: 130,
    UPS.TG16: 86,
    UPS.TURBOGRAFX_CD: 150,
    UPS.VECTREX: 70,
    UPS.VIRTUALBOY: 87,
    UPS.WII: 5,
    UPS.WIIU: 41,
    UPS.WIN: 6,
    UPS.WONDERSWAN: 57,
    UPS.WONDERSWAN_COLOR: 123,
    UPS.XBOX: 11,
    UPS.XBOX360: 12,
    UPS.XBOXONE: 49,
    UPS.ZXS: 26,
}

MOBYGAMES_PLATFORM_MAP: dict[UPS, int] = {
    UPS._3DO: 35,
    UPS.N3DS: 101,
    UPS.N64: 9,
    UPS.ARCADE: 143,
    UPS.ATARI2600: 28,
    UPS.ATARI5200: 33,
    UPS.ATARI7800: 34,
    UPS.C64: 27,
    UPS.DC: 8,
    UPS.DOS: 2,
    UPS.FAMICOM: 22,
    UPS.GB: 10,
    UPS.GBA: 12,
    UPS.GBC: 11,
    UPS.GENESIS: 16,
    UPS.GAMEGEAR: 25,
    UPS.JAGUAR: 17,
    UPS.LYNX: 18,
    UPS.MAC: 74,
    UPS.MSX: 57,
    UPS.NDS: 44,
    UPS.NEO_GEO_CD: 54,
    UPS.NEO_GEO_POCKET: 52,
    UPS.NEO_GEO_POCKET_COLOR: 53,
    UPS.NEOGEOAES: 36,
    UPS.NES: 22,
    UPS.NGC: 14,
    UPS.PC_FX: 59,
    UPS.PS2: 7,
    UPS.PS3: 81,
    UPS.PS4: 141,
    UPS.PS5: 288,
    UPS.PSP: 46,
    UPS.PSVITA: 105,
    UPS.PSX: 6,
    UPS.SATURN: 23,
    UPS.SEGA32: 21,
    UPS.SEGACD: 20,
    UPS.SFAM: 15,
    UPS.SG1000: 114,
    UPS.SMS: 26,
    UPS.SNES: 15,
    UPS.SUPERGRAFX: 127,
    UPS.SWITCH: 203,
    UPS.TG16: 40,
    UPS.TURBOGRAFX_CD: 45,
    UPS.VECTREX: 37,
    UPS.VIRTUALBOY: 38,
    UPS.WII: 82,
    UPS.WIIU: 132,
    UPS.WIN: 3,
    UPS.WONDERSWAN: 48,
    UPS.WONDERSWAN_COLOR: 49,
    UPS.XBOX: 13,
    UPS.XBOX360: 69,
    UPS.XBOXONE: 142,
    UPS.ZXS: 41,
}

SCREENSCRAPER_PLATFORM_MAP: dict[UPS, int] = {
    UPS._3DO: 29,
    UPS.N3DS: 17,
    UPS.N64: 14,
    UPS.ARCADE: 75,
    UPS.ATARI2600: 26,
    UPS.ATARI5200: 40,
    UPS.ATARI7800: 41,
    UPS.C64: 66,
    UPS.DC: 23,
    UPS.DOS: 135,
    UPS.FAMICOM: 3,
    UPS.FDS: 106,
    UPS.GB: 9,
    UPS.GBA: 12,
    UPS.GBC: 10,
    UPS.GENESIS: 1,
    UPS.GAMEGEAR: 21,
    UPS.JAGUAR: 27,
    UPS.LYNX: 28,
    UPS.MSX: 113,
    UPS.MSX2: 116,
    UPS.NDS: 15,
    UPS.NEO_GEO_CD: 70,
    UPS.NEO_GEO_POCKET: 25,
    UPS.NEO_GEO_POCKET_COLOR: 82,
    UPS.NEOGEOAES: 142,
    UPS.NES: 3,
    UPS.NGC: 13,
    UPS.PC_FX: 72,
    UPS.PS2: 58,
    UPS.PS3: 59,
    UPS.PSP: 61,
    UPS.PSVITA: 62,
    UPS.PSX: 57,
    UPS.SATURN: 22,
    UPS.SEGA32: 19,
    UPS.SEGACD: 20,
    UPS.SFAM: 4,
    UPS.SG1000: 109,
    UPS.SMS: 2,
    UPS.SNES: 4,
    UPS.SUPERGRAFX: 105,
    UPS.SWITCH: 225,
    UPS.TG16: 31,
    UPS.TURBOGRAFX_CD: 114,
    UPS.VECTREX: 102,
    UPS.VIRTUALBOY: 11,
    UPS.WII: 16,
    UPS.WIIU: 18,
    UPS.WONDERSWAN: 45,
    UPS.WONDERSWAN_COLOR: 46,
    UPS.XBOX: 32,
    UPS.XBOX360: 33,
    UPS.ZXS: 76,
}

RETROACHIEVEMENTS_PLATFORM_MAP: dict[UPS, int] = {
    UPS._3DO: 43,
    UPS.N64: 2,
    UPS.ARCADE: 27,
    UPS.ATARI2600: 25,
    UPS.ATARI7800: 51,
    UPS.DC: 40,
    UPS.FAMICOM: 1,
    UPS.GB: 4,
    UPS.GBA: 5,
    UPS.GBC: 6,
    UPS.GENESIS: 1,
    UPS.GAMEGEAR: 15,
    UPS.JAGUAR: 17,
    UPS.LYNX: 13,
    UPS.MSX: 29,
    UPS.NDS: 18,
    UPS.NEO_GEO_POCKET: 14,
    UPS.NEOGEOAES: 27,
    UPS.NES: 7,
    UPS.NGC: 16,
    UPS.PC_FX: 49,
    UPS.PS2: 21,
    UPS.PSP: 41,
    UPS.PSX: 12,
    UPS.SATURN: 39,
    UPS.SEGA32: 10,
    UPS.SEGACD: 9,
    UPS.SFAM: 3,
    UPS.SG1000: 33,
    UPS.SMS: 11,
    UPS.SNES: 3,
    UPS.SUPERGRAFX: 8,
    UPS.TG16: 8,
    UPS.VECTREX: 46,
    UPS.VIRTUALBOY: 28,
    UPS.WONDERSWAN: 53,
}


def get_igdb_platform_id(slug: str | UPS) -> int | None:
    """Get the IGDB platform ID for a universal platform slug.

    Args:
        slug: Universal platform slug or UPS enum value

    Returns:
        IGDB platform ID or None if not found
    """
    if isinstance(slug, str):
        try:
            slug = UPS(slug)
        except ValueError:
            return None
    return IGDB_PLATFORM_MAP.get(slug)


def get_mobygames_platform_id(slug: str | UPS) -> int | None:
    """Get the MobyGames platform ID for a universal platform slug.

    Args:
        slug: Universal platform slug or UPS enum value

    Returns:
        MobyGames platform ID or None if not found
    """
    if isinstance(slug, str):
        try:
            slug = UPS(slug)
        except ValueError:
            return None
    return MOBYGAMES_PLATFORM_MAP.get(slug)


def get_screenscraper_platform_id(slug: str | UPS) -> int | None:
    """Get the ScreenScraper platform ID for a universal platform slug.

    Args:
        slug: Universal platform slug or UPS enum value

    Returns:
        ScreenScraper platform ID or None if not found
    """
    if isinstance(slug, str):
        try:
            slug = UPS(slug)
        except ValueError:
            return None
    return SCREENSCRAPER_PLATFORM_MAP.get(slug)


def get_retroachievements_platform_id(slug: str | UPS) -> int | None:
    """Get the RetroAchievements console ID for a universal platform slug.

    Args:
        slug: Universal platform slug or UPS enum value

    Returns:
        RetroAchievements console ID or None if not found
    """
    if isinstance(slug, str):
        try:
            slug = UPS(slug)
        except ValueError:
            return None
    return RETROACHIEVEMENTS_PLATFORM_MAP.get(slug)


def get_platform_info(slug: str | UPS) -> PlatformInfo | None:
    """Get comprehensive platform information for a universal platform slug.

    Args:
        slug: Universal platform slug or UPS enum value

    Returns:
        PlatformInfo with all available provider IDs, or None if slug is invalid
    """
    if isinstance(slug, str):
        try:
            ups = UPS(slug)
        except ValueError:
            return None
    else:
        ups = slug
        slug = ups.value

    # Get a human-readable name from the slug
    name = slug.replace("-", " ").replace("_", " ").title()

    return PlatformInfo(
        slug=slug,
        name=name,
        igdb_id=get_igdb_platform_id(ups),
        mobygames_id=get_mobygames_platform_id(ups),
        screenscraper_id=get_screenscraper_platform_id(ups),
        retroachievements_id=get_retroachievements_platform_id(ups),
    )


def slug_from_igdb_id(igdb_id: int) -> UPS | None:
    """Get the universal platform slug from an IGDB platform ID.

    Args:
        igdb_id: IGDB platform ID

    Returns:
        UniversalPlatformSlug or None if not found
    """
    for slug, pid in IGDB_PLATFORM_MAP.items():
        if pid == igdb_id:
            return slug
    return None


def slug_from_mobygames_id(moby_id: int) -> UPS | None:
    """Get the universal platform slug from a MobyGames platform ID.

    Args:
        moby_id: MobyGames platform ID

    Returns:
        UniversalPlatformSlug or None if not found
    """
    for slug, pid in MOBYGAMES_PLATFORM_MAP.items():
        if pid == moby_id:
            return slug
    return None
