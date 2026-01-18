"""HowLongToBeat metadata provider implementation."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any, Final

import httpx

logger = logging.getLogger(__name__)

from retro_metadata.core.exceptions import (
    ProviderConnectionError,
)
from retro_metadata.providers.base import MetadataProvider
from retro_metadata.types.common import (
    Artwork,
    GameMetadata,
    GameResult,
    SearchResult,
)

if TYPE_CHECKING:
    from retro_metadata.cache.base import CacheBackend
    from retro_metadata.core.config import ProviderConfig

# Regex to detect HLTB ID tags in filenames like (hltb-12345)
HLTB_TAG_REGEX: Final = re.compile(r"\(hltb-(\d+)\)", re.IGNORECASE)

# Base URL for images
HLTB_IMAGE_URL: Final = "https://howlongtobeat.com/games/"


class HLTBProvider(MetadataProvider):
    """HowLongToBeat metadata provider.

    Provides game completion time data and basic metadata.
    Note: HLTB doesn't require authentication.

    Example:
        config = ProviderConfig(enabled=True)
        provider = HLTBProvider(config)
        results = await provider.search("Super Mario World")
    """

    name = "hltb"

    def __init__(
        self,
        config: "ProviderConfig",
        cache: "CacheBackend | None" = None,
        user_agent: str = "retro-metadata/1.0",
    ) -> None:
        super().__init__(config, cache)
        self._base_url = "https://howlongtobeat.com/api"
        self._user_agent = user_agent
        self._client: httpx.AsyncClient | None = None
        self._min_similarity_score = 0.6

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

    async def _request(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an API request to HowLongToBeat."""
        client = await self._get_client()

        url = f"{self._base_url}/{endpoint}"

        logger.debug("HLTB API: POST %s", url)
        if data:
            logger.debug("HLTB API data: %s", data)

        try:
            response = await client.post(url, json=data)
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
        platform_id: int | None = None,
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
                try:
                    release_year = int(game["release_world"])
                except ValueError:
                    pass

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
        platform_id: int | None = None,
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
            try:
                release_year = int(game["release_world"])
            except ValueError:
                pass

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

        return GameMetadata(
            release_year=release_year,
            game_modes=game_modes,
            developer=developer,
            publisher=publisher,
            raw_data={
                "main_story": game.get("comp_main"),
                "main_plus_extras": game.get("comp_plus"),
                "completionist": game.get("comp_100"),
                "all_styles": game.get("comp_all"),
                "platforms": platforms_list,
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

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
