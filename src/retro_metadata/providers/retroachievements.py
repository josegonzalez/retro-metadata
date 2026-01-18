"""RetroAchievements metadata provider implementation."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Final

import httpx

logger = logging.getLogger(__name__)

from retro_metadata.core.exceptions import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderRateLimitError,
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

# Regex to detect RetroAchievements ID tags in filenames like (ra-12345)
RA_TAG_REGEX: Final = re.compile(r"\(ra-(\d+)\)", re.IGNORECASE)

# Base URL for media assets
RA_MEDIA_URL: Final = "https://media.retroachievements.org"

# Base URL for achievement badges
RA_BADGE_URL: Final = "https://media.retroachievements.org/Badge"


@dataclass
class RAGameAchievement:
    """RetroAchievements achievement data.

    Attributes:
        id: Achievement ID
        title: Achievement title/name
        description: Achievement description
        points: Points awarded for unlocking
        badge_id: Badge ID for constructing image URL
        badge_url: Full URL to badge image
        badge_url_locked: Full URL to locked badge image
        type: Achievement type (e.g., "progression", "win_condition", "missable")
        num_awarded: Number of times awarded
        num_awarded_hardcore: Number of times awarded in hardcore mode
        display_order: Display order in the list
    """

    id: int
    title: str
    description: str = ""
    points: int = 0
    badge_id: str = ""
    badge_url: str = ""
    badge_url_locked: str = ""
    type: str = ""
    num_awarded: int = 0
    num_awarded_hardcore: int = 0
    display_order: int = 0

    @classmethod
    def from_api_data(cls, data: dict[str, Any]) -> "RAGameAchievement":
        """Create RAGameAchievement from API response data."""
        badge_id = str(data.get("BadgeName", ""))
        badge_url = f"{RA_BADGE_URL}/{badge_id}.png" if badge_id else ""
        badge_url_locked = f"{RA_BADGE_URL}/{badge_id}_lock.png" if badge_id else ""

        return cls(
            id=data.get("ID", 0),
            title=data.get("Title", ""),
            description=data.get("Description", ""),
            points=data.get("Points", 0),
            badge_id=badge_id,
            badge_url=badge_url,
            badge_url_locked=badge_url_locked,
            type=data.get("type", ""),
            num_awarded=data.get("NumAwarded", 0),
            num_awarded_hardcore=data.get("NumAwardedHardcore", 0),
            display_order=data.get("DisplayOrder", 0),
        )


class RetroAchievementsProvider(MetadataProvider):
    """RetroAchievements metadata provider.

    Requires an api_key credential and username from RetroAchievements.

    Example:
        config = ProviderConfig(
            enabled=True,
            credentials={"api_key": "your_api_key", "username": "your_username"}
        )
        provider = RetroAchievementsProvider(config)
        results = await provider.search("Super Mario World", platform_id=3)
    """

    name = "retroachievements"

    def __init__(
        self,
        config: "ProviderConfig",
        cache: "CacheBackend | None" = None,
        user_agent: str = "retro-metadata/1.0",
    ) -> None:
        super().__init__(config, cache)
        self._base_url = "https://retroachievements.org/API"
        self._user_agent = user_agent
        self._client: httpx.AsyncClient | None = None
        self._min_similarity_score = 0.6

    @property
    def api_key(self) -> str:
        return self.config.get_credential("api_key")

    @property
    def username(self) -> str:
        return self.config.get_credential("username", "")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={"User-Agent": self._user_agent},
                timeout=self.config.timeout,
            )
        return self._client

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make an API request to RetroAchievements."""
        client = await self._get_client()

        if params is None:
            params = {}
        params["z"] = self.username or "retro-metadata"
        params["y"] = self.api_key

        # Log request (mask API key)
        log_params = {k: v for k, v in params.items() if k not in ("y",)}
        logger.debug("RetroAchievements API: GET %s%s", self._base_url, endpoint)
        logger.debug("RetroAchievements API params: %s", log_params)

        try:
            response = await client.get(endpoint, params=params)

            if response.status_code == 401:
                logger.debug("RetroAchievements API: 401 Unauthorized")
                raise ProviderAuthenticationError(self.name, "Invalid API key")
            elif response.status_code == 429:
                logger.debug("RetroAchievements API: 429 Rate limited")
                raise ProviderRateLimitError(self.name)

            response.raise_for_status()
            data = response.json()

            # Log full response body only when debug logging is enabled
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("RetroAchievements API response:\n%s", json.dumps(data, indent=2, ensure_ascii=False))

            return data
        except httpx.RequestError as e:
            logger.debug("RetroAchievements API error: %s", e)
            raise ProviderConnectionError(self.name, str(e)) from e

    async def search(
        self,
        query: str,
        platform_id: int | None = None,
        limit: int = 25,
    ) -> list[SearchResult]:
        """Search for games by name.

        Note: RetroAchievements doesn't have a search endpoint, so this
        fetches the game list for the platform and filters locally.

        Args:
            query: Search query string
            platform_id: RetroAchievements console ID to filter by
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.is_enabled:
            return []

        if not platform_id:
            return []

        # Get game list for platform
        params = {
            "i": str(platform_id),
            "f": "1",  # Only games with achievements
            "h": "0",  # Don't include hashes
        }

        results = await self._request("/API_GetGameList.php", params)

        if not isinstance(results, list):
            return []

        # Filter by query
        query_lower = query.lower()
        filtered = [
            g for g in results if query_lower in g.get("Title", "").lower()
        ][:limit]

        search_results = []
        for game in filtered:
            icon = game.get("ImageIcon", "")
            cover_url = f"{RA_MEDIA_URL}{icon}" if icon else ""

            search_results.append(
                SearchResult(
                    name=game.get("Title", ""),
                    provider=self.name,
                    provider_id=game["ID"],
                    cover_url=cover_url,
                    platforms=[game.get("ConsoleName", "")],
                )
            )

        return search_results

    async def get_by_id(self, game_id: int) -> GameResult | None:
        """Get game details by RetroAchievements ID.

        Args:
            game_id: RetroAchievements game ID

        Returns:
            GameResult with full details, or None if not found
        """
        if not self.is_enabled:
            return None

        result = await self._request("/API_GetGameExtended.php", {"i": str(game_id)})

        if not isinstance(result, dict) or "ID" not in result:
            return None

        return self._build_game_result(result)

    async def get_achievements(self, game_id: int) -> list[RAGameAchievement]:
        """Get all achievements for a game.

        Args:
            game_id: RetroAchievements game ID

        Returns:
            List of RAGameAchievement objects
        """
        if not self.is_enabled:
            return []

        result = await self._request("/API_GetGameExtended.php", {"i": str(game_id)})

        if not isinstance(result, dict):
            return []

        achievements_data = result.get("Achievements", {})
        if not achievements_data:
            return []

        achievements = []
        for ach_data in achievements_data.values():
            if isinstance(ach_data, dict):
                achievements.append(RAGameAchievement.from_api_data(ach_data))

        # Sort by display order
        achievements.sort(key=lambda a: a.display_order)
        return achievements

    async def lookup_by_hash(
        self,
        platform_id: int,
        md5: str | None = None,
    ) -> GameResult | None:
        """Look up a game by ROM hash.

        RetroAchievements uses MD5 hashes for ROM identification.

        Args:
            platform_id: RetroAchievements console ID
            md5: MD5 hash of the ROM

        Returns:
            GameResult if found, None otherwise
        """
        if not self.is_enabled:
            return None

        if not md5:
            return None

        # Get game list with hashes
        params = {
            "i": str(platform_id),
            "f": "1",  # Only games with achievements
            "h": "1",  # Include hashes
        }

        results = await self._request("/API_GetGameList.php", params)

        if not isinstance(results, list):
            return None

        # Find matching hash
        md5_lower = md5.lower()
        for game in results:
            hashes = game.get("Hashes", [])
            if any(md5_lower == h.lower() for h in hashes):
                # Get full game details
                return await self.get_by_id(game["ID"])

        return None

    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Args:
            filename: ROM filename
            platform_id: RetroAchievements console ID

        Returns:
            GameResult if a match is found, None otherwise
        """
        if not self.is_enabled:
            return None

        # Check for RetroAchievements ID tag in filename
        tagged_id = self.extract_id_from_filename(filename, RA_TAG_REGEX)
        if tagged_id:
            result = await self.get_by_id(tagged_id)
            if result:
                return result

        if not platform_id:
            return None

        # Clean the filename and search
        search_term = self._clean_filename(filename)

        # Get game list for platform
        params = {
            "i": str(platform_id),
            "f": "1",
            "h": "0",
        }

        results = await self._request("/API_GetGameList.php", params)

        if not isinstance(results, list) or not results:
            return None

        # Build name mapping
        games_by_name = {g["Title"]: g for g in results if g.get("Title")}

        # Find best match
        best_match, score = self.find_best_match(
            search_term, list(games_by_name.keys())
        )

        if best_match and best_match in games_by_name:
            game = games_by_name[best_match]
            result = await self.get_by_id(game["ID"])
            if result:
                result.match_score = score
                return result

        return None

    def _clean_filename(self, filename: str) -> str:
        """Remove tags and extension from filename."""
        name = re.sub(r"\.[^.]+$", "", filename)
        name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name)
        return name.strip()

    def _build_game_result(self, game: dict[str, Any]) -> GameResult:
        """Build a GameResult from RetroAchievements game data."""
        # Build artwork URLs
        icon = game.get("ImageIcon", "")
        title_img = game.get("ImageTitle", "")
        ingame_img = game.get("ImageIngame", "")
        boxart_img = game.get("ImageBoxArt", "")

        cover_url = f"{RA_MEDIA_URL}{boxart_img}" if boxart_img else ""
        if not cover_url and title_img:
            cover_url = f"{RA_MEDIA_URL}{title_img}"

        screenshot_urls = []
        if ingame_img:
            screenshot_urls.append(f"{RA_MEDIA_URL}{ingame_img}")
        if title_img and title_img != boxart_img:
            screenshot_urls.append(f"{RA_MEDIA_URL}{title_img}")

        icon_url = f"{RA_MEDIA_URL}{icon}" if icon else ""

        # Extract metadata
        metadata = self._extract_metadata(game)

        return GameResult(
            name=game.get("Title", ""),
            summary="",  # RA doesn't provide game descriptions
            provider=self.name,
            provider_id=game["ID"],
            provider_ids={"retroachievements": game["ID"]},
            artwork=Artwork(
                cover_url=cover_url,
                screenshot_urls=screenshot_urls,
                icon_url=icon_url,
            ),
            metadata=metadata,
            raw_response=game,
        )

    def _extract_metadata(self, game: dict[str, Any]) -> GameMetadata:
        """Extract GameMetadata from RetroAchievements game data."""
        # Extract genres
        genres = []
        genre = game.get("Genre", "")
        if genre:
            genres = [genre]

        # Extract companies
        companies = []
        if game.get("Publisher"):
            companies.append(game["Publisher"])
        if game.get("Developer"):
            companies.append(game["Developer"])

        # Extract release date
        first_release_date = None
        released = game.get("Released", "")
        if released:
            try:
                date_str = released.split()[0]  # Handle "YYYY-MM-DD extra info"
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                first_release_date = int(parsed_date.timestamp())
            except (ValueError, IndexError):
                pass

        # Extract release year
        release_year = None
        if first_release_date:
            release_year = datetime.fromtimestamp(first_release_date).year

        # Get platform info
        platforms = []
        if game.get("ConsoleName"):
            platforms.append(
                Platform(
                    slug="",
                    name=game["ConsoleName"],
                    provider_ids={"retroachievements": game.get("ConsoleID", 0)},
                )
            )

        # Extract achievement statistics
        achievements_data = game.get("Achievements", {})
        achievement_count = len(achievements_data) if achievements_data else game.get("NumAchievements", 0)
        total_points = sum(
            a.get("Points", 0) for a in achievements_data.values()
        ) if isinstance(achievements_data, dict) else game.get("points_total", 0)

        return GameMetadata(
            first_release_date=first_release_date,
            genres=genres,
            companies=list(dict.fromkeys(companies)),
            platforms=platforms,
            developer=game.get("Developer", ""),
            publisher=game.get("Publisher", ""),
            release_year=release_year,
            raw_data={
                **game,
                "achievement_count": achievement_count,
                "total_points": total_points,
                "players_total": game.get("players_total", 0),
                "players_hardcore": game.get("players_hardcore", 0),
            },
        )

    def get_platform(self, slug: str) -> Platform | None:
        """Get platform information for a slug.

        Args:
            slug: Universal platform slug

        Returns:
            Platform with RetroAchievements ID, or None if not supported
        """
        try:
            ups = UPS(slug)
        except ValueError:
            return None

        if ups not in RA_PLATFORM_MAP:
            return None

        platform_info = RA_PLATFORM_MAP[ups]
        return Platform(
            slug=slug,
            name=platform_info["name"],
            provider_ids={"retroachievements": platform_info["id"]},
        )

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()


# Platform mapping from universal slugs to RetroAchievements console IDs
RA_PLATFORM_MAP: dict[UPS, dict[str, Any]] = {
    UPS._3DO: {"id": 43, "name": "3DO"},
    UPS.ACPC: {"id": 37, "name": "Amstrad CPC"},
    UPS.APPLEII: {"id": 38, "name": "Apple II"},
    UPS.ARCADE: {"id": 27, "name": "Arcade"},
    UPS.ARCADIA_2001: {"id": 73, "name": "Arcadia 2001"},
    UPS.ARDUBOY: {"id": 71, "name": "Arduboy"},
    UPS.ATARI2600: {"id": 25, "name": "Atari 2600"},
    UPS.ATARI5200: {"id": 50, "name": "Atari 5200"},
    UPS.ATARI7800: {"id": 51, "name": "Atari 7800"},
    UPS.ATARI_JAGUAR_CD: {"id": 77, "name": "Atari Jaguar CD"},
    UPS.ATARI_ST: {"id": 36, "name": "Atari ST"},
    UPS.COLECOVISION: {"id": 44, "name": "ColecoVision"},
    UPS.DC: {"id": 40, "name": "Dreamcast"},
    UPS.ELEKTOR: {"id": 75, "name": "Elektor TV Games Computer"},
    UPS.FAIRCHILD_CHANNEL_F: {"id": 57, "name": "Fairchild Channel F"},
    UPS.GB: {"id": 4, "name": "Game Boy"},
    UPS.GBA: {"id": 5, "name": "Game Boy Advance"},
    UPS.GBC: {"id": 6, "name": "Game Boy Color"},
    UPS.GAMEGEAR: {"id": 15, "name": "Game Gear"},
    UPS.GENESIS: {"id": 1, "name": "Mega Drive"},
    UPS.INTELLIVISION: {"id": 45, "name": "Intellivision"},
    UPS.INTERTON_VC_4000: {"id": 75, "name": "Interton VC 4000"},
    UPS.JAGUAR: {"id": 17, "name": "Jaguar"},
    UPS.LYNX: {"id": 13, "name": "Lynx"},
    UPS.MEGA_DUCK_SLASH_COUGAR_BOY: {"id": 69, "name": "Mega Duck"},
    UPS.MSX: {"id": 29, "name": "MSX"},
    UPS.N64: {"id": 2, "name": "Nintendo 64"},
    UPS.NDS: {"id": 18, "name": "Nintendo DS"},
    UPS.NES: {"id": 7, "name": "NES"},
    UPS.NGC: {"id": 16, "name": "GameCube"},
    UPS.NEO_GEO_CD: {"id": 56, "name": "Neo Geo CD"},
    UPS.NEO_GEO_POCKET: {"id": 14, "name": "Neo Geo Pocket"},
    UPS.NINTENDO_DSI: {"id": 78, "name": "Nintendo DSi"},
    UPS.ODYSSEY_2: {"id": 23, "name": "Odyssey 2"},
    UPS.PC_8800_SERIES: {"id": 47, "name": "PC-8000/8800"},
    UPS.PC_9800_SERIES: {"id": 48, "name": "PC-9800"},
    UPS.PC_FX: {"id": 49, "name": "PC-FX"},
    UPS.POKEMON_MINI: {"id": 24, "name": "Pokemon Mini"},
    UPS.PSX: {"id": 12, "name": "PlayStation"},
    UPS.PS2: {"id": 21, "name": "PlayStation 2"},
    UPS.PSP: {"id": 41, "name": "PSP"},
    UPS.SATURN: {"id": 39, "name": "Saturn"},
    UPS.SEGA32: {"id": 10, "name": "32X"},
    UPS.SEGACD: {"id": 9, "name": "Mega CD"},
    UPS.SG1000: {"id": 33, "name": "SG-1000"},
    UPS.SMS: {"id": 11, "name": "Master System"},
    UPS.SNES: {"id": 3, "name": "SNES"},
    UPS.SUPERGRAFX: {"id": 76, "name": "SuperGrafx"},
    UPS.TG16: {"id": 8, "name": "TurboGrafx-16"},
    UPS.UZEBOX: {"id": 80, "name": "Uzebox"},
    UPS.VECTREX: {"id": 46, "name": "Vectrex"},
    UPS.VIRTUALBOY: {"id": 28, "name": "Virtual Boy"},
    UPS.SUPERVISION: {"id": 63, "name": "Watara Supervision"},
    UPS.WASM_4: {"id": 72, "name": "WASM-4"},
    UPS.WII: {"id": 19, "name": "Wii"},
    UPS.WONDERSWAN: {"id": 53, "name": "WonderSwan"},
    UPS.SHARP_X68000: {"id": 52, "name": "Sharp X68000"},
    UPS.ZXS: {"id": 34, "name": "ZX Spectrum"},
}

# Reverse lookup from RA console ID to UPS slug
RA_ID_TO_SLUG: dict[int, UPS] = {v["id"]: k for k, v in RA_PLATFORM_MAP.items()}
