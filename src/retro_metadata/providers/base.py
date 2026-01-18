"""Abstract base class for metadata providers."""

from __future__ import annotations

import abc
import re
from typing import TYPE_CHECKING, Any

from retro_metadata.core.matching import find_best_match
from retro_metadata.core.normalization import (
    SEARCH_TERM_SPLIT_PATTERN,
    normalize_cover_url,
    normalize_search_term,
)
from retro_metadata.types.common import GameResult, SearchResult

if TYPE_CHECKING:
    from retro_metadata.cache.base import CacheBackend
    from retro_metadata.core.config import ProviderConfig


class MetadataProvider(abc.ABC):
    """Abstract base class for all metadata providers.

    Providers implement the interface for fetching game metadata from
    different sources (IGDB, MobyGames, ScreenScraper, etc.).

    Attributes:
        name: Provider name (e.g., "igdb", "mobygames")
        config: Provider configuration
        cache: Optional cache backend
    """

    name: str = "base"

    def __init__(
        self,
        config: "ProviderConfig",
        cache: "CacheBackend | None" = None,
    ) -> None:
        self.config = config
        self.cache = cache
        self._min_similarity_score = 0.75

    @property
    def is_enabled(self) -> bool:
        """Check if this provider is enabled and configured."""
        return self.config.enabled and self.config.is_configured

    @abc.abstractmethod
    async def search(
        self,
        query: str,
        platform_id: int | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search for games by name.

        Args:
            query: Search query string
            platform_id: Provider-specific platform ID to filter by
            limit: Maximum number of results to return

        Returns:
            List of search results
        """

    @abc.abstractmethod
    async def get_by_id(self, game_id: int) -> GameResult | None:
        """Get game details by provider-specific ID.

        Args:
            game_id: Provider-specific game ID

        Returns:
            GameResult with full details, or None if not found
        """

    @abc.abstractmethod
    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Args:
            filename: ROM filename (e.g., "Super Mario World (USA).sfc")
            platform_id: Provider-specific platform ID

        Returns:
            GameResult if a match is found, None otherwise
        """

    async def heartbeat(self) -> bool:
        """Check if the provider API is accessible.

        Returns:
            True if the API is accessible, False otherwise
        """
        if not self.is_enabled:
            return False
        try:
            results = await self.search("test", limit=1)
            return True
        except Exception:
            return False

    def normalize_search_term(
        self,
        name: str,
        remove_articles: bool = True,
        remove_punctuation: bool = True,
    ) -> str:
        """Normalize a search term for comparison.

        Args:
            name: The search term to normalize
            remove_articles: Whether to remove articles
            remove_punctuation: Whether to remove punctuation

        Returns:
            Normalized search term
        """
        return normalize_search_term(name, remove_articles, remove_punctuation)

    def normalize_cover_url(self, url: str) -> str:
        """Normalize a cover image URL.

        Args:
            url: Cover URL to normalize

        Returns:
            Normalized URL
        """
        return normalize_cover_url(url)

    def find_best_match(
        self,
        search_term: str,
        candidates: list[str],
        min_similarity_score: float | None = None,
        split_candidate_name: bool = False,
    ) -> tuple[str | None, float]:
        """Find the best matching name from candidates.

        Args:
            search_term: The search term to match
            candidates: List of candidate names
            min_similarity_score: Minimum score (uses default if None)
            split_candidate_name: Whether to split candidates by delimiters

        Returns:
            Tuple of (best_match, score) or (None, 0.0)
        """
        if min_similarity_score is None:
            min_similarity_score = self._min_similarity_score
        return find_best_match(
            search_term,
            candidates,
            min_similarity_score,
            split_candidate_name,
        )

    def extract_id_from_filename(self, filename: str, pattern: re.Pattern) -> int | None:
        """Extract a provider ID from a filename using a regex pattern.

        Args:
            filename: The filename to search
            pattern: Regex pattern with a capturing group for the ID

        Returns:
            Extracted ID or None if not found
        """
        match = pattern.search(filename)
        if match:
            try:
                return int(match.group(1))
            except (IndexError, ValueError):
                return None
        return None

    def split_search_term(self, name: str) -> list[str]:
        """Split a search term by common delimiters.

        Args:
            name: The game name to split

        Returns:
            List of parts split by colons, dashes, and slashes
        """
        return SEARCH_TERM_SPLIT_PATTERN.split(name)

    async def _get_cached(self, key: str) -> Any | None:
        """Get a value from cache if available.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if self.cache is None:
            return None
        return await self.cache.get(f"{self.name}:{key}")

    async def _set_cached(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in cache if available.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        if self.cache is None:
            return
        await self.cache.set(f"{self.name}:{key}", value, ttl)

    async def close(self) -> None:
        """Clean up provider resources.

        Override in subclasses if cleanup is needed.
        """


class ProviderRegistry:
    """Registry for metadata providers.

    Provides a way to register and retrieve provider implementations.
    """

    _providers: dict[str, type[MetadataProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[MetadataProvider]) -> None:
        """Register a provider class.

        Args:
            name: Provider name
            provider_class: Provider class to register
        """
        cls._providers[name] = provider_class

    @classmethod
    def get(cls, name: str) -> type[MetadataProvider] | None:
        """Get a registered provider class.

        Args:
            name: Provider name

        Returns:
            Provider class or None if not registered
        """
        return cls._providers.get(name)

    @classmethod
    def list_providers(cls) -> list[str]:
        """Get list of registered provider names.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
