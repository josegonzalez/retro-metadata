"""MetadataClient - Main entry point for the retro-metadata library."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from retro_metadata.cache.base import CacheBackend, NullCache
from retro_metadata.cache.memory import MemoryCache
from retro_metadata.core.config import MetadataConfig
from retro_metadata.core.exceptions import ProviderNotFoundError
from retro_metadata.platforms.mappings import (
    get_igdb_platform_id,
    get_mobygames_platform_id,
    get_retroachievements_platform_id,
    get_screenscraper_platform_id,
)
from retro_metadata.providers.base import MetadataProvider
from retro_metadata.types.common import GameResult, SearchResult

if TYPE_CHECKING:
    from retro_metadata.platforms.slugs import UniversalPlatformSlug

logger = logging.getLogger(__name__)


class MetadataClient:
    """Unified interface for fetching game metadata from multiple providers.

    The MetadataClient provides a high-level API for searching, identifying,
    and retrieving game metadata from various sources like IGDB, MobyGames,
    ScreenScraper, and more.

    Example:
        from retro_metadata import MetadataClient, MetadataConfig, ProviderConfig

        config = MetadataConfig(
            igdb=ProviderConfig(
                enabled=True,
                credentials={
                    "client_id": "your_client_id",
                    "client_secret": "your_client_secret"
                }
            )
        )

        async with MetadataClient(config) as client:
            # Search for games
            results = await client.search("Super Mario World", platform="snes")

            # Identify a ROM file
            game = await client.identify("Super Mario World (USA).sfc", platform="snes")

            # Get by provider ID
            game = await client.get_by_id("igdb", 1234)
    """

    def __init__(
        self,
        config: MetadataConfig,
        cache: CacheBackend | None = None,
    ) -> None:
        """Initialize the MetadataClient.

        Args:
            config: Configuration for all providers
            cache: Cache backend (uses MemoryCache by default)
        """
        self.config = config
        self._cache = cache
        self._providers: dict[str, MetadataProvider] = {}
        self._initialized = False

    async def __aenter__(self) -> MetadataClient:
        """Async context manager entry."""
        await self._initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _initialize(self) -> None:
        """Initialize providers and cache."""
        if self._initialized:
            return

        # Initialize cache
        if self._cache is None:
            cache_config = self.config.cache
            if cache_config.backend == "memory":
                self._cache = MemoryCache(
                    max_size=cache_config.max_size,
                    default_ttl=cache_config.ttl,
                )
            elif cache_config.backend == "redis":
                try:
                    from redis.asyncio import Redis

                    from retro_metadata.cache.redis import RedisCache

                    client = Redis.from_url(cache_config.connection_string)
                    self._cache = RedisCache(client, default_ttl=cache_config.ttl)
                except ImportError:
                    self._cache = MemoryCache()
            elif cache_config.backend == "sqlite":
                try:
                    from retro_metadata.cache.sqlite import SQLiteCache

                    self._cache = SQLiteCache(
                        cache_config.connection_string or "retro_metadata_cache.db",
                        default_ttl=cache_config.ttl,
                    )
                except ImportError:
                    self._cache = MemoryCache()
            elif cache_config.backend == "none":
                self._cache = NullCache()
            else:
                self._cache = MemoryCache()

        # Initialize providers
        await self._init_providers()
        self._initialized = True

    async def _init_providers(self) -> None:
        """Initialize all enabled providers."""
        # IGDB
        if self.config.igdb.enabled:
            from retro_metadata.providers.igdb import IGDBProvider

            self._providers["igdb"] = IGDBProvider(
                self.config.igdb,
                self._cache,
                self.config.user_agent,
            )

        # MobyGames
        if self.config.mobygames.enabled:
            from retro_metadata.providers.mobygames import MobyGamesProvider

            self._providers["mobygames"] = MobyGamesProvider(
                self.config.mobygames,
                self._cache,
                self.config.user_agent,
            )

        # ScreenScraper
        if self.config.screenscraper.enabled:
            from retro_metadata.providers.screenscraper import ScreenScraperProvider

            self._providers["screenscraper"] = ScreenScraperProvider(
                self.config.screenscraper,
                self._cache,
                self.config.user_agent,
                region_priority=self.config.region_priority,
            )

        # RetroAchievements
        if self.config.retroachievements.enabled:
            from retro_metadata.providers.retroachievements import RetroAchievementsProvider

            self._providers["retroachievements"] = RetroAchievementsProvider(
                self.config.retroachievements,
                self._cache,
                self.config.user_agent,
            )

        # SteamGridDB
        if self.config.steamgriddb.enabled:
            from retro_metadata.providers.steamgriddb import SteamGridDBProvider

            self._providers["steamgriddb"] = SteamGridDBProvider(
                self.config.steamgriddb,
                self._cache,
                self.config.user_agent,
            )

        # HowLongToBeat
        if self.config.hltb.enabled:
            from retro_metadata.providers.hltb import HLTBProvider

            self._providers["hltb"] = HLTBProvider(
                self.config.hltb,
                self._cache,
                self.config.user_agent,
            )

        # TheGamesDB
        if self.config.thegamesdb.enabled:
            from retro_metadata.providers.thegamesdb import TheGamesDBProvider

            self._providers["thegamesdb"] = TheGamesDBProvider(
                self.config.thegamesdb,
                self._cache,
                self.config.user_agent,
            )

        # Hasheous
        if self.config.hasheous.enabled:
            from retro_metadata.providers.hasheous import HasheousProvider

            self._providers["hasheous"] = HasheousProvider(
                self.config.hasheous,
                self._cache,
                self.config.user_agent,
            )

        # Flashpoint
        if self.config.flashpoint.enabled:
            from retro_metadata.providers.flashpoint import FlashpointProvider

            self._providers["flashpoint"] = FlashpointProvider(
                self.config.flashpoint,
                self._cache,
                self.config.user_agent,
            )

        # Playmatch
        if self.config.playmatch.enabled:
            from retro_metadata.providers.playmatch import PlaymatchProvider

            self._providers["playmatch"] = PlaymatchProvider(
                self.config.playmatch,
                self._cache,
                self.config.user_agent,
            )

        # LaunchBox (local metadata)
        if self.config.launchbox.enabled:
            from retro_metadata.providers.launchbox import LaunchBoxProvider

            self._providers["launchbox"] = LaunchBoxProvider(
                self.config.launchbox,
                self._cache,
                metadata_path=self.config.launchbox.options.get("metadata_path"),
            )

        # Gamelist (local gamelist.xml parser)
        if self.config.gamelist.enabled:
            from retro_metadata.providers.gamelist import GamelistProvider

            self._providers["gamelist"] = GamelistProvider(
                self.config.gamelist,
                self._cache,
                roms_path=self.config.gamelist.options.get("roms_path"),
            )

    def get_provider(self, name: str) -> MetadataProvider:
        """Get a specific provider by name.

        Args:
            name: Provider name (e.g., "igdb", "mobygames")

        Returns:
            The provider instance

        Raises:
            ProviderNotFoundError: If provider is not found or not enabled
        """
        provider = self._providers.get(name)
        if provider is None:
            raise ProviderNotFoundError(name)
        return provider

    def list_providers(self) -> list[str]:
        """Get list of enabled provider names.

        Returns:
            List of provider names
        """
        return list(self._providers.keys())

    def _get_platform_id(self, provider: str, platform: str | UniversalPlatformSlug) -> int | None:
        """Get provider-specific platform ID from universal slug.

        Args:
            provider: Provider name
            platform: Platform slug or UniversalPlatformSlug

        Returns:
            Provider-specific platform ID or None
        """
        if provider == "igdb":
            return get_igdb_platform_id(platform)
        elif provider == "mobygames":
            return get_mobygames_platform_id(platform)
        elif provider == "screenscraper":
            return get_screenscraper_platform_id(platform)
        elif provider == "retroachievements":
            return get_retroachievements_platform_id(platform)
        # Other providers don't use platform IDs or have their own mapping
        return None

    async def search(
        self,
        query: str,
        platform: str | UniversalPlatformSlug | None = None,
        providers: list[str] | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search for games across enabled providers.

        Args:
            query: Search query string
            platform: Platform slug to filter by
            providers: List of provider names to search (all enabled if None)
            limit: Maximum results per provider

        Returns:
            List of search results from all queried providers
        """
        await self._initialize()

        if providers is None:
            providers = self.list_providers()

        logger.debug(
            "Search: query='%s', platform=%s, providers=%s, limit=%d",
            query,
            platform,
            providers,
            limit,
        )

        all_results: list[SearchResult] = []

        for provider_name in providers:
            if provider_name not in self._providers:
                logger.debug(
                    "Provider '%s' not available (not enabled or not configured)",
                    provider_name,
                )
                continue

            provider = self._providers[provider_name]
            platform_id = self._get_platform_id(provider_name, platform) if platform else None

            logger.debug(
                "Searching %s: query='%s', platform_id=%s",
                provider_name,
                query,
                platform_id,
            )

            try:
                results = await provider.search(query, platform_id, limit)
                logger.debug(
                    "Search %s returned %d results",
                    provider_name,
                    len(results),
                )
                all_results.extend(results)
            except Exception as e:
                logger.debug("Search %s failed: %s: %s", provider_name, type(e).__name__, e)
                pass

        return all_results

    async def search_all(
        self,
        query: str,
        platform: str | UniversalPlatformSlug | None = None,
        limit: int = 10,
    ) -> AsyncIterator[SearchResult]:
        """Search for games across all providers, yielding results as they arrive.

        Args:
            query: Search query string
            platform: Platform slug to filter by
            limit: Maximum results per provider

        Yields:
            SearchResult objects as they are retrieved from each provider
        """
        await self._initialize()

        for provider_name, provider in self._providers.items():
            platform_id = self._get_platform_id(provider_name, platform) if platform else None

            try:
                results = await provider.search(query, platform_id, limit)
                for result in results:
                    yield result
            except Exception:
                # Log error but continue with other providers
                pass

    async def identify(
        self,
        filename: str,
        platform: str | UniversalPlatformSlug,
        providers: list[str] | None = None,
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Searches providers in priority order until a match is found.

        Args:
            filename: ROM filename (e.g., "Super Mario World (USA).sfc")
            platform: Platform slug
            providers: List of provider names to try (priority order if None)

        Returns:
            GameResult if a match is found, None otherwise
        """
        await self._initialize()

        if providers is None:
            providers = self.config.get_enabled_providers()

        logger.debug(
            "Identify: filename='%s', platform=%s, providers=%s",
            filename,
            platform,
            providers,
        )

        for provider_name in providers:
            if provider_name not in self._providers:
                logger.debug(
                    "Provider '%s' not available (not enabled or not configured)",
                    provider_name,
                )
                continue

            provider = self._providers[provider_name]
            platform_id = self._get_platform_id(provider_name, platform)

            if platform_id is None:
                logger.debug(
                    "Skipping %s: no platform mapping for '%s'",
                    provider_name,
                    platform,
                )
                continue

            logger.debug(
                "Trying %s: filename='%s', platform_id=%s",
                provider_name,
                filename,
                platform_id,
            )

            try:
                result = await provider.identify(filename, platform_id)
                if result:
                    logger.debug(
                        "Identified by %s: '%s' (id=%s)",
                        provider_name,
                        result.name,
                        result.provider_id,
                    )
                    return result
                else:
                    logger.debug("No match from %s", provider_name)
            except Exception as e:
                logger.debug("Identify %s failed: %s: %s", provider_name, type(e).__name__, e)
                pass

        logger.debug("No identification match found for '%s'", filename)
        return None

    async def get_by_id(
        self,
        provider: str,
        game_id: int,
    ) -> GameResult | None:
        """Get game details by provider-specific ID.

        Args:
            provider: Provider name (e.g., "igdb", "mobygames")
            game_id: Provider-specific game ID

        Returns:
            GameResult with full details, or None if not found

        Raises:
            ProviderNotFoundError: If provider is not found or not enabled
        """
        await self._initialize()

        logger.debug("Get by ID: provider=%s, game_id=%s", provider, game_id)

        provider_instance = self.get_provider(provider)
        result = await provider_instance.get_by_id(game_id)

        if result:
            logger.debug(
                "Got game from %s: '%s' (id=%s)",
                provider,
                result.name,
                result.provider_id,
            )
        else:
            logger.debug("No game found for %s id=%s", provider, game_id)

        return result

    async def identify_by_hash(
        self,
        platform: str | UniversalPlatformSlug,
        md5: str | None = None,
        sha1: str | None = None,
        crc: str | None = None,
        file_size: int | None = None,
        filename: str | None = None,
        providers: list[str] | None = None,
    ) -> GameResult | None:
        """Identify a game by ROM hash.

        Searches hash-capable providers until a match is found.
        Providers that support hash lookup: screenscraper, retroachievements,
        playmatch, hasheous.

        Args:
            platform: Platform slug
            md5: MD5 hash of the ROM
            sha1: SHA1 hash of the ROM
            crc: CRC32 hash of the ROM
            file_size: Size of the ROM file in bytes
            filename: ROM filename (used by some providers)
            providers: List of provider names to try (hash-capable only if None)

        Returns:
            GameResult if a match is found, None otherwise
        """
        await self._initialize()

        # Hash-capable providers in priority order
        hash_providers = ["screenscraper", "retroachievements", "playmatch", "hasheous"]

        if providers is None:
            # Filter to only hash-capable providers that are enabled
            providers = [p for p in hash_providers if p in self._providers]
        else:
            # Filter requested providers to only hash-capable ones
            providers = [p for p in providers if p in hash_providers and p in self._providers]

        if not providers:
            logger.debug("No hash-capable providers available")
            return None

        logger.debug(
            "Identify by hash: platform=%s, md5=%s, sha1=%s, crc=%s, providers=%s",
            platform,
            md5[:8] + "..." if md5 else None,
            sha1[:8] + "..." if sha1 else None,
            crc,
            providers,
        )

        for provider_name in providers:
            if provider_name not in self._providers:
                logger.debug(
                    "Provider '%s' not available (not enabled or not configured)",
                    provider_name,
                )
                continue

            provider = self._providers[provider_name]
            platform_id = self._get_platform_id(provider_name, platform)

            # Skip if no platform mapping (except for hasheous which doesn't need it)
            if platform_id is None and provider_name != "hasheous":
                logger.debug(
                    "Skipping %s: no platform mapping for '%s'",
                    provider_name,
                    platform,
                )
                continue

            logger.debug(
                "Trying hash lookup with %s: platform_id=%s",
                provider_name,
                platform_id,
            )

            try:
                result = None

                if provider_name == "screenscraper":
                    result = await provider.lookup_by_hash(
                        platform_id=platform_id,
                        md5=md5,
                        sha1=sha1,
                        crc=crc,
                        rom_size=file_size,
                    )
                elif provider_name == "retroachievements":
                    if md5:
                        result = await provider.lookup_by_hash(
                            platform_id=platform_id,
                            md5=md5,
                        )
                elif provider_name == "playmatch":
                    if filename and file_size:
                        lookup = await provider.lookup_by_hash(
                            filename=filename,
                            file_size=file_size,
                            md5=md5,
                            sha1=sha1,
                        )
                        # Playmatch returns IGDB IDs - fetch full details
                        if lookup and lookup.get("igdb_id"):
                            igdb_id = lookup["igdb_id"]
                            if "igdb" in self._providers:
                                result = await self._providers["igdb"].get_by_id(igdb_id)
                elif provider_name == "hasheous":
                    result = await provider.lookup_by_hash(
                        md5=md5,
                        sha1=sha1,
                        crc=crc,
                    )

                if result:
                    logger.debug(
                        "Hash match found by %s: '%s' (id=%s)",
                        provider_name,
                        result.name,
                        result.provider_id,
                    )
                    return result
                else:
                    logger.debug("No hash match from %s", provider_name)

            except Exception as e:
                logger.debug(
                    "Hash lookup %s failed: %s: %s",
                    provider_name,
                    type(e).__name__,
                    e,
                )
                continue

        logger.debug("No hash match found")
        return None

    async def identify_smart(
        self,
        filename: str,
        platform: str | UniversalPlatformSlug,
        md5: str | None = None,
        sha1: str | None = None,
        crc: str | None = None,
        file_size: int | None = None,
        providers: list[str] | None = None,
        require_unique: bool = True,
    ) -> GameResult | None:
        """Smart identification using a heuristic matching order.

        Matching order (most to least confident):
        1. Match by hash AND filename - hash match where name also matches
        2. Match by hash - any hash match
        3. Match by filename - fuzzy filename matching

        Args:
            filename: ROM filename
            platform: Platform slug
            md5: MD5 hash of the ROM
            sha1: SHA1 hash of the ROM
            crc: CRC32 hash of the ROM
            file_size: Size of the ROM file in bytes
            providers: List of provider names to try
            require_unique: If True, only accept matches when there's a single
                            unique result. If False, accept first/best match.

        Returns:
            GameResult if a match is found, None otherwise
        """
        await self._initialize()

        logger.debug(
            "Smart identify: filename='%s', platform=%s, require_unique=%s",
            filename,
            platform,
            require_unique,
        )

        # Clean filename for comparison
        clean_name = self._clean_filename_for_match(filename)

        # Step 1 & 2: Try hash-based identification if hashes provided
        if md5 or sha1 or crc:
            hash_result = await self.identify_by_hash(
                platform=platform,
                md5=md5,
                sha1=sha1,
                crc=crc,
                file_size=file_size,
                filename=filename,
                providers=providers,
            )

            if hash_result:
                # Check if filename also matches (Step 1: hash + filename)
                result_clean_name = self._clean_filename_for_match(hash_result.name)
                from retro_metadata.core.matching import jaro_winkler_similarity

                similarity = jaro_winkler_similarity(clean_name, result_clean_name)
                if similarity >= 0.6:
                    logger.debug(
                        "Hash + filename match: '%s' ~ '%s' (similarity=%.2f)",
                        clean_name,
                        result_clean_name,
                        similarity,
                    )
                    hash_result.match_type = "hash+filename"
                    return hash_result
                else:
                    # Step 2: Hash match only (filename doesn't match well)
                    logger.debug(
                        "Hash match only (filename mismatch): '%s' vs '%s' (similarity=%.2f)",
                        clean_name,
                        result_clean_name,
                        similarity,
                    )
                    hash_result.match_type = "hash"
                    return hash_result

        # Step 3: Fall back to filename-based identification
        logger.debug("Trying filename-based identification")

        if require_unique:
            # Search and check for unique result
            search_term = self._clean_filename_for_match(filename)
            results = await self.search(
                query=search_term,
                platform=platform,
                providers=providers,
                limit=5,
            )

            if not results:
                logger.debug("No search results for filename")
                return None

            if len(results) == 1:
                # Single unique result - fetch full details
                result = results[0]
                logger.debug(
                    "Unique filename match: '%s' (provider=%s, id=%s)",
                    result.name,
                    result.provider,
                    result.provider_id,
                )
                game = await self.get_by_id(result.provider, result.provider_id)
                if game:
                    game.match_type = "filename_unique"
                return game
            else:
                # Multiple results - check if first is significantly better
                from retro_metadata.core.matching import jaro_winkler_similarity

                first_sim = jaro_winkler_similarity(search_term, results[0].name)
                second_sim = jaro_winkler_similarity(search_term, results[1].name)

                # Accept if first result is much better than second
                if first_sim >= 0.8 and (first_sim - second_sim) >= 0.2:
                    logger.debug(
                        "Best filename match: '%s' (similarity=%.2f, gap=%.2f)",
                        results[0].name,
                        first_sim,
                        first_sim - second_sim,
                    )
                    game = await self.get_by_id(results[0].provider, results[0].provider_id)
                    if game:
                        game.match_type = "filename_best"
                    return game

                logger.debug(
                    "Multiple ambiguous results (%d), require_unique=True - rejecting",
                    len(results),
                )
                return None
        else:
            # Just use standard identify (takes first good match)
            result = await self.identify(
                filename=filename,
                platform=platform,
                providers=providers,
            )
            if result:
                result.match_type = "filename"
            return result

    def _clean_filename_for_match(self, filename: str) -> str:
        """Clean a filename for matching comparison."""
        import re

        # Remove extension
        name = re.sub(r"\.[^.]+$", "", filename)
        # Remove tags in parentheses/brackets
        name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name)
        # Normalize whitespace
        name = " ".join(name.split())
        return name.strip().lower()

    async def heartbeat(self) -> dict[str, bool]:
        """Check connectivity to all enabled providers.

        Returns:
            Dictionary mapping provider names to their connectivity status
        """
        await self._initialize()

        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.heartbeat()
            except Exception:
                results[name] = False

        return results

    async def close(self) -> None:
        """Close all provider connections and clean up resources."""
        for provider in self._providers.values():
            with contextlib.suppress(Exception):
                await provider.close()

        if self._cache is not None:
            with contextlib.suppress(Exception):
                await self._cache.close()

        self._providers.clear()
        self._initialized = False
