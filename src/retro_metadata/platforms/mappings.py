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
# Platform IDs sourced from RomM project for compatibility
IGDB_PLATFORM_MAP: dict[UPS, int] = {
    # 3DO / Panasonic
    UPS._3DO: 50,
    # Amstrad
    UPS.ACPC: 25,
    UPS.AMSTRAD_GX4000: 158,
    # Android / iOS / Mobile
    UPS.ANDROID: 34,
    UPS.IOS: 39,
    # Apple
    UPS.APPLEII: 75,
    UPS.APPLE_IIGS: 115,
    UPS.MAC: 14,
    # Arcade
    UPS.ARCADE: 52,
    UPS.CPS1: 52,
    UPS.CPS2: 52,
    UPS.CPS3: 52,
    UPS.NEOGEOMVS: 79,
    UPS.NEOGEOAES: 80,
    # Atari
    UPS.ATARI2600: 59,
    UPS.ATARI5200: 66,
    UPS.ATARI7800: 60,
    UPS.ATARI8BIT: 65,
    UPS.ATARI_JAGUAR_CD: 171,
    UPS.ATARI_ST: 63,
    UPS.ATARI_XEGS: 111,
    UPS.JAGUAR: 62,
    UPS.LYNX: 61,
    # Bandai
    UPS.WONDERSWAN: 57,
    UPS.WONDERSWAN_COLOR: 123,
    # Commodore
    UPS.AMIGA: 16,
    UPS.AMIGA_CD: 114,
    UPS.AMIGA_CD32: 117,
    UPS.C128: 15,
    UPS.C16: 93,
    UPS.C64: 15,
    UPS.C_PLUS_4: 94,
    UPS.COMMODORE_CDTV: 116,
    UPS.VIC_20: 71,
    # DOS / PC
    UPS.DOS: 13,
    UPS.LINUX: 3,
    UPS.WIN: 6,
    UPS.WIN3X: 6,
    # Microsoft Xbox
    UPS.XBOX: 11,
    UPS.XBOX360: 12,
    UPS.XBOXONE: 49,
    UPS.SERIES_X_S: 169,
    # NEC
    UPS.PC_8800_SERIES: 125,
    UPS.PC_9800_SERIES: 149,
    UPS.PC_FX: 274,
    UPS.SUPERGRAFX: 128,
    UPS.TG16: 86,
    UPS.TURBOGRAFX_CD: 150,
    # Neo Geo
    UPS.NEO_GEO_CD: 136,
    UPS.NEO_GEO_POCKET: 119,
    UPS.NEO_GEO_POCKET_COLOR: 120,
    # Nintendo Consoles
    UPS.FAMICOM: 99,
    UPS.FDS: 51,
    UPS.N64: 4,
    UPS.N64DD: 416,
    UPS.NES: 18,
    UPS.NGC: 21,
    UPS.SATELLAVIEW: 58,
    UPS.SFAM: 58,
    UPS.SNES: 19,
    UPS.SWITCH: 130,
    UPS.WII: 5,
    UPS.WIIU: 41,
    # Nintendo Handhelds
    UPS.GB: 33,
    UPS.GBA: 24,
    UPS.GBC: 22,
    UPS.N3DS: 37,
    UPS.NDS: 20,
    UPS.NEW_NINTENDON3DS: 137,
    UPS.NINTENDO_DSI: 20,
    UPS.VIRTUALBOY: 87,
    # Philips
    UPS.PHILIPS_CD_I: 117,
    # Sega
    UPS.DC: 23,
    UPS.GAMEGEAR: 35,
    UPS.GENESIS: 29,
    UPS.SATURN: 32,
    UPS.SEGA32: 30,
    UPS.SEGACD: 78,
    UPS.SEGACD32: 78,
    UPS.SG1000: 84,
    UPS.SMS: 64,
    UPS.SEGA_PICO: 339,
    # Sharp
    UPS.SHARP_X68000: 112,
    UPS.X1: 77,
    # SNK
    UPS.HYPER_NEO_GEO_64: 79,
    # Sony PlayStation
    UPS.POCKETSTATION: 76,
    UPS.PS2: 8,
    UPS.PS3: 9,
    UPS.PS4: 48,
    UPS.PS5: 167,
    UPS.PSP: 38,
    UPS.PSVITA: 46,
    UPS.PSVR: 165,
    UPS.PSVR2: 390,
    UPS.PSX: 7,
    # Other Computers
    UPS.BBCMICRO: 69,
    UPS.MSX: 27,
    UPS.MSX2: 53,
    UPS.MSX2PLUS: 161,
    UPS.ZX80: 26,
    UPS.ZX81: 26,
    UPS.ZXS: 26,
    # Other Consoles
    UPS.COLECOVISION: 68,
    UPS.FAIRCHILD_CHANNEL_F: 127,
    UPS.INTELLIVISION: 67,
    UPS.ODYSSEY_2: 133,
    UPS.VECTREX: 70,
    # Other Handhelds
    UPS.GAMATE: 340,
    UPS.GAME_DOT_COM: 122,
    UPS.GIZMONDO: 121,
    UPS.NGAGE: 42,
    UPS.PLAYDATE: 308,
    UPS.POKEMON_MINI: 207,
    UPS.SUPERVISION: 343,
    # Modern / Cloud
    UPS.STADIA: 170,
    UPS.AMAZON_FIRE_TV: 132,
    UPS.OUYA: 72,
}

MOBYGAMES_PLATFORM_MAP: dict[UPS, int] = {
    # 3DO / Panasonic
    UPS._3DO: 35,
    # Amstrad
    UPS.ACPC: 60,
    UPS.AMSTRAD_GX4000: 198,
    UPS.AMSTRAD_PCW: 136,
    # Android / iOS / Mobile
    UPS.ANDROID: 91,
    UPS.IOS: 86,
    UPS.J2ME: 64,
    UPS.BLACKBERRY: 90,
    UPS.BREW: 63,
    UPS.NGAGE: 32,
    UPS.PALM_OS: 51,
    UPS.SYMBIAN: 67,
    UPS.WINDOWS_MOBILE: 56,
    # Apple
    UPS.APPLEII: 31,
    UPS.APPLE_IIGS: 39,
    UPS.MAC: 74,
    # Arcade
    UPS.ARCADE: 143,
    UPS.CPS1: 143,
    UPS.CPS2: 143,
    UPS.CPS3: 143,
    UPS.NEOGEOMVS: 36,
    UPS.NEOGEOAES: 36,
    # Atari
    UPS.ATARI2600: 28,
    UPS.ATARI5200: 33,
    UPS.ATARI7800: 34,
    UPS.ATARI8BIT: 39,
    UPS.ATARI800: 39,
    UPS.ATARI_JAGUAR_CD: 17,
    UPS.ATARI_ST: 24,
    UPS.ATARI_XEGS: 39,
    UPS.JAGUAR: 17,
    UPS.LYNX: 18,
    # Bandai
    UPS.WONDERSWAN: 48,
    UPS.WONDERSWAN_COLOR: 49,
    UPS.PLAYDIA: 161,
    # Coleco
    UPS.COLECOADAM: 84,
    UPS.COLECOVISION: 29,
    # Commodore
    UPS.AMIGA: 19,
    UPS.AMIGA_CD: 56,
    UPS.AMIGA_CD32: 56,
    UPS.C128: 61,
    UPS.C16: 115,
    UPS.C64: 27,
    UPS.C_PLUS_4: 115,
    UPS.COMMODORE_CDTV: 83,
    UPS.VIC_20: 43,
    # DOS / PC / Linux
    UPS.DOS: 2,
    UPS.LINUX: 1,
    UPS.WIN: 3,
    UPS.WIN3X: 5,
    UPS.PC_BOOTER: 4,
    UPS.CPM: 52,
    UPS.OS2: 85,
    # Microsoft Xbox
    UPS.XBOX: 13,
    UPS.XBOX360: 69,
    UPS.XBOXONE: 142,
    UPS.SERIES_X_S: 289,
    # NEC
    UPS.PC_8800_SERIES: 94,
    UPS.PC_9800_SERIES: 95,
    UPS.PC_FX: 59,
    UPS.SUPERGRAFX: 127,
    UPS.TG16: 40,
    UPS.TURBOGRAFX_CD: 45,
    # Neo Geo
    UPS.NEO_GEO_CD: 54,
    UPS.NEO_GEO_POCKET: 52,
    UPS.NEO_GEO_POCKET_COLOR: 53,
    # Nintendo Consoles
    UPS.FAMICOM: 22,
    UPS.FDS: 22,
    UPS.N64: 9,
    UPS.N64DD: 9,
    UPS.NES: 22,
    UPS.NGC: 14,
    UPS.SATELLAVIEW: 15,
    UPS.SFAM: 15,
    UPS.SNES: 15,
    UPS.SWITCH: 203,
    UPS.WII: 82,
    UPS.WIIU: 132,
    # Nintendo Handhelds
    UPS.GB: 10,
    UPS.GBA: 12,
    UPS.GBC: 11,
    UPS.N3DS: 101,
    UPS.NDS: 44,
    UPS.NEW_NINTENDON3DS: 174,
    UPS.NINTENDO_DSI: 87,
    UPS.VIRTUALBOY: 38,
    UPS.POKEMON_MINI: 152,
    UPS.G_AND_W: 98,
    # Philips
    UPS.PHILIPS_CD_I: 73,
    UPS.VIDEOPAC_G7400: 128,
    UPS.ODYSSEY_2: 78,
    # Sega
    UPS.DC: 8,
    UPS.GAMEGEAR: 25,
    UPS.GENESIS: 16,
    UPS.SATURN: 23,
    UPS.SEGA32: 21,
    UPS.SEGACD: 20,
    UPS.SEGACD32: 20,
    UPS.SG1000: 114,
    UPS.SMS: 26,
    UPS.SC3000: 114,
    UPS.SEGA_PICO: 103,
    # Sharp
    UPS.SHARP_X68000: 106,
    UPS.X1: 121,
    UPS.SHARP_MZ_80K7008001500: 125,
    UPS.SHARP_MZ_2200: 126,
    # Sinclair
    UPS.ZXS: 41,
    UPS.ZX80: 119,
    UPS.ZX81: 120,
    UPS.SINCLAIR_QL: 62,
    UPS.TIMEX_SINCLAIR_2068: 176,
    # SNK
    UPS.HYPER_NEO_GEO_64: 36,
    # Sony PlayStation
    UPS.POCKETSTATION: 147,
    UPS.PS2: 7,
    UPS.PS3: 81,
    UPS.PS4: 141,
    UPS.PS5: 288,
    UPS.PSP: 46,
    UPS.PSVITA: 105,
    UPS.PSVR: 286,
    UPS.PSVR2: 286,
    UPS.PSX: 6,
    # Other Computers
    UPS.BBCMICRO: 92,
    UPS.ACORN_ELECTRON: 93,
    UPS.ACORN_ARCHIMEDES: 117,
    UPS.MSX: 57,
    UPS.MSX2: 57,
    UPS.MSX2PLUS: 57,
    UPS.MSX_TURBO: 182,
    UPS.FM_TOWNS: 102,
    UPS.FM_7: 126,
    UPS.DRAGON_32_SLASH_64: 79,
    UPS.TRS_80: 58,
    UPS.TRS_80_COLOR_COMPUTER: 62,
    UPS.ATOM: 129,
    UPS.SAM_COUPE: 124,
    UPS.TATUNG_EINSTEIN: 143,
    UPS.THOMSON_TO: 134,
    UPS.THOMSON_MO5: 144,
    UPS.ORIC: 111,
    UPS.ENTERPRISE: 113,
    UPS.SPECTRAVIDEO: 120,
    UPS.AQUARIUS: 97,
    UPS.TI_994A: 47,
    UPS.TI_99: 47,
    # Other Consoles
    UPS.FAIRCHILD_CHANNEL_F: 76,
    UPS.INTELLIVISION: 30,
    UPS.VECTREX: 37,
    UPS.ARCADIA_2001: 162,
    UPS.RCA_STUDIO_II: 96,
    UPS.ASTROCADE: 160,
    UPS.CREATIVISION: 212,
    UPS.EPOCH_CASSETTE_VISION: 193,
    UPS.EPOCH_SUPER_CASSETTE_VISION: 212,
    UPS.INTERTON_VC_4000: 139,
    UPS.VC_4000: 139,
    UPS.LASERACTIVE: 163,
    UPS.CASIO_LOOPY: 159,
    UPS.CASIO_PV_1000: 212,
    # Other Handhelds
    UPS.GAMATE: 189,
    UPS.GAME_DOT_COM: 50,
    UPS.GIZMONDO: 55,
    UPS.SUPERVISION: 109,
    UPS.MICROVISION: 89,
    UPS.MEGA_DUCK_SLASH_COUGAR_BOY: 129,
    UPS.EPOCH_GAME_POCKET_COMPUTER: 194,
    # Modern / Cloud
    UPS.STADIA: 273,
    UPS.AMAZON_FIRE_TV: 159,
    UPS.OUYA: 144,
    UPS.PLAYDATE: 298,
    UPS.EVERCADE: 294,
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
