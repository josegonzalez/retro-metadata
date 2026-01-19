"""HowLongToBeat metadata provider implementation."""

from __future__ import annotations

import contextlib
import json
import logging
import re
from typing import TYPE_CHECKING, Any, Final

import httpx

from retro_metadata.core.exceptions import (
    ProviderConnectionError,
)
from retro_metadata.platforms.slugs import UniversalPlatformSlug as UPS
from retro_metadata.providers.base import MetadataProvider
from retro_metadata.types.common import (
    Artwork,
    GameMetadata,
    GameResult,
    Platform,
    SearchResult,
)

if TYPE_CHECKING:
    from retro_metadata.cache.base import CacheBackend
    from retro_metadata.core.config import ProviderConfig

logger = logging.getLogger(__name__)

# Regex to detect HLTB ID tags in filenames like (hltb-12345)
HLTB_TAG_REGEX: Final = re.compile(r"\(hltb-(\d+)\)", re.IGNORECASE)

# Base URL for images
HLTB_IMAGE_URL: Final = "https://howlongtobeat.com/games/"

# GitHub URL for dynamic search endpoint (HLTB rotates this endpoint)
GITHUB_HLTB_API_URL: Final = "https://raw.githubusercontent.com/rommapp/romm/refs/heads/master/backend/handler/metadata/fixtures/hltb_api_url"

# Fallback search endpoint if GitHub fetch fails
DEFAULT_SEARCH_ENDPOINT: Final = "search"


class HLTBProvider(MetadataProvider):
    """HowLongToBeat metadata provider.

    Provides game completion time data and basic metadata.
    Note: HLTB requires a security token fetched from /api/search/init.
    The search endpoint is dynamically rotated, so we fetch it from GitHub.

    Example:
        config = ProviderConfig(enabled=True)
        provider = HLTBProvider(config)
        results = await provider.search("Super Mario World")
    """

    name = "hltb"

    def __init__(
        self,
        config: ProviderConfig,
        cache: CacheBackend | None = None,
        user_agent: str = "retro-metadata/1.0",
    ) -> None:
        super().__init__(config, cache)
        self._base_url = "https://howlongtobeat.com/api"
        self._user_agent = user_agent
        self._client: httpx.AsyncClient | None = None
        self._min_similarity_score = 0.85
        self._security_token: str | None = None
        self._search_endpoint: str | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "User-Agent": self._user_agent,
                    "Content-Type": "application/json",
                    "Origin": "https://howlongtobeat.com",
                    "Referer": "https://howlongtobeat.com",
                },
                timeout=self.config.timeout,
            )
        return self._client

    async def _fetch_search_endpoint(self) -> str:
        """Fetch the dynamic search endpoint URL from GitHub.

        HLTB rotates the search endpoint, so we fetch the current one
        from a maintained GitHub file or use the fallback.

        Returns:
            The search endpoint path (e.g., "search/abc123")
        """
        if self._search_endpoint:
            return self._search_endpoint

        client = await self._get_client()

        try:
            logger.debug("HLTB: Fetching dynamic search endpoint from GitHub")
            response = await client.get(GITHUB_HLTB_API_URL)
            response.raise_for_status()
            self._search_endpoint = response.text.strip()
            logger.debug("HLTB: Using search endpoint: %s", self._search_endpoint)
            return self._search_endpoint
        except httpx.RequestError as e:
            logger.warning("HLTB: Failed to fetch search endpoint from GitHub: %s", e)
            self._search_endpoint = DEFAULT_SEARCH_ENDPOINT
            return self._search_endpoint

    async def _fetch_security_token(self) -> str | None:
        """Fetch the security token from HLTB.

        HLTB requires a security token for API requests, obtained from /api/search/init.

        Returns:
            The security token, or None if unavailable
        """
        if self._security_token:
            return self._security_token

        client = await self._get_client()

        try:
            logger.debug("HLTB: Fetching security token from /api/search/init")
            response = await client.get(f"{self._base_url}/search/init")
            response.raise_for_status()
            data = response.json()
            self._security_token = data.get("token")
            if self._security_token:
                logger.debug("HLTB: Security token obtained successfully")
            else:
                logger.warning("HLTB: No token in search/init response")
            return self._security_token
        except httpx.RequestError as e:
            logger.warning("HLTB: Failed to fetch security token: %s", e)
            return None

    async def _request(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an API request to HowLongToBeat."""
        client = await self._get_client()

        # Use dynamic search endpoint if this is a search request
        if endpoint == "search":
            endpoint = await self._fetch_search_endpoint()

        url = f"{self._base_url}/{endpoint}"

        # Fetch security token and add to headers if available
        security_token = await self._fetch_security_token()
        headers = {}
        if security_token:
            headers["X-Auth-Token"] = security_token

        logger.debug("HLTB API: POST %s", url)
        if data:
            logger.debug("HLTB API data: %s", data)

        try:
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            result = response.json()

            # Log full response body only when debug logging is enabled
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("HLTB API response:\n%s", json.dumps(result, indent=2, ensure_ascii=False))

            return result
        except httpx.RequestError as e:
            logger.debug("HLTB API error: %s", e)
            raise ProviderConnectionError(self.name, str(e)) from e

    async def search(
        self,
        query: str,
        platform_id: int | None = None,  # noqa: ARG002
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search for games by name.

        Args:
            query: Search query string
            platform_id: Platform filter (optional)
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.is_enabled:
            return []

        # HLTB uses a specific search API format
        search_data = {
            "searchType": "games",
            "searchTerms": query.split(),
            "searchPage": 1,
            "size": limit,
            "searchOptions": {
                "games": {
                    "userId": 0,
                    "platform": "",
                    "sortCategory": "popular",
                    "rangeCategory": "main",
                    "rangeTime": {"min": 0, "max": 0},
                    "gameplay": {"perspective": "", "flow": "", "genre": ""},
                    "modifier": "",
                },
                "users": {"sortCategory": "postcount"},
                "filter": "",
                "sort": 0,
                "randomizer": 0,
            },
        }

        result = await self._request("search", search_data)

        if "data" not in result:
            return []

        search_results = []
        for game in result["data"]:
            game_id = game.get("game_id")
            if not game_id:
                continue

            cover_url = ""
            if game.get("game_image"):
                cover_url = f"{HLTB_IMAGE_URL}{game['game_image']}"

            release_year = None
            if game.get("release_world"):
                with contextlib.suppress(ValueError):
                    release_year = int(game["release_world"])

            search_results.append(
                SearchResult(
                    name=game.get("game_name", ""),
                    provider=self.name,
                    provider_id=game_id,
                    cover_url=cover_url,
                    platforms=game.get("profile_platform", "").split(", "),
                    release_year=release_year,
                )
            )

        return search_results

    async def get_by_id(self, game_id: int) -> GameResult | None:
        """Get game details by HLTB ID.

        Args:
            game_id: HowLongToBeat game ID

        Returns:
            GameResult with full details, or None if not found
        """
        if not self.is_enabled:
            return None

        # HLTB doesn't have a direct ID lookup, so we search by ID
        search_data = {
            "searchType": "games",
            "searchTerms": [],
            "searchPage": 1,
            "size": 1,
            "searchOptions": {
                "games": {
                    "userId": 0,
                    "platform": "",
                    "sortCategory": "popular",
                    "rangeCategory": "main",
                    "rangeTime": {"min": 0, "max": 0},
                    "gameplay": {"perspective": "", "flow": "", "genre": ""},
                    "modifier": "",
                },
                "users": {"sortCategory": "postcount"},
                "filter": "",
                "sort": 0,
                "randomizer": 0,
            },
            "gameId": game_id,
        }

        result = await self._request("search", search_data)

        if "data" not in result or not result["data"]:
            return None

        game = result["data"][0]
        return self._build_game_result(game)

    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,  # noqa: ARG002
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Args:
            filename: ROM filename
            platform_id: Platform filter (optional)

        Returns:
            GameResult if a match is found, None otherwise
        """
        if not self.is_enabled:
            return None

        # Check for HLTB ID tag in filename
        tagged_id = self.extract_id_from_filename(filename, HLTB_TAG_REGEX)
        if tagged_id:
            result = await self.get_by_id(tagged_id)
            if result:
                return result

        # Clean the filename
        search_term = self._clean_filename(filename)

        # Search for the game
        search_data = {
            "searchType": "games",
            "searchTerms": search_term.split(),
            "searchPage": 1,
            "size": 20,
            "searchOptions": {
                "games": {
                    "userId": 0,
                    "platform": "",
                    "sortCategory": "popular",
                    "rangeCategory": "main",
                    "rangeTime": {"min": 0, "max": 0},
                    "gameplay": {"perspective": "", "flow": "", "genre": ""},
                    "modifier": "",
                },
                "users": {"sortCategory": "postcount"},
                "filter": "",
                "sort": 0,
                "randomizer": 0,
            },
        }

        result = await self._request("search", search_data)

        if "data" not in result or not result["data"]:
            return None

        # Find best match
        games_by_name = {g["game_name"]: g for g in result["data"] if g.get("game_name")}
        best_match, score = self.find_best_match(
            search_term, list(games_by_name.keys())
        )

        if best_match and best_match in games_by_name:
            game = games_by_name[best_match]
            game_result = self._build_game_result(game)
            game_result.match_score = score
            return game_result

        return None

    def _clean_filename(self, filename: str) -> str:
        """Remove tags and extension from filename."""
        name = re.sub(r"\.[^.]+$", "", filename)
        name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name)
        return name.strip()

    def _build_game_result(self, game: dict[str, Any]) -> GameResult:
        """Build a GameResult from HLTB game data."""
        game_id = game.get("game_id", 0)

        cover_url = ""
        if game.get("game_image"):
            cover_url = f"{HLTB_IMAGE_URL}{game['game_image']}"

        # Extract metadata
        metadata = self._extract_metadata(game)

        return GameResult(
            name=game.get("game_name", ""),
            summary="",  # HLTB doesn't provide descriptions
            provider=self.name,
            provider_id=game_id,
            provider_ids={"hltb": game_id},
            artwork=Artwork(cover_url=cover_url),
            metadata=metadata,
            raw_response=game,
        )

    def _extract_metadata(self, game: dict[str, Any]) -> GameMetadata:
        """Extract GameMetadata from HLTB game data."""
        # Release year
        release_year = None
        if game.get("release_world"):
            with contextlib.suppress(ValueError):
                release_year = int(game["release_world"])

        # Game modes from completion times
        game_modes = []
        if game.get("comp_main"):
            game_modes.append("Single Player")
        if game.get("comp_plus"):
            game_modes.append("Completionist")

        # Developer/Publisher
        developer = game.get("profile_dev", "")
        publisher = ""

        # Platforms
        platforms_str = game.get("profile_platform", "")
        platforms_list = [p.strip() for p in platforms_str.split(",") if p.strip()]

        # Review score (HLTB uses a 0-100 scale)
        total_rating = None
        review_score = game.get("review_score")
        if review_score is not None:
            with contextlib.suppress(ValueError, TypeError):
                total_rating = float(review_score)

        return GameMetadata(
            release_year=release_year,
            game_modes=game_modes,
            developer=developer,
            publisher=publisher,
            total_rating=total_rating,
            raw_data={
                "main_story": game.get("comp_main"),
                "main_plus_extras": game.get("comp_plus"),
                "completionist": game.get("comp_100"),
                "all_styles": game.get("comp_all"),
                "platforms": platforms_list,
                "profile_popular": game.get("profile_popular"),
                "count_comp": game.get("count_comp"),
                "count_playing": game.get("count_playing"),
                "count_backlog": game.get("count_backlog"),
                "count_replay": game.get("count_replay"),
                "count_retired": game.get("count_retired"),
                "review_score": game.get("review_score"),
            },
        )

    async def get_completion_times(self, game_id: int) -> dict[str, float | None]:
        """Get completion times for a game.

        Args:
            game_id: HLTB game ID

        Returns:
            Dictionary with completion times in hours
        """
        if not self.is_enabled:
            return {}

        result = await self.get_by_id(game_id)
        if not result:
            return {}

        raw_data = result.metadata.raw_data
        return {
            "main_story": raw_data.get("main_story"),
            "main_plus_extras": raw_data.get("main_plus_extras"),
            "completionist": raw_data.get("completionist"),
            "all_styles": raw_data.get("all_styles"),
        }

    async def price_check(
        self,
        hltb_id: int,
        steam_id: int | None = None,
        itch_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Check game prices across GOG, Steam, and Itch.io.

        Args:
            hltb_id: HowLongToBeat game ID
            steam_id: Steam app ID (optional)
            itch_id: Itch.io game ID (optional)

        Returns:
            Dictionary with price information from various stores:
            {
                "gog": {"price": "9.99", "url": "...", "name": "Game Name"},
                "steam": {"price": "14.99", "url": "...", "name": "Game Name"},
                "itch": {"price": "4.99", "url": "...", "name": "Game Name"}
            }
            Or None if price check fails
        """
        if not self.is_enabled:
            return None

        client = await self._get_client()

        # Build price check request
        price_check_data: dict[str, Any] = {"hltb_id": hltb_id}
        if steam_id:
            price_check_data["steam_id"] = steam_id
        if itch_id:
            price_check_data["itch_id"] = itch_id

        # Fetch security token for auth
        security_token = await self._fetch_security_token()
        headers = {}
        if security_token:
            headers["X-Auth-Token"] = security_token

        url = f"https://howlongtobeat.com/api/price-checks/{hltb_id}"
        logger.debug("HLTB price check: POST %s", url)

        try:
            response = await client.post(url, json=price_check_data, headers=headers)
            response.raise_for_status()
            result = response.json()

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("HLTB price check response:\n%s", json.dumps(result, indent=2, ensure_ascii=False))

            # Parse price check response
            prices: dict[str, Any] = {}

            # GOG prices
            if result.get("gog"):
                gog_data = result["gog"]
                prices["gog"] = {
                    "price": gog_data.get("price"),
                    "url": gog_data.get("url"),
                    "name": gog_data.get("name"),
                }

            # Steam prices
            if result.get("steam"):
                steam_data = result["steam"]
                prices["steam"] = {
                    "price": steam_data.get("price"),
                    "url": steam_data.get("url"),
                    "name": steam_data.get("name"),
                }

            # Itch.io prices
            if result.get("itch"):
                itch_data = result["itch"]
                prices["itch"] = {
                    "price": itch_data.get("price"),
                    "url": itch_data.get("url"),
                    "name": itch_data.get("name"),
                }

            return prices if prices else None
        except httpx.RequestError as e:
            logger.debug("HLTB price check error: %s", e)
            return None

    def get_platform(self, slug: str) -> Platform | None:
        """Get platform information for a slug.

        Args:
            slug: Universal platform slug

        Returns:
            Platform with HLTB platform name, or None if not supported
        """
        try:
            ups = UPS(slug)
        except ValueError:
            return None

        if ups not in HLTB_PLATFORM_MAP:
            return None

        platform_name = HLTB_PLATFORM_MAP[ups]
        return Platform(
            slug=slug,
            name=platform_name,
            provider_ids={"hltb": platform_name},
        )

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()


# HLTB Platform mapping from universal slugs to HLTB platform names
# HLTB uses platform name strings rather than numeric IDs
# Based on romm's HLTB_PLATFORM_LIST for full compatibility
HLTB_PLATFORM_MAP: dict[UPS, str] = {
    # 3DO / Panasonic
    UPS._3DO: "3DO",
    # Acorn
    UPS.ACORN_ARCHIMEDES: "Acorn Archimedes",
    UPS.ACORN_ELECTRON: "Acorn Electron",
    # Amstrad
    UPS.ACPC: "Amstrad CPC",
    UPS.AMSTRAD_PCW: "Amstrad PCW",
    # Android / iOS / Mobile
    UPS.ANDROID: "Android",
    UPS.IOS: "iOS",
    UPS.MOBILE: "Mobile",
    # Apple
    UPS.APPLEII: "Apple II",
    UPS.APPLE_IIGS: "Apple IIGS",
    UPS.MAC: "Mac",
    # Arcade
    UPS.ARCADE: "Arcade",
    UPS.CPS1: "Arcade",
    UPS.CPS2: "Arcade",
    UPS.CPS3: "Arcade",
    UPS.NEOGEOAES: "Neo Geo",
    UPS.NEOGEOMVS: "Neo Geo",
    # Atari
    UPS.ATARI2600: "Atari 2600",
    UPS.ATARI5200: "Atari 5200",
    UPS.ATARI7800: "Atari 7800",
    UPS.ATARI8BIT: "Atari 8-bit Family",
    UPS.ATARI800: "Atari 8-bit Family",
    UPS.ATARI_ST: "Atari ST",
    UPS.JAGUAR: "Atari Jaguar",
    UPS.ATARI_JAGUAR_CD: "Atari Jaguar CD",
    UPS.LYNX: "Atari Lynx",
    UPS.ATARI_VCS: "Atari VCS",
    # Bandai
    UPS.WONDERSWAN: "WonderSwan",
    UPS.WONDERSWAN_COLOR: "WonderSwan Color",
    # BBC
    UPS.BBCMICRO: "BBC Micro",
    # ColecoVision
    UPS.COLECOVISION: "ColecoVision",
    UPS.COLECOADAM: "ColecoVision",
    # Commodore
    UPS.AMIGA: "Amiga",
    UPS.AMIGA_CD32: "Amiga CD32",
    UPS.C64: "Commodore 64",
    UPS.C128: "Commodore 64",
    UPS.VIC_20: "Commodore VIC-20",
    UPS.COMMODORE_CDTV: "Commodore CDTV",
    # DOS / PC
    UPS.DOS: "PC",
    UPS.WIN: "PC",
    UPS.WIN3X: "PC",
    UPS.LINUX: "Linux",
    # Fairchild
    UPS.FAIRCHILD_CHANNEL_F: "Channel F",
    # FM Towns
    UPS.FM_TOWNS: "FM Towns",
    UPS.FM_7: "FM-7",
    # Intellivision
    UPS.INTELLIVISION: "Intellivision",
    UPS.INTELLIVISION_AMICO: "Intellivision Amico",
    # Microsoft Xbox
    UPS.XBOX: "Xbox",
    UPS.XBOX360: "Xbox 360",
    UPS.XBOXONE: "Xbox One",
    UPS.SERIES_X_S: "Xbox Series X/S",
    # NEC
    UPS.PC_8800_SERIES: "PC-88",
    UPS.PC_9800_SERIES: "PC-98",
    UPS.PC_FX: "PC-FX",
    UPS.TG16: "TurboGrafx-16",
    UPS.TURBOGRAFX_CD: "TurboGrafx-CD",
    UPS.SUPERGRAFX: "SuperGrafx",
    UPS.NEC_PC_6000_SERIES: "NEC PC-6000 Series",
    # Neo Geo
    UPS.NEO_GEO_CD: "Neo Geo CD",
    UPS.NEO_GEO_POCKET: "Neo Geo Pocket",
    UPS.NEO_GEO_POCKET_COLOR: "Neo Geo Pocket Color",
    # Nintendo Consoles
    UPS.NES: "NES",
    UPS.FAMICOM: "NES",
    UPS.FDS: "Famicom Disk System",
    UPS.SNES: "SNES",
    UPS.SFAM: "SNES",
    UPS.SATELLAVIEW: "Satellaview",
    UPS.N64: "Nintendo 64",
    UPS.N64DD: "Nintendo 64DD",
    UPS.NGC: "GameCube",
    UPS.WII: "Wii",
    UPS.WIIU: "Wii U",
    UPS.SWITCH: "Nintendo Switch",
    UPS.SWITCH_2: "Nintendo Switch 2",
    # Nintendo Handhelds
    UPS.GB: "Game Boy",
    UPS.GBC: "Game Boy Color",
    UPS.GBA: "Game Boy Advance",
    UPS.NDS: "Nintendo DS",
    UPS.NINTENDO_DSI: "Nintendo DSi",
    UPS.N3DS: "Nintendo 3DS",
    UPS.NEW_NINTENDON3DS: "New Nintendo 3DS",
    UPS.VIRTUALBOY: "Virtual Boy",
    # Odyssey
    UPS.ODYSSEY: "Odyssey",
    UPS.ODYSSEY_2: "Odyssey 2",
    # Philips
    UPS.PHILIPS_CD_I: "Philips CD-i",
    # Sega
    UPS.SMS: "Master System",
    UPS.SG1000: "SG-1000",
    UPS.SC3000: "Sega SC-3000",
    UPS.GENESIS: "Genesis",
    UPS.SEGACD: "Sega CD",
    UPS.SEGA32: "Sega 32X",
    UPS.SATURN: "Saturn",
    UPS.DC: "Dreamcast",
    UPS.GAMEGEAR: "Game Gear",
    UPS.SEGA_PICO: "Sega Pico",
    # Sharp
    UPS.SHARP_X68000: "Sharp X68000",
    UPS.X1: "Sharp X1",
    UPS.SHARP_MZ_80K7008001500: "Sharp MZ Series",
    # Sinclair
    UPS.ZXS: "ZX Spectrum",
    UPS.ZX80: "ZX80",
    UPS.ZX81: "ZX81",
    UPS.ZX_SPECTRUM_NEXT: "ZX Spectrum Next",
    UPS.SINCLAIR_QL: "Sinclair QL",
    # Sony PlayStation
    UPS.PSX: "PlayStation",
    UPS.PS2: "PlayStation 2",
    UPS.PS3: "PlayStation 3",
    UPS.PS4: "PlayStation 4",
    UPS.PS5: "PlayStation 5",
    UPS.PSP: "PlayStation Portable",
    UPS.PSVITA: "PlayStation Vita",
    UPS.PSVR: "PlayStation VR",
    UPS.PSVR2: "PlayStation VR2",
    UPS.POCKETSTATION: "PocketStation",
    # Vectrex
    UPS.VECTREX: "Vectrex",
    # MSX
    UPS.MSX: "MSX",
    UPS.MSX2: "MSX2",
    UPS.MSX2PLUS: "MSX2+",
    UPS.MSX_TURBO: "MSX turboR",
    # Modern / Cloud
    UPS.STADIA: "Google Stadia",
    UPS.LUNA: "Luna",
    UPS.AMAZON_FIRE_TV: "Amazon Fire TV",
    UPS.OUYA: "Ouya",
    UPS.PLAYDATE: "Playdate",
    UPS.GAMESTICK: "GameStick",
    UPS.ONLIVE_GAME_SYSTEM: "OnLive Game System",
    # VR Platforms
    UPS.OCULUS_QUEST: "Meta Quest",
    UPS.META_QUEST_2: "Meta Quest",
    UPS.META_QUEST_3: "Meta Quest",
    UPS.OCULUS_RIFT: "Oculus Rift",
    UPS.OCULUS_GO: "Oculus Go",
    UPS.GEAR_VR: "Gear VR",
    UPS.DAYDREAM: "Daydream",
    UPS.WINDOWS_MIXED_REALITY: "Windows Mixed Reality",
    UPS.STEAM_VR: "Steam VR",
    # N-Gage
    UPS.NGAGE: "N-Gage",
    UPS.NGAGE2: "N-Gage 2.0",
    # Handheld Gaming
    UPS.GP32: "GP32",
    UPS.GP2X: "GP2X",
    UPS.GP2X_WIZ: "GP2X Wiz",
    UPS.PANDORA: "Pandora",
    UPS.ZODIAC: "Zodiac",
    # Classic Handhelds
    UPS.DEDICATED_HANDHELD: "Handheld",
    UPS.G_AND_W: "Game & Watch",
    UPS.GAMATE: "Gamate",
    UPS.GAME_DOT_COM: "Game.com",
    UPS.GIZMONDO: "Gizmondo",
    UPS.POKEMON_MINI: "Pokémon Mini",
    UPS.SUPERVISION: "Supervision",
    UPS.MEGA_DUCK_SLASH_COUGAR_BOY: "Mega Duck",
    UPS.MICROVISION: "Microvision",
    # Modern Handhelds / Retro
    UPS.EVERCADE: "Evercade",
    UPS.POLYMEGA: "Polymega",
    UPS.ARDUBOY: "Arduboy",
    # Other Consoles
    UPS.ARCADIA_2001: "Arcadia 2001",
    UPS.ASTROCADE: "Bally Astrocade",
    UPS.CASIO_LOOPY: "Casio Loopy",
    UPS.CASIO_PV_1000: "Casio PV-1000",
    UPS.EPOCH_CASSETTE_VISION: "Cassette Vision",
    UPS.EPOCH_SUPER_CASSETTE_VISION: "Super Cassette Vision",
    UPS.INTERTON_VC_4000: "VC 4000",
    UPS.VC_4000: "VC 4000",
    UPS.ADVENTURE_VISION: "Adventure Vision",
    UPS.CREATIVISION: "CreatiVision",
    UPS.RCA_STUDIO_II: "RCA Studio II",
    UPS.NUON: "Nuon",
    UPS.HYPERSCAN: "HyperScan",
    UPS.LASERACTIVE: "LaserActive",
    UPS.PLAYDIA: "Playdia",
    UPS.SUPER_ACAN: "Super A'Can",
    # Classic Computers
    UPS.TRS_80: "TRS-80",
    UPS.TRS_80_COLOR_COMPUTER: "TRS-80 Color Computer",
    UPS.TI_994A: "TI-99/4A",
    UPS.DRAGON_32_SLASH_64: "Dragon 32/64",
    UPS.SAM_COUPE: "SAM Coupé",
    UPS.ORIC: "Oric",
    UPS.TATUNG_EINSTEIN: "Tatung Einstein",
    UPS.ENTERPRISE: "Enterprise",
    UPS.COLOUR_GENIE: "Colour Genie",
    UPS.AQUARIUS: "Aquarius",
    UPS.SORD_M5: "Sord M5",
    UPS.MEMOTECH_MTX: "Memotech MTX",
    UPS.EXIDY_SORCERER: "Exidy Sorcerer",
    UPS.TOMY_TUTOR: "Tomy Tutor",
    UPS.SPECTRAVIDEO: "Spectravideo",
    UPS.EXELVISION: "Exelvision",
    UPS.THOMSON_MO5: "Thomson MO5",
    UPS.THOMSON_TO: "Thomson TO",
    # Web / Browser
    UPS.BROWSER: "Browser",
    UPS.WEBOS: "webOS",
    # Mobile Platforms
    UPS.WINPHONE: "Windows Phone",
    UPS.WINDOWS_MOBILE: "Windows Mobile",
    UPS.SYMBIAN: "Symbian",
    UPS.BLACKBERRY: "BlackBerry",
    UPS.PALM_OS: "Palm OS",
    UPS.J2ME: "Java ME",
    UPS.BREW: "BREW",
    # Learning / Educational
    UPS.LEAPSTER: "Leapster",
    UPS.LEAPTV: "LeapTV",
    UPS.DIDJ: "Didj",
    UPS.VSMILE: "V.Smile",
    UPS.CLICKSTART: "ClickStart",
    # Other
    UPS.ZEEBO: "Zeebo",
    UPS.UZEBOX: "Uzebox",
    UPS.WASM_4: "WASM-4",
    UPS.TIC_80: "TIC-80",
}
