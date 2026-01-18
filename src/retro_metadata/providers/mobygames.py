"""MobyGames metadata provider implementation."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

from retro_metadata.core.exceptions import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderRateLimitError,
)
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

# Regex to detect MobyGames ID tags in filenames like (moby-12345)
MOBYGAMES_TAG_REGEX: Final = re.compile(r"\(moby-(\d+)\)", re.IGNORECASE)


class MobyGamesProvider(MetadataProvider):
    """MobyGames metadata provider.

    Requires an api_key credential from MobyGames.

    Example:
        config = ProviderConfig(
            enabled=True,
            credentials={"api_key": "your_api_key"}
        )
        provider = MobyGamesProvider(config)
        results = await provider.search("Super Mario World", platform_id=15)
    """

    name = "mobygames"

    def __init__(
        self,
        config: "ProviderConfig",
        cache: "CacheBackend | None" = None,
        user_agent: str = "retro-metadata/1.0",
    ) -> None:
        super().__init__(config, cache)
        self._base_url = "https://api.mobygames.com/v1"
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
                headers={
                    "User-Agent": self._user_agent,
                },
                timeout=self.config.timeout,
            )
        return self._client

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make an API request to MobyGames."""
        client = await self._get_client()

        if params is None:
            params = {}
        params["api_key"] = self.api_key

        # Log request (mask API key)
        log_params = {k: v for k, v in params.items() if k != "api_key"}
        logger.debug("MobyGames API: GET %s%s", self._base_url, endpoint)
        logger.debug("MobyGames API params: %s", log_params)

        try:
            response = await client.get(endpoint, params=params)

            if response.status_code == 401:
                logger.debug("MobyGames API: 401 Unauthorized")
                raise ProviderAuthenticationError(self.name, "Invalid API key")
            elif response.status_code == 429:
                logger.debug("MobyGames API: 429 Rate limited")
                raise ProviderRateLimitError(self.name)

            response.raise_for_status()
            data = response.json()

            # Log full response body only when debug logging is enabled
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("MobyGames API response:\n%s", json.dumps(data, indent=2, ensure_ascii=False))

            return data
        except httpx.RequestError as e:
            logger.debug("MobyGames API error: %s", e)
            raise ProviderConnectionError(self.name, str(e)) from e

    async def search(
        self,
        query: str,
        platform_id: int | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search for games by name.

        Args:
            query: Search query string
            platform_id: MobyGames platform ID to filter by
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.is_enabled:
            return []

        params: dict[str, Any] = {
            "title": query,
            "limit": limit,
        }

        if platform_id:
            params["platform"] = platform_id

        results = await self._request("/games", params)

        if not isinstance(results, dict) or "games" not in results:
            return []

        search_results = []
        for game in results["games"]:
            cover_url = ""
            if "sample_cover" in game and game["sample_cover"]:
                cover_url = game["sample_cover"].get("image", "")

            platforms = []
            if "platforms" in game:
                platforms = [p.get("platform_name", "") for p in game["platforms"]]

            release_year = None
            if "platforms" in game and game["platforms"]:
                first_date = game["platforms"][0].get("first_release_date", "")
                if first_date:
                    try:
                        release_year = int(first_date[:4])
                    except (ValueError, IndexError):
                        pass

            search_results.append(SearchResult(
                name=game.get("title", ""),
                provider=self.name,
                provider_id=game["game_id"],
                cover_url=cover_url,
                platforms=platforms,
                release_year=release_year,
            ))

        return search_results

    async def get_by_id(self, game_id: int) -> GameResult | None:
        """Get game details by MobyGames ID.

        Args:
            game_id: MobyGames game ID

        Returns:
            GameResult with full details, or None if not found
        """
        if not self.is_enabled:
            return None

        result = await self._request(f"/games/{game_id}")

        if not isinstance(result, dict) or "game_id" not in result:
            return None

        return self._build_game_result(result)

    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Args:
            filename: ROM filename
            platform_id: MobyGames platform ID

        Returns:
            GameResult if a match is found, None otherwise
        """
        if not self.is_enabled:
            return None

        # Check for MobyGames ID tag in filename
        tagged_id = self.extract_id_from_filename(filename, MOBYGAMES_TAG_REGEX)
        if tagged_id:
            result = await self.get_by_id(tagged_id)
            if result:
                return result

        if not platform_id:
            return None

        # Clean the filename
        search_term = self._clean_filename(filename)

        # Try unidecode for ASCII conversion
        try:
            from unidecode import unidecode
            search_term = unidecode(search_term)
        except ImportError:
            pass

        # Search for the game
        params: dict[str, Any] = {
            "title": quote(search_term, safe="/ "),
            "platform": platform_id,
        }

        results = await self._request("/games", params)

        if not isinstance(results, dict) or "games" not in results or not results["games"]:
            # Try splitting by special characters
            terms = self.split_search_term(search_term)
            if len(terms) > 1:
                params["title"] = quote(terms[-1], safe="/ ")
                results = await self._request("/games", params)

        if not isinstance(results, dict) or "games" not in results or not results["games"]:
            return None

        # Find best match
        games_by_name = {g["title"]: g for g in results["games"]}
        best_match, score = self.find_best_match(
            search_term,
            list(games_by_name.keys()),
        )

        if best_match and best_match in games_by_name:
            result = self._build_game_result(games_by_name[best_match])
            result.match_score = score
            return result

        return None

    def _clean_filename(self, filename: str) -> str:
        """Remove tags and extension from filename."""
        # Remove extension
        name = re.sub(r"\.[^.]+$", "", filename)
        # Remove common tags like (USA), [!], etc.
        name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name)
        return name.strip()

    def _build_game_result(self, game: dict[str, Any]) -> GameResult:
        """Build a GameResult from MobyGames game data."""
        # Extract cover URL
        cover_url = ""
        if "sample_cover" in game and game["sample_cover"]:
            cover_url = game["sample_cover"].get("image", "")

        # Extract screenshots
        screenshot_urls = []
        if "sample_screenshots" in game:
            screenshot_urls = [s.get("image", "") for s in game["sample_screenshots"] if s.get("image")]

        # Extract metadata
        metadata = self._extract_metadata(game)

        return GameResult(
            name=game.get("title", ""),
            summary=game.get("description", ""),
            provider=self.name,
            provider_id=game["game_id"],
            provider_ids={"mobygames": game["game_id"]},
            artwork=Artwork(
                cover_url=cover_url,
                screenshot_urls=screenshot_urls,
            ),
            metadata=metadata,
            raw_response=game,
        )

    def _extract_metadata(self, game: dict[str, Any]) -> GameMetadata:
        """Extract GameMetadata from MobyGames game data."""
        # Extract genres
        genres = []
        if "genres" in game:
            genres = [g.get("genre_name", "") for g in game["genres"] if g.get("genre_name")]

        # Extract alternative names
        alt_names = []
        if "alternate_titles" in game:
            alt_names = [t.get("title", "") for t in game["alternate_titles"] if t.get("title")]

        # Extract platforms
        platforms = []
        if "platforms" in game:
            for p in game["platforms"]:
                platforms.append(Platform(
                    slug="",
                    name=p.get("platform_name", ""),
                    provider_ids={"mobygames": p.get("platform_id", 0)},
                ))

        # Extract rating
        total_rating = None
        if "moby_score" in game and game["moby_score"]:
            # MobyGames scores are out of 10, convert to 100
            try:
                total_rating = float(game["moby_score"]) * 10
            except (ValueError, TypeError):
                pass

        return GameMetadata(
            total_rating=total_rating,
            genres=genres,
            alternative_names=alt_names,
            platforms=platforms,
            raw_data=game,
        )

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
