"""Playmatch hash-matching provider implementation.

Playmatch is a service for matching ROMs by hash to external metadata providers.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import TYPE_CHECKING, Any

import httpx

logger = logging.getLogger(__name__)

from retro_metadata.core.exceptions import (
    ProviderConnectionError,
)
from retro_metadata.providers.base import MetadataProvider
from retro_metadata.types.common import (
    GameResult,
    SearchResult,
)

if TYPE_CHECKING:
    from retro_metadata.cache.base import CacheBackend
    from retro_metadata.core.config import ProviderConfig


class GameMatchType(str, Enum):
    """Types of matches Playmatch can return."""

    SHA256 = "SHA256"
    SHA1 = "SHA1"
    MD5 = "MD5"
    FILE_NAME_AND_SIZE = "FileNameAndSize"
    NO_MATCH = "NoMatch"


class PlaymatchProvider(MetadataProvider):
    """Playmatch hash-matching provider.

    Matches ROM hashes to external metadata providers (primarily IGDB).
    Returns provider IDs rather than full metadata - use those IDs with
    the respective provider to get full details.

    Does not require authentication.

    Example:
        config = ProviderConfig(enabled=True)
        provider = PlaymatchProvider(config)
        result = await provider.lookup_by_hash(
            filename="game.rom",
            file_size=1234567,
            md5="abc123...",
            sha1="def456..."
        )
    """

    name = "playmatch"

    def __init__(
        self,
        config: "ProviderConfig",
        cache: "CacheBackend | None" = None,
        user_agent: str = "retro-metadata/1.0",
    ) -> None:
        super().__init__(config, cache)
        self._base_url = "https://playmatch.retrorealm.dev/api"
        self._user_agent = user_agent
        self._client: httpx.AsyncClient | None = None

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
    ) -> dict[str, Any] | None:
        """Make an API request to Playmatch."""
        client = await self._get_client()

        logger.debug("Playmatch API: GET %s%s", self._base_url, endpoint)
        if params:
            logger.debug("Playmatch API params: %s", params)

        try:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            # Log full response body only when debug logging is enabled
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Playmatch API response:\n%s", json.dumps(data, indent=2, ensure_ascii=False))

            return data
        except httpx.RequestError as e:
            logger.debug("Playmatch API error: %s", e)
            raise ProviderConnectionError(self.name, str(e)) from e
        except httpx.HTTPStatusError as e:
            logger.debug("Playmatch API HTTP error: %s", e)
            return None

    async def search(
        self,
        query: str,
        platform_id: int | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search for games by name.

        Note: Playmatch doesn't support name-based search. Use lookup_by_hash instead.

        Args:
            query: Search query string (not used)
            platform_id: Platform ID (not used)
            limit: Maximum results (not used)

        Returns:
            Empty list (Playmatch only supports hash lookups)
        """
        return []

    async def get_by_id(self, game_id: int) -> GameResult | None:
        """Get game details by ID.

        Note: Playmatch doesn't support ID lookups. Use the returned provider
        IDs with the respective provider (e.g., IGDB).

        Args:
            game_id: Game ID (not used)

        Returns:
            None (Playmatch only supports hash lookups)
        """
        return None

    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Note: For Playmatch, use lookup_by_hash with file hash information
        for better results.

        Args:
            filename: ROM filename
            platform_id: Platform ID (not used)

        Returns:
            None (use lookup_by_hash instead)
        """
        return None

    async def lookup_by_hash(
        self,
        filename: str,
        file_size: int,
        md5: str | None = None,
        sha1: str | None = None,
    ) -> dict[str, Any] | None:
        """Look up a ROM by hash to get external provider IDs.

        Args:
            filename: Name of the ROM file
            file_size: Size of the file in bytes
            md5: MD5 hash of the ROM (optional)
            sha1: SHA1 hash of the ROM (optional)

        Returns:
            Dictionary with match information including:
            - igdb_id: IGDB game ID if found
            - match_type: Type of match (SHA256, SHA1, MD5, FileNameAndSize, NoMatch)
            - external_metadata: List of external provider matches
        """
        if not self.is_enabled:
            return None

        params: dict[str, Any] = {
            "fileName": filename,
            "fileSize": str(file_size),
        }

        if md5:
            params["md5"] = md5
        if sha1:
            params["sha1"] = sha1

        result = await self._request("/identify/ids", params)

        if not result:
            return None

        match_type = result.get("gameMatchType", GameMatchType.NO_MATCH.value)
        if match_type == GameMatchType.NO_MATCH.value:
            return None

        external_metadata = result.get("externalMetadata", [])
        if not external_metadata:
            return None

        # Extract IGDB ID if available
        igdb_id = None
        for metadata in external_metadata:
            if metadata.get("providerName") == "IGDB":
                provider_id = metadata.get("providerId")
                if provider_id:
                    try:
                        igdb_id = int(provider_id)
                    except ValueError:
                        pass
                break

        return {
            "igdb_id": igdb_id,
            "match_type": match_type,
            "external_metadata": external_metadata,
        }

    async def get_igdb_id(
        self,
        filename: str,
        file_size: int,
        md5: str | None = None,
        sha1: str | None = None,
    ) -> int | None:
        """Convenience method to get just the IGDB ID for a ROM.

        Args:
            filename: Name of the ROM file
            file_size: Size of the file in bytes
            md5: MD5 hash of the ROM (optional)
            sha1: SHA1 hash of the ROM (optional)

        Returns:
            IGDB game ID if found, None otherwise
        """
        result = await self.lookup_by_hash(filename, file_size, md5, sha1)
        if result:
            return result.get("igdb_id")
        return None

    async def heartbeat(self) -> bool:
        """Check if the Playmatch API is available.

        Returns:
            True if the API is responding, False otherwise
        """
        if not self.is_enabled:
            return False

        try:
            result = await self._request("/health")
            return result is not None
        except Exception:
            return False

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
