"""TheGamesDB metadata provider implementation."""

from __future__ import annotations

import json
import logging
import re
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

# Regex to detect TheGamesDB ID tags in filenames like (tgdb-12345)
TGDB_TAG_REGEX: Final = re.compile(r"\(tgdb-(\d+)\)", re.IGNORECASE)


class TheGamesDBProvider(MetadataProvider):
    """TheGamesDB metadata provider.

    Requires an api_key credential from TheGamesDB.

    Example:
        config = ProviderConfig(
            enabled=True,
            credentials={"api_key": "your_api_key"}
        )
        provider = TheGamesDBProvider(config)
        results = await provider.search("Super Mario World", platform_id=6)
    """

    name = "thegamesdb"

    def __init__(
        self,
        config: "ProviderConfig",
        cache: "CacheBackend | None" = None,
        user_agent: str = "retro-metadata/1.0",
    ) -> None:
        super().__init__(config, cache)
        self._base_url = "https://api.thegamesdb.net/v1"
        self._user_agent = user_agent
        self._client: httpx.AsyncClient | None = None
        self._min_similarity_score = 0.6

    @property
    def api_key(self) -> str:
        return self.config.get_credential("api_key")

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
    ) -> dict[str, Any]:
        """Make an API request to TheGamesDB."""
        client = await self._get_client()

        if params is None:
            params = {}
        params["apikey"] = self.api_key

        # Log request (mask API key)
        log_params = {k: v for k, v in params.items() if k not in ("apikey",)}
        logger.debug("TheGamesDB API: GET %s%s", self._base_url, endpoint)
        logger.debug("TheGamesDB API params: %s", log_params)

        try:
            response = await client.get(endpoint, params=params)

            if response.status_code == 401:
                logger.debug("TheGamesDB API: 401 Unauthorized")
                raise ProviderAuthenticationError(self.name, "Invalid API key")
            elif response.status_code == 429:
                logger.debug("TheGamesDB API: 429 Rate limited")
                raise ProviderRateLimitError(self.name)

            response.raise_for_status()
            data = response.json()

            # Log full response body only when debug logging is enabled
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("TheGamesDB API response:\n%s", json.dumps(data, indent=2, ensure_ascii=False))

            return data
        except httpx.RequestError as e:
            logger.debug("TheGamesDB API error: %s", e)
            raise ProviderConnectionError(self.name, str(e)) from e

    async def search(
        self,
        query: str,
        platform_id: int | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search for games by name.

        Args:
            query: Search query string
            platform_id: TheGamesDB platform ID to filter by
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.is_enabled:
            return []

        params: dict[str, Any] = {
            "name": query,
            "fields": "players,publishers,genres,overview,rating",
            "include": "boxart",
        }

        if platform_id:
            params["filter[platform]"] = str(platform_id)

        result = await self._request("/Games/ByGameName", params)

        if "data" not in result or "games" not in result["data"]:
            return []

        games = result["data"]["games"]
        boxart_data = result.get("include", {}).get("boxart", {})
        base_url = boxart_data.get("base_url", {})

        # Sort games to prefer the specified platform
        if platform_id:
            games = sorted(
                games,
                key=lambda g: (0 if g.get("platform") == platform_id else 1),
            )

        search_results = []
        for game in games[:limit]:
            game_id = game.get("id")
            if not game_id:
                continue

            # Get cover image
            cover_url = ""
            game_boxart = boxart_data.get("data", {}).get(str(game_id), [])
            for art in game_boxart:
                if art.get("side") == "front":
                    cover_url = base_url.get("thumb", "") + art.get("filename", "")
                    break

            # Get release year
            release_year = None
            release_date = game.get("release_date")
            if release_date:
                try:
                    release_year = int(release_date[:4])
                except (ValueError, IndexError):
                    pass

            search_results.append(
                SearchResult(
                    name=game.get("game_title", ""),
                    provider=self.name,
                    provider_id=game_id,
                    cover_url=cover_url,
                    platforms=[str(game.get("platform", ""))],
                    release_year=release_year,
                )
            )

        return search_results

    async def get_by_id(self, game_id: int) -> GameResult | None:
        """Get game details by TheGamesDB ID.

        Args:
            game_id: TheGamesDB game ID

        Returns:
            GameResult with full details, or None if not found
        """
        if not self.is_enabled:
            return None

        params = {
            "id": str(game_id),
            "fields": "players,publishers,genres,overview,rating,platform",
            "include": "boxart",
        }

        result = await self._request("/Games/ByGameID", params)

        if "data" not in result or "games" not in result["data"]:
            return None

        games = result["data"]["games"]
        if not games:
            return None

        game = games[0] if isinstance(games, list) else games.get(str(game_id))
        if not game:
            return None

        boxart_data = result.get("include", {}).get("boxart", {})

        return self._build_game_result(game, boxart_data)

    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Args:
            filename: ROM filename
            platform_id: TheGamesDB platform ID

        Returns:
            GameResult if a match is found, None otherwise
        """
        if not self.is_enabled:
            return None

        # Check for TheGamesDB ID tag in filename
        tagged_id = self.extract_id_from_filename(filename, TGDB_TAG_REGEX)
        if tagged_id:
            result = await self.get_by_id(tagged_id)
            if result:
                return result

        if not platform_id:
            return None

        # Clean the filename
        search_term = self._clean_filename(filename)

        # Search for the game
        params: dict[str, Any] = {
            "name": search_term,
            "filter[platform]": str(platform_id),
            "fields": "players,publishers,genres,overview,rating",
            "include": "boxart",
        }

        result = await self._request("/Games/ByGameName", params)

        if "data" not in result or "games" not in result["data"]:
            # Try with split search term
            terms = self.split_search_term(search_term)
            if len(terms) > 1:
                params["name"] = terms[-1]
                result = await self._request("/Games/ByGameName", params)

        if "data" not in result or "games" not in result["data"]:
            return None

        games = result["data"]["games"]
        if not games:
            return None

        boxart_data = result.get("include", {}).get("boxart", {})

        # Sort games to prefer the specified platform
        if platform_id:
            games = sorted(
                games,
                key=lambda g: (0 if g.get("platform") == platform_id else 1),
            )

        # Find best match - build dict with platform preference
        # (games from matching platform will overwrite others with same name)
        games_by_name: dict[str, Any] = {}
        for g in reversed(games):  # Reversed so preferred platform wins
            if g.get("game_title"):
                games_by_name[g["game_title"]] = g

        best_match, score = self.find_best_match(
            search_term, list(games_by_name.keys())
        )

        if best_match and best_match in games_by_name:
            game = games_by_name[best_match]
            game_result = self._build_game_result(game, boxart_data)
            game_result.match_score = score
            return game_result

        return None

    def _clean_filename(self, filename: str) -> str:
        """Remove tags and extension from filename."""
        name = re.sub(r"\.[^.]+$", "", filename)
        name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name)
        return name.strip()

    def _build_game_result(
        self, game: dict[str, Any], boxart_data: dict[str, Any]
    ) -> GameResult:
        """Build a GameResult from TheGamesDB game data."""
        game_id = game.get("id", 0)

        # Get artwork
        base_url = boxart_data.get("base_url", {})
        game_boxart = boxart_data.get("data", {}).get(str(game_id), [])

        cover_url = ""
        screenshot_urls = []

        for art in game_boxart:
            url = base_url.get("original", "") + art.get("filename", "")
            side = art.get("side", "")

            if side == "front" and not cover_url:
                cover_url = url
            elif side == "back":
                screenshot_urls.append(url)

        # Extract metadata
        metadata = self._extract_metadata(game)

        return GameResult(
            name=game.get("game_title", ""),
            summary=game.get("overview", ""),
            provider=self.name,
            provider_id=game_id,
            provider_ids={"thegamesdb": game_id},
            artwork=Artwork(
                cover_url=cover_url,
                screenshot_urls=screenshot_urls,
            ),
            metadata=metadata,
            raw_response=game,
        )

    def _extract_metadata(self, game: dict[str, Any]) -> GameMetadata:
        """Extract GameMetadata from TheGamesDB game data."""
        # Release year
        release_year = None
        release_date = game.get("release_date")
        if release_date:
            try:
                release_year = int(release_date[:4])
            except (ValueError, IndexError):
                pass

        # Genres
        genres = game.get("genres", [])
        if isinstance(genres, dict):
            genres = list(genres.values())

        # Player count
        player_count = str(game.get("players", 1))

        # Rating
        total_rating = None
        rating = game.get("rating")
        if rating:
            try:
                # TGDB uses "Rating: X.XX/10" format
                if isinstance(rating, str) and "/" in rating:
                    num = rating.split("/")[0].replace("Rating: ", "")
                    total_rating = float(num) * 10
                else:
                    total_rating = float(rating) * 10
            except (ValueError, TypeError):
                pass

        # Publishers
        publishers = game.get("publishers", [])
        if isinstance(publishers, dict):
            publishers = list(publishers.values())

        # Developers
        developers = game.get("developers", [])
        if isinstance(developers, dict):
            developers = list(developers.values())

        companies = publishers + developers

        return GameMetadata(
            total_rating=total_rating,
            genres=genres if isinstance(genres, list) else [],
            companies=list(dict.fromkeys(companies)),
            player_count=player_count,
            release_year=release_year,
            publisher=publishers[0] if publishers else "",
            developer=developers[0] if developers else "",
            raw_data=game,
        )

    def get_platform(self, slug: str) -> Platform | None:
        """Get platform information for a slug.

        Args:
            slug: Universal platform slug

        Returns:
            Platform with TheGamesDB ID, or None if not supported
        """
        try:
            ups = UPS(slug)
        except ValueError:
            return None

        if ups not in TGDB_PLATFORM_MAP:
            return None

        platform_info = TGDB_PLATFORM_MAP[ups]
        return Platform(
            slug=slug,
            name=platform_info["name"],
            provider_ids={"thegamesdb": platform_info["id"]},
        )

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()


# Platform mapping from universal slugs to TheGamesDB platform IDs
TGDB_PLATFORM_MAP: dict[UPS, dict[str, Any]] = {
    UPS._3DO: {"id": 25, "name": "3DO"},
    UPS.ACORN_ARCHIMEDES: {"id": 4944, "name": "Acorn Archimedes"},
    UPS.ACORN_ELECTRON: {"id": 4954, "name": "Acorn Electron"},
    UPS.ACTION_MAX: {"id": 4976, "name": "Action Max"},
    UPS.AMIGA: {"id": 4911, "name": "Amiga"},
    UPS.AMIGA_CD32: {"id": 4947, "name": "Amiga CD32"},
    UPS.ACPC: {"id": 4914, "name": "Amstrad CPC"},
    UPS.AMSTRAD_GX4000: {"id": 4999, "name": "Amstrad GX4000"},
    UPS.ANDROID: {"id": 4916, "name": "Android"},
    UPS.APPLEII: {"id": 4942, "name": "Apple II"},
    UPS.ARCADE: {"id": 23, "name": "Arcade"},
    UPS.ATARI2600: {"id": 22, "name": "Atari 2600"},
    UPS.ATARI5200: {"id": 26, "name": "Atari 5200"},
    UPS.ATARI7800: {"id": 27, "name": "Atari 7800"},
    UPS.ATARI800: {"id": 4943, "name": "Atari 800"},
    UPS.JAGUAR: {"id": 28, "name": "Atari Jaguar"},
    UPS.ATARI_JAGUAR_CD: {"id": 29, "name": "Atari Jaguar CD"},
    UPS.LYNX: {"id": 4924, "name": "Atari Lynx"},
    UPS.ATARI_ST: {"id": 4937, "name": "Atari ST"},
    UPS.ATARI_XEGS: {"id": 30, "name": "Atari XEGS"},
    UPS.ASTROCADE: {"id": 4968, "name": "Bally Astrocade"},
    UPS.BBCMICRO: {"id": 5013, "name": "BBC Micro"},
    UPS.CASIO_LOOPY: {"id": 4991, "name": "Casio Loopy"},
    UPS.CASIO_PV_1000: {"id": 4964, "name": "Casio PV-1000"},
    UPS.COLECOVISION: {"id": 31, "name": "Colecovision"},
    UPS.C64: {"id": 40, "name": "Commodore 64"},
    UPS.DOS: {"id": 1, "name": "PC"},
    UPS.DC: {"id": 16, "name": "Sega Dreamcast"},
    UPS.FAIRCHILD_CHANNEL_F: {"id": 4928, "name": "Fairchild Channel F"},
    UPS.FDS: {"id": 4936, "name": "Famicom Disk System"},
    UPS.GB: {"id": 4, "name": "Nintendo Game Boy"},
    UPS.GBA: {"id": 5, "name": "Nintendo Game Boy Advance"},
    UPS.GBC: {"id": 41, "name": "Nintendo Game Boy Color"},
    UPS.GAMEGEAR: {"id": 20, "name": "Sega Game Gear"},
    UPS.GENESIS: {"id": 18, "name": "Sega Genesis"},
    UPS.INTELLIVISION: {"id": 32, "name": "Intellivision"},
    UPS.MSX: {"id": 4929, "name": "MSX"},
    UPS.N64: {"id": 3, "name": "Nintendo 64"},
    UPS.N3DS: {"id": 4912, "name": "Nintendo 3DS"},
    UPS.NDS: {"id": 8, "name": "Nintendo DS"},
    UPS.NES: {"id": 7, "name": "Nintendo Entertainment System (NES)"},
    UPS.NGC: {"id": 2, "name": "Nintendo GameCube"},
    UPS.NEO_GEO_CD: {"id": 4956, "name": "Neo Geo CD"},
    UPS.NEO_GEO_POCKET: {"id": 4922, "name": "Neo Geo Pocket"},
    UPS.NEO_GEO_POCKET_COLOR: {"id": 4923, "name": "Neo Geo Pocket Color"},
    UPS.NEOGEOAES: {"id": 24, "name": "Neo Geo"},
    UPS.ODYSSEY_2: {"id": 4927, "name": "Magnavox Odyssey 2"},
    UPS.PC_FX: {"id": 4930, "name": "PC-FX"},
    UPS.PSX: {"id": 10, "name": "Sony Playstation"},
    UPS.PS2: {"id": 11, "name": "Sony Playstation 2"},
    UPS.PS3: {"id": 12, "name": "Sony Playstation 3"},
    UPS.PSP: {"id": 13, "name": "Sony PSP"},
    UPS.PSVITA: {"id": 39, "name": "Sony Playstation Vita"},
    UPS.SATURN: {"id": 17, "name": "Sega Saturn"},
    UPS.SEGA32: {"id": 33, "name": "Sega 32X"},
    UPS.SEGACD: {"id": 21, "name": "Sega CD"},
    UPS.SG1000: {"id": 4949, "name": "Sega SG-1000"},
    UPS.SMS: {"id": 35, "name": "Sega Master System"},
    UPS.SNES: {"id": 6, "name": "Super Nintendo (SNES)"},
    UPS.SUPERGRAFX: {"id": 4955, "name": "PC Engine SuperGrafx"},
    UPS.SWITCH: {"id": 4971, "name": "Nintendo Switch"},
    UPS.TG16: {"id": 34, "name": "TurboGrafx 16"},
    UPS.TURBOGRAFX_CD: {"id": 4940, "name": "TurboGrafx CD"},
    UPS.VECTREX: {"id": 4939, "name": "Vectrex"},
    UPS.VIRTUALBOY: {"id": 4918, "name": "Nintendo Virtual Boy"},
    UPS.WII: {"id": 9, "name": "Nintendo Wii"},
    UPS.WIIU: {"id": 38, "name": "Nintendo Wii U"},
    UPS.WONDERSWAN: {"id": 4925, "name": "WonderSwan"},
    UPS.WONDERSWAN_COLOR: {"id": 4926, "name": "WonderSwan Color"},
    UPS.XBOX: {"id": 14, "name": "Microsoft Xbox"},
    UPS.XBOX360: {"id": 15, "name": "Microsoft Xbox 360"},
    UPS.ZXS: {"id": 4913, "name": "Sinclair ZX Spectrum"},
}
