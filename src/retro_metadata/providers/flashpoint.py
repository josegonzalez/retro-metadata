"""Flashpoint Project metadata provider implementation.

Flashpoint Archive is a preservation project for Flash games and browser-based content.
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
from datetime import datetime
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

# Regex to detect Flashpoint ID tags in filenames (UUID format)
FLASHPOINT_TAG_REGEX: Final = re.compile(
    r"\(fp-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\)",
    re.IGNORECASE,
)

# UUID regex for filename extraction
UUID_REGEX: Final = re.compile(
    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
    re.IGNORECASE,
)


def _build_image_url(game_id: str, image_type: str = "Logos") -> str:
    """Build Flashpoint image URL from game ID."""
    if len(game_id) < 4:
        return ""
    return f"https://infinity.unstable.life/images/{image_type}/{game_id[:2]}/{game_id[2:4]}/{game_id}?type=jpg"


class FlashpointProvider(MetadataProvider):
    """Flashpoint Project metadata provider.

    Provides metadata for Flash games and browser-based content.
    Does not require authentication.

    Example:
        config = ProviderConfig(enabled=True)
        provider = FlashpointProvider(config)
        results = await provider.search("QWOP")
    """

    name = "flashpoint"

    def __init__(
        self,
        config: ProviderConfig,
        cache: CacheBackend | None = None,
        user_agent: str = "retro-metadata/1.0",
    ) -> None:
        super().__init__(config, cache)
        self._base_url = "https://db-api.unstable.life"
        self._user_agent = user_agent
        self._client: httpx.AsyncClient | None = None
        self._min_similarity_score = 0.75

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
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Make an API request to Flashpoint."""
        client = await self._get_client()

        logger.debug("Flashpoint API: GET %s%s", self._base_url, endpoint)
        if params:
            logger.debug("Flashpoint API params: %s", params)

        try:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            # Log full response body only when debug logging is enabled
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Flashpoint API response:\n%s", json.dumps(data, indent=2, ensure_ascii=False))

            return data
        except httpx.RequestError as e:
            logger.debug("Flashpoint API error: %s", e)
            raise ProviderConnectionError(self.name, str(e)) from e

    async def search(
        self,
        query: str,
        platform_id: int | None = None,  # noqa: ARG002
        limit: int = 30,
    ) -> list[SearchResult]:
        """Search for games by name.

        Args:
            query: Search query string
            platform_id: Not used by Flashpoint (browser-only)
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.is_enabled:
            return []

        params = {
            "smartSearch": query,
            "filter": "false",
        }

        result = await self._request("/search", params)

        if not result or not isinstance(result, list):
            return []

        search_results = []
        for game in result[:limit]:
            game_id = game.get("id", "")
            if not game_id:
                continue

            cover_url = _build_image_url(game_id, "Logos")

            # Extract release year
            release_year = None
            release_date = game.get("releaseDate", "")
            if release_date:
                with contextlib.suppress(ValueError, IndexError):
                    release_year = int(release_date[:4])

            search_results.append(
                SearchResult(
                    name=game.get("title", ""),
                    provider=self.name,
                    provider_id=game_id,  # Flashpoint uses UUID strings
                    slug=game_id,
                    cover_url=cover_url,
                    platforms=[game.get("platform", "Browser")],
                    release_year=release_year,
                )
            )

        return search_results

    async def get_by_id(self, game_id: str) -> GameResult | None:
        """Get game details by Flashpoint UUID.

        Args:
            game_id: Flashpoint game UUID

        Returns:
            GameResult with full details, or None if not found
        """
        if not self.is_enabled:
            return None

        params = {
            "id": game_id,
            "filter": "false",
        }

        result = await self._request("/search", params)

        if not result or not isinstance(result, list) or not result:
            return None

        game = result[0]
        if not game.get("id"):
            return None

        return self._build_game_result(game)

    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,  # noqa: ARG002
    ) -> GameResult | None:
        """Identify a game from a filename.

        Flashpoint filenames often contain UUIDs directly.

        Args:
            filename: ROM/game filename
            platform_id: Not used

        Returns:
            GameResult if a match is found, None otherwise
        """
        if not self.is_enabled:
            return None

        # Check for Flashpoint ID tag in filename
        match = FLASHPOINT_TAG_REGEX.search(filename)
        if match:
            result = await self.get_by_id(match.group(1))
            if result:
                return result

        # Check for UUID in filename
        uuid_match = UUID_REGEX.search(filename)
        if uuid_match:
            result = await self.get_by_id(uuid_match.group(0))
            if result:
                return result

        # Clean the filename and search
        search_term = self._clean_filename(filename)

        # Search for the game
        params = {
            "smartSearch": search_term,
            "filter": "false",
        }

        result = await self._request("/search", params)

        if not result or not isinstance(result, list) or not result:
            return None

        # Find best match
        games_by_name = {g["title"]: g for g in result if g.get("title")}
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
        # Remove UUID patterns
        name = UUID_REGEX.sub("", name)
        return name.strip()

    def _build_game_result(self, game: dict[str, Any]) -> GameResult:
        """Build a GameResult from Flashpoint game data."""
        game_id = game.get("id", "")

        cover_url = _build_image_url(game_id, "Logos")
        screenshot_urls = [_build_image_url(game_id, "Screenshots")]

        # Extract metadata
        metadata = self._extract_metadata(game)

        return GameResult(
            name=game.get("title", ""),
            summary=game.get("originalDescription", ""),
            provider=self.name,
            provider_id=game_id,
            provider_ids={"flashpoint": game_id},
            slug=game_id,
            artwork=Artwork(
                cover_url=cover_url,
                screenshot_urls=screenshot_urls,
            ),
            metadata=metadata,
            raw_response=game,
        )

    def _extract_metadata(self, game: dict[str, Any]) -> GameMetadata:
        """Extract GameMetadata from Flashpoint game data."""
        # Release date
        first_release_date = None
        release_year = None
        release_date = game.get("releaseDate", "")
        if release_date:
            try:
                date_obj = datetime.strptime(release_date, "%Y-%m-%d")
                first_release_date = int(date_obj.timestamp())
                release_year = date_obj.year
            except (ValueError, TypeError):
                pass

        # Genres (from tags)
        genres = game.get("tags", [])
        if isinstance(genres, str):
            genres = [g.strip() for g in genres.split(",")]

        # Companies
        companies = []
        if game.get("developer"):
            companies.append(game["developer"])
        if game.get("publisher") and game["publisher"] not in companies:
            companies.append(game["publisher"])

        # Franchises (from series)
        franchises = []
        series = game.get("series", [])
        if isinstance(series, str) and series:
            franchises = [series]
        elif isinstance(series, list):
            franchises = series

        # Game modes
        game_modes = []
        play_mode = game.get("playMode", "")
        if play_mode:
            game_modes = [play_mode]

        return GameMetadata(
            first_release_date=first_release_date,
            genres=genres if isinstance(genres, list) else [],
            franchises=franchises,
            companies=list(dict.fromkeys(companies)),
            game_modes=game_modes,
            developer=game.get("developer", ""),
            publisher=game.get("publisher", ""),
            release_year=release_year,
            raw_data={
                "source": game.get("source", ""),
                "status": game.get("status", ""),
                "version": game.get("version", ""),
                "language": game.get("language", ""),
                "library": game.get("library", ""),
                "platform": game.get("platform", ""),
                "notes": game.get("notes", ""),
            },
        )

    def get_platform(self, slug: str) -> Platform | None:
        """Get platform information for a slug.

        Flashpoint only supports browser-based content.

        Args:
            slug: Universal platform slug

        Returns:
            Platform with Flashpoint ID, or None if not supported
        """
        try:
            ups = UPS(slug)
        except ValueError:
            return None

        if ups not in FLASHPOINT_PLATFORM_MAP:
            return None

        platform_info = FLASHPOINT_PLATFORM_MAP[ups]
        return Platform(
            slug=slug,
            name=platform_info["name"],
            provider_ids={"flashpoint": platform_info["id"]},
        )

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()


# Flashpoint only supports browser-based content
FLASHPOINT_PLATFORM_MAP: dict[UPS, dict[str, Any]] = {
    UPS.BROWSER: {"id": 1, "name": "Browser (Flash/HTML5)"},
}
