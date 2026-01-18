"""Hasheous metadata provider implementation.

Hasheous is a service that matches ROM hashes to game metadata.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any, Final

import httpx

logger = logging.getLogger(__name__)

from retro_metadata.core.exceptions import (
    ProviderConnectionError,
    ProviderRateLimitError,
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

# Regex to detect Hasheous ID tags in filenames like (hasheous-xxxxx)
HASHEOUS_TAG_REGEX: Final = re.compile(r"\(hasheous-([a-f0-9-]+)\)", re.IGNORECASE)


class HasheousProvider(MetadataProvider):
    """Hasheous hash-based metadata provider.

    Matches ROM hashes (MD5, SHA1, CRC) to game metadata.
    Does not require authentication.

    Example:
        config = ProviderConfig(enabled=True)
        provider = HasheousProvider(config)
        result = await provider.lookup_by_hash(md5="abc123...")
    """

    name = "hasheous"

    def __init__(
        self,
        config: "ProviderConfig",
        cache: "CacheBackend | None" = None,
        user_agent: str = "retro-metadata/1.0",
    ) -> None:
        super().__init__(config, cache)
        self._base_url = "https://hasheous.org/api/v1"
        self._user_agent = user_agent
        self._client: httpx.AsyncClient | None = None
        self._min_similarity_score = 0.6

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "application/json",
                },
                timeout=self.config.timeout,
            )
        return self._client

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        """Make an API request to Hasheous."""
        client = await self._get_client()

        logger.debug("Hasheous API: %s %s%s", method, self._base_url, endpoint)
        if params:
            logger.debug("Hasheous API params: %s", params)
        if json_data:
            logger.debug("Hasheous API data: %s", json_data)

        try:
            if method == "POST":
                response = await client.post(endpoint, json=json_data)
            else:
                response = await client.get(endpoint, params=params)

            if response.status_code == 429:
                logger.debug("Hasheous API: 429 Rate limited")
                raise ProviderRateLimitError(self.name)
            elif response.status_code == 404:
                logger.debug("Hasheous API: 404 Not found")
                return None

            response.raise_for_status()
            data = response.json()

            # Log full response body only when debug logging is enabled
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Hasheous API response:\n%s", json.dumps(data, indent=2, ensure_ascii=False))

            return data
        except httpx.RequestError as e:
            logger.debug("Hasheous API error: %s", e)
            raise ProviderConnectionError(self.name, str(e)) from e

    async def search(
        self,
        query: str,
        platform_id: int | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search for games by name.

        Note: Hasheous primarily works with hashes, not name searches.
        This method provides basic search functionality.

        Args:
            query: Search query string
            platform_id: Platform ID to filter by (optional)
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.is_enabled:
            return []

        # Hasheous search endpoint
        params = {"q": query}
        if platform_id:
            params["platform"] = str(platform_id)

        result = await self._request("/search", params)

        if not result or not isinstance(result, list):
            return []

        search_results = []
        for game in result[:limit]:
            game_id = game.get("id")
            if not game_id:
                continue

            search_results.append(
                SearchResult(
                    name=game.get("name", ""),
                    provider=self.name,
                    provider_id=game_id,
                    cover_url=game.get("cover_url", ""),
                    platforms=game.get("platforms", []),
                )
            )

        return search_results

    async def get_by_id(self, game_id: int | str) -> GameResult | None:
        """Get game details by Hasheous ID.

        Args:
            game_id: Hasheous game ID

        Returns:
            GameResult with full details, or None if not found
        """
        if not self.is_enabled:
            return None

        result = await self._request(f"/games/{game_id}")

        if not result or not isinstance(result, dict):
            return None

        return self._build_game_result(result)

    async def lookup_by_hash(
        self,
        md5: str | None = None,
        sha1: str | None = None,
        crc: str | None = None,
    ) -> GameResult | None:
        """Look up a game by ROM hash.

        Args:
            md5: MD5 hash of the ROM
            sha1: SHA1 hash of the ROM
            crc: CRC32 hash of the ROM

        Returns:
            GameResult if found, None otherwise
        """
        if not self.is_enabled:
            return None

        if not (md5 or sha1 or crc):
            return None

        # Build request data
        hashes = {}
        if md5:
            hashes["md5"] = md5
        if sha1:
            hashes["sha1"] = sha1
        if crc:
            hashes["crc32"] = crc

        result = await self._request("/lookup", method="POST", json_data=hashes)

        if not result or not isinstance(result, dict):
            return None

        return self._build_game_result(result)

    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Note: Hasheous works best with hash lookups rather than filename matching.

        Args:
            filename: ROM filename
            platform_id: Platform ID (optional)

        Returns:
            GameResult if a match is found, None otherwise
        """
        if not self.is_enabled:
            return None

        # Check for Hasheous ID tag in filename
        tagged_id = self.extract_id_from_filename(filename, HASHEOUS_TAG_REGEX)
        if tagged_id:
            result = await self.get_by_id(tagged_id)
            if result:
                return result

        # Hasheous primarily works with hashes, so name-based identification
        # has limited functionality. Try a search instead.
        search_term = self._clean_filename(filename)
        results = await self.search(search_term, platform_id, limit=10)

        if not results:
            return None

        # Find best match
        games_by_name = {r.name: r for r in results}
        best_match, score = self.find_best_match(
            search_term, list(games_by_name.keys())
        )

        if best_match and best_match in games_by_name:
            search_result = games_by_name[best_match]
            # Get full details
            full_result = await self.get_by_id(search_result.provider_id)
            if full_result:
                full_result.match_score = score
                return full_result

        return None

    def _clean_filename(self, filename: str) -> str:
        """Remove tags and extension from filename."""
        name = re.sub(r"\.[^.]+$", "", filename)
        name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name)
        return name.strip()

    def _build_game_result(self, game: dict[str, Any]) -> GameResult:
        """Build a GameResult from Hasheous game data."""
        game_id = game.get("id", 0)

        # Get artwork
        cover_url = game.get("cover_url", "") or game.get("boxart", "")
        screenshot_urls = game.get("screenshots", [])

        # Extract metadata
        metadata = self._extract_metadata(game)

        return GameResult(
            name=game.get("name", "") or game.get("title", ""),
            summary=game.get("description", "") or game.get("overview", ""),
            provider=self.name,
            provider_id=game_id,
            provider_ids={"hasheous": game_id},
            artwork=Artwork(
                cover_url=cover_url,
                screenshot_urls=screenshot_urls,
            ),
            metadata=metadata,
            raw_response=game,
        )

    def _extract_metadata(self, game: dict[str, Any]) -> GameMetadata:
        """Extract GameMetadata from Hasheous game data."""
        # Genres
        genres = game.get("genres", [])
        if isinstance(genres, str):
            genres = [g.strip() for g in genres.split(",")]

        # Companies
        companies = []
        if game.get("publisher"):
            companies.append(game["publisher"])
        if game.get("developer"):
            companies.append(game["developer"])

        # Player count
        player_count = str(game.get("players", 1))

        # Release year
        release_year = None
        release_date = game.get("release_date") or game.get("year")
        if release_date:
            try:
                if isinstance(release_date, int):
                    release_year = release_date
                else:
                    release_year = int(str(release_date)[:4])
            except (ValueError, IndexError):
                pass

        return GameMetadata(
            genres=genres if isinstance(genres, list) else [],
            companies=list(dict.fromkeys(companies)),
            player_count=player_count,
            release_year=release_year,
            developer=game.get("developer", ""),
            publisher=game.get("publisher", ""),
            raw_data=game,
        )

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
