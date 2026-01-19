"""SteamGridDB artwork provider implementation."""

from __future__ import annotations

import json
import logging
import re
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final

import httpx

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
    SearchResult,
)

if TYPE_CHECKING:
    from retro_metadata.cache.base import CacheBackend
    from retro_metadata.core.config import ProviderConfig

logger = logging.getLogger(__name__)


class SGDBDimension(StrEnum):
    """SteamGridDB grid dimension options."""

    # Vertical grids
    STEAM_VERTICAL = "600x900"
    GOG_GALAXY = "342x482"
    SQUARE = "512x512"
    SQUARE_ICON = "256x256"

    # Horizontal grids
    STEAM_HORIZONTAL = "460x215"
    LEGACY = "920x430"
    OLD = "460x215"

    # Heroes
    HERO_BLURRED = "1920x620"
    HERO_MATERIAL = "3840x1240"

    # Logos
    LOGO_CUSTOM = "custom"


class SGDBStyle(StrEnum):
    """SteamGridDB artwork style options."""

    # Grid styles
    ALTERNATE = "alternate"
    BLURRED = "blurred"
    WHITE_LOGO = "white_logo"
    MATERIAL = "material"
    NO_LOGO = "no_logo"

    # Hero styles
    HERO_ALTERNATE = "alternate"
    HERO_BLURRED = "blurred"
    HERO_MATERIAL = "material"

    # Logo styles
    LOGO_OFFICIAL = "official"
    LOGO_WHITE = "white"
    LOGO_BLACK = "black"
    LOGO_CUSTOM = "custom"


class SGDBMime(StrEnum):
    """SteamGridDB MIME type options."""

    PNG = "image/png"
    JPEG = "image/jpeg"
    WEBP = "image/webp"
    ICO = "image/vnd.microsoft.icon"

# Regex to detect SteamGridDB ID tags in filenames like (sgdb-12345)
SGDB_TAG_REGEX: Final = re.compile(r"\(sgdb-(\d+)\)", re.IGNORECASE)


class SteamGridDBProvider(MetadataProvider):
    """SteamGridDB artwork provider.

    Provides artwork (covers, banners, logos, icons, heroes) for games.
    Note: This provider focuses on artwork rather than full metadata.

    Requires an api_key credential from SteamGridDB.

    Example:
        config = ProviderConfig(
            enabled=True,
            credentials={"api_key": "your_api_key"}
        )
        provider = SteamGridDBProvider(config)
        results = await provider.search("Super Mario World")
    """

    name = "steamgriddb"

    def __init__(
        self,
        config: ProviderConfig,
        cache: CacheBackend | None = None,
        user_agent: str = "retro-metadata/1.0",
    ) -> None:
        super().__init__(config, cache)
        self._base_url = "https://www.steamgriddb.com/api/v2"
        self._user_agent = user_agent
        self._client: httpx.AsyncClient | None = None
        # High similarity threshold for better matches (RomM uses 0.98)
        self._min_similarity_score = 0.98
        # Content filter defaults (can be configured)
        self._nsfw = config.settings.get("nsfw", False)
        self._humor = config.settings.get("humor", True)
        self._epilepsy = config.settings.get("epilepsy", True)

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
                    "Authorization": f"Bearer {self.api_key}",
                },
                timeout=self.config.timeout,
            )
        return self._client

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an API request to SteamGridDB."""
        client = await self._get_client()

        logger.debug("SteamGridDB API: GET %s%s", self._base_url, endpoint)
        if params:
            logger.debug("SteamGridDB API params: %s", params)

        try:
            response = await client.get(endpoint, params=params)

            if response.status_code == 401:
                logger.debug("SteamGridDB API: 401 Unauthorized")
                raise ProviderAuthenticationError(self.name, "Invalid API key")
            elif response.status_code == 429:
                logger.debug("SteamGridDB API: 429 Rate limited")
                raise ProviderRateLimitError(self.name)

            response.raise_for_status()
            data = response.json()

            # Log full response body only when debug logging is enabled
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("SteamGridDB API response:\n%s", json.dumps(data, indent=2, ensure_ascii=False))

            return data
        except httpx.RequestError as e:
            logger.debug("SteamGridDB API error: %s", e)
            raise ProviderConnectionError(self.name, str(e)) from e

    async def search(
        self,
        query: str,
        platform_id: int | None = None,  # noqa: ARG002
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search for games by name.

        Args:
            query: Search query string
            platform_id: Not used by SteamGridDB
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.is_enabled:
            return []

        result = await self._request("/search/autocomplete/" + query)

        if not result.get("success") or "data" not in result:
            return []

        search_results = []
        for game in result["data"][:limit]:
            # Get cover image for the game
            cover_url = ""
            try:
                grids = await self._request(f"/grids/game/{game['id']}")
                if grids.get("success") and grids.get("data"):
                    cover_url = grids["data"][0].get("url", "")
            except Exception:
                pass

            search_results.append(
                SearchResult(
                    name=game.get("name", ""),
                    provider=self.name,
                    provider_id=game["id"],
                    cover_url=cover_url,
                    release_year=game.get("release_date"),
                )
            )

        return search_results

    async def get_by_id(self, game_id: int) -> GameResult | None:
        """Get game artwork by SteamGridDB ID.

        Args:
            game_id: SteamGridDB game ID

        Returns:
            GameResult with artwork, or None if not found
        """
        if not self.is_enabled:
            return None

        result = await self._request(f"/games/id/{game_id}")

        if not result.get("success") or "data" not in result:
            return None

        game = result["data"]

        # Fetch all artwork types
        artwork = await self._fetch_all_artwork(game_id)

        return GameResult(
            name=game.get("name", ""),
            provider=self.name,
            provider_id=game["id"],
            provider_ids={"steamgriddb": game["id"]},
            artwork=artwork,
            metadata=GameMetadata(
                release_year=game.get("release_date"),
            ),
            raw_response=game,
        )

    async def _fetch_all_artwork(self, game_id: int) -> Artwork:
        """Fetch all artwork types for a game."""
        artwork = Artwork()

        # Fetch grids (covers) with content filters
        try:
            grids = await self._fetch_grids(game_id)
            if grids:
                artwork.cover_url = grids[0].get("url", "")
        except Exception:
            pass

        # Fetch heroes (banners/backgrounds)
        try:
            heroes = await self._fetch_heroes(game_id)
            if heroes:
                artwork.background_url = heroes[0].get("url", "")
                if len(heroes) > 1:
                    artwork.banner_url = heroes[1].get("url", "")
        except Exception:
            pass

        # Fetch logos
        try:
            logos = await self._fetch_logos(game_id)
            if logos:
                artwork.logo_url = logos[0].get("url", "")
        except Exception:
            pass

        # Fetch icons
        try:
            icons = await self._fetch_icons(game_id)
            if icons:
                artwork.icon_url = icons[0].get("url", "")
        except Exception:
            pass

        return artwork

    def _build_filter_params(
        self,
        dimensions: list[SGDBDimension] | None = None,
        styles: list[SGDBStyle] | None = None,
        mimes: list[SGDBMime] | None = None,
        types: list[str] | None = None,
    ) -> dict[str, str]:
        """Build filter parameters for artwork requests."""
        params: dict[str, str] = {}

        # Content filters
        nsfw = "any" if self._nsfw else "false"
        humor = "any" if self._humor else "false"
        epilepsy = "any" if self._epilepsy else "false"

        params["nsfw"] = nsfw
        params["humor"] = humor
        params["epilepsy"] = epilepsy

        if dimensions:
            params["dimensions"] = ",".join(dimensions)
        if styles:
            params["styles"] = ",".join(styles)
        if mimes:
            params["mimes"] = ",".join(mimes)
        if types:
            params["types"] = ",".join(types)

        return params

    async def _fetch_grids(
        self,
        game_id: int,
        dimensions: list[SGDBDimension] | None = None,
        styles: list[SGDBStyle] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch grid artwork with optional filters."""
        params = self._build_filter_params(dimensions=dimensions, styles=styles)
        result = await self._request(f"/grids/game/{game_id}", params or None)
        if result.get("success") and result.get("data"):
            return result["data"]
        return []

    async def _fetch_heroes(
        self,
        game_id: int,
        dimensions: list[SGDBDimension] | None = None,
        styles: list[SGDBStyle] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch hero artwork with optional filters."""
        params = self._build_filter_params(dimensions=dimensions, styles=styles)
        result = await self._request(f"/heroes/game/{game_id}", params or None)
        if result.get("success") and result.get("data"):
            return result["data"]
        return []

    async def _fetch_logos(
        self,
        game_id: int,
        styles: list[SGDBStyle] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch logo artwork with optional filters."""
        params = self._build_filter_params(styles=styles)
        result = await self._request(f"/logos/game/{game_id}", params or None)
        if result.get("success") and result.get("data"):
            return result["data"]
        return []

    async def _fetch_icons(
        self,
        game_id: int,
        dimensions: list[SGDBDimension] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch icon artwork with optional filters."""
        params = self._build_filter_params(dimensions=dimensions)
        result = await self._request(f"/icons/game/{game_id}", params or None)
        if result.get("success") and result.get("data"):
            return result["data"]
        return []

    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,  # noqa: ARG002
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Args:
            filename: ROM filename
            platform_id: Not used by SteamGridDB

        Returns:
            GameResult if a match is found, None otherwise
        """
        if not self.is_enabled:
            return None

        # Check for SteamGridDB ID tag in filename
        tagged_id = self.extract_id_from_filename(filename, SGDB_TAG_REGEX)
        if tagged_id:
            result = await self.get_by_id(tagged_id)
            if result:
                return result

        # Clean the filename
        search_term = self._clean_filename(filename)

        # Search for the game
        result = await self._request("/search/autocomplete/" + search_term)

        if not result.get("success") or not result.get("data"):
            # Try splitting by special characters
            terms = self.split_search_term(search_term)
            if len(terms) > 1:
                result = await self._request("/search/autocomplete/" + terms[-1])

        if not result.get("success") or not result.get("data"):
            return None

        # Find best match
        games_by_name = {g["name"]: g for g in result["data"]}
        best_match, score = self.find_best_match(
            search_term, list(games_by_name.keys())
        )

        if best_match and best_match in games_by_name:
            game = games_by_name[best_match]
            artwork = await self._fetch_all_artwork(game["id"])

            game_result = GameResult(
                name=game.get("name", ""),
                provider=self.name,
                provider_id=game["id"],
                provider_ids={"steamgriddb": game["id"]},
                artwork=artwork,
                metadata=GameMetadata(
                    release_year=game.get("release_date"),
                ),
                match_score=score,
                raw_response=game,
            )
            return game_result

        return None

    def _clean_filename(self, filename: str) -> str:
        """Remove tags and extension from filename."""
        name = re.sub(r"\.[^.]+$", "", filename)
        name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name)
        return name.strip()

    async def get_artwork_for_steam_id(self, steam_app_id: int) -> Artwork:
        """Get artwork using a Steam App ID.

        Args:
            steam_app_id: Steam application ID

        Returns:
            Artwork object with available images
        """
        if not self.is_enabled:
            return Artwork()

        # Look up game by Steam ID
        result = await self._request(f"/games/steam/{steam_app_id}")

        if not result.get("success") or "data" not in result:
            return Artwork()

        game_id = result["data"]["id"]
        return await self._fetch_all_artwork(game_id)

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
