"""Hasheous metadata provider implementation.

Hasheous is a service that matches ROM hashes to game metadata.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any, Final

import httpx

from retro_metadata.core.exceptions import (
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

logger = logging.getLogger(__name__)

# Regex to detect Hasheous ID tags in filenames like (hasheous-xxxxx)
HASHEOUS_TAG_REGEX: Final = re.compile(r"\(hasheous-([a-f0-9-]+)\)", re.IGNORECASE)

# Hasheous API keys for client authentication
HASHEOUS_API_KEY_PRODUCTION: Final = "JNoFBA-jEh4HbxuxEHM6MVzydKoAXs9eCcp2dvcg5LRCnpp312voiWmjuaIssSzS"
HASHEOUS_API_KEY_DEV: Final = "UUvh9ef_CddMM4xXO1iqxl9FqEt764v33LU-UiGFc0P34odXjMP9M6MTeE4JZRxZ"

# Hasheous API URLs
HASHEOUS_PRODUCTION_URL: Final = "https://hasheous.org/api/v1"
HASHEOUS_BETA_URL: Final = "https://beta.hasheous.org/api/v1"


class HasheousProvider(MetadataProvider):
    """Hasheous hash-based metadata provider.

    Matches ROM hashes (MD5, SHA1, CRC) to game metadata.
    Requires an X-Client-API-Key header for authentication.

    Example:
        config = ProviderConfig(enabled=True)
        provider = HasheousProvider(config)
        result = await provider.lookup_by_hash(md5="abc123...")
    """

    name = "hasheous"

    def __init__(
        self,
        config: ProviderConfig,
        cache: CacheBackend | None = None,
        user_agent: str = "retro-metadata/1.0",
        dev_mode: bool = False,
    ) -> None:
        super().__init__(config, cache)
        self._dev_mode = dev_mode
        self._base_url = HASHEOUS_BETA_URL if dev_mode else HASHEOUS_PRODUCTION_URL
        self._api_key = HASHEOUS_API_KEY_DEV if dev_mode else HASHEOUS_API_KEY_PRODUCTION
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
                    "Content-Type": "application/json-patch+json",
                    "X-Client-API-Key": self._api_key,
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
        return_all_sources: bool = True,
    ) -> dict[str, Any] | None:
        """Look up a game by ROM hash.

        Args:
            md5: MD5 hash of the ROM
            sha1: SHA1 hash of the ROM
            crc: CRC32 hash of the ROM
            return_all_sources: Whether to return all metadata sources

        Returns:
            Raw Hasheous response dict if found, None otherwise.
            Use get_igdb_game() or get_ra_game() to fetch additional metadata.
        """
        if not self.is_enabled:
            return None

        if not (md5 or sha1 or crc):
            return None

        # Build request data with Hasheous's expected field names
        hashes: dict[str, Any] = {}
        if md5:
            hashes["mD5"] = md5
        if sha1:
            hashes["shA1"] = sha1
        if crc:
            hashes["crc"] = crc

        # Add query params to match romm's implementation
        params: dict[str, str] = {
            "returnAllSources": "true" if return_all_sources else "false",
            "returnFields": "Signatures, Metadata, Attributes",
        }

        result = await self._request_with_params(
            "/Lookup/ByHash",
            params=params,
            method="POST",
            json_data=hashes,
        )

        if not result or not isinstance(result, dict):
            return None

        return result

    async def _request_with_params(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        """Make an API request to Hasheous with both query params and body."""
        client = await self._get_client()

        logger.debug("Hasheous API: %s %s%s", method, self._base_url, endpoint)
        if params:
            logger.debug("Hasheous API params: %s", params)
        if json_data:
            logger.debug("Hasheous API data: %s", json_data)

        try:
            if method == "POST":
                response = await client.post(endpoint, params=params, json=json_data)
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

    async def get_igdb_game(self, hasheous_result: dict[str, Any]) -> dict[str, Any] | None:
        """Get IGDB game data through Hasheous proxy.

        Hasheous can provide IGDB game data for matched ROMs without requiring
        a separate IGDB API key.

        Args:
            hasheous_result: Result from lookup_by_hash containing IGDB reference

        Returns:
            IGDB game data dict, or None if not available
        """
        if not self.is_enabled:
            return None

        # Check for IGDB ID in the Hasheous result
        igdb_id = None

        # Look in metadata list (romm's format)
        metadata_list = hasheous_result.get("metadata", [])
        for meta in metadata_list:
            if meta.get("source") == "IGDB":
                try:
                    igdb_id = int(meta.get("immutableId"))
                except (ValueError, TypeError):
                    # Hasheous may return slugs instead of IDs
                    logger.debug(f"Found IGDB slug instead of ID: {meta.get('immutableId')}")
                break

        # Also check direct igdb_id field
        if not igdb_id:
            igdb_id = hasheous_result.get("igdb_id") or hasheous_result.get("igdbId")

        if not igdb_id:
            return None

        # Fetch IGDB data through Hasheous proxy (matches romm's endpoint)
        result = await self._request(
            "/MetadataProxy/IGDB/Game",
            params={
                "Id": igdb_id,
                "expandColumns": "age_ratings, alternative_names, collections, cover, dlcs, expanded_games, franchise, franchises, game_modes, genres, involved_companies, platforms, ports, remakes, screenshots, similar_games, videos",
            },
        )

        if not result or not isinstance(result, dict):
            return None

        return result

    async def get_ra_game(self, hasheous_result: dict[str, Any]) -> dict[str, Any] | None:
        """Get RetroAchievements game data through Hasheous proxy.

        Hasheous can provide RetroAchievements game data for matched ROMs
        without requiring a separate RA API key.

        Args:
            hasheous_result: Result from lookup_by_hash containing RA reference

        Returns:
            RetroAchievements game data dict, or None if not available
        """
        if not self.is_enabled:
            return None

        # Check for RetroAchievements ID in the Hasheous result
        ra_id = None

        # Look in metadata list (romm's format)
        metadata_list = hasheous_result.get("metadata", [])
        for meta in metadata_list:
            if meta.get("source") == "RetroAchievements":
                ra_id = meta.get("immutableId")
                break

        # Also check direct ra_id field
        if not ra_id:
            ra_id = hasheous_result.get("ra_id") or hasheous_result.get("retroAchievementsId")

        if not ra_id:
            return None

        # Fetch RA data through Hasheous proxy (matches romm's endpoint)
        result = await self._request(
            "/MetadataProxy/RA/Game",
            params={"Id": ra_id},
        )

        if not result or not isinstance(result, dict):
            return None

        return result

    def get_signature_matches(self, hasheous_result: dict[str, Any]) -> dict[str, bool]:
        """Extract signature matching flags from Hasheous lookup result.

        Hasheous can match ROMs against multiple signature databases.
        This method extracts which databases matched.

        Args:
            hasheous_result: Result from lookup_by_hash

        Returns:
            Dictionary of signature source to match status:
            {
                "tosec_match": True/False,
                "nointro_match": True/False,
                "redump_match": True/False,
                "mame_arcade_match": True/False,
                "mame_mess_match": True/False,
                "whdload_match": True/False,
                "ra_match": True/False,
                "fbneo_match": True/False,
                "puredos_match": True/False,
            }
        """
        # Get signature keys from the dict (romm's format)
        signatures = hasheous_result.get("signatures", {})
        signature_keys = set(signatures.keys()) if isinstance(signatures, dict) else set()

        return {
            "tosec_match": "TOSEC" in signature_keys,
            "nointro_match": "NoIntros" in signature_keys,
            "redump_match": "Redump" in signature_keys,
            "mame_arcade_match": "MAMEArcade" in signature_keys,
            "mame_mess_match": "MAMEMess" in signature_keys,
            "whdload_match": "WHDLoad" in signature_keys,
            "ra_match": "RetroAchievements" in signature_keys,
            "fbneo_match": "FBNeo" in signature_keys,
            "puredos_match": "PureDOS" in signature_keys,
        }

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

    def get_platform(self, slug: str) -> Platform | None:
        """Get platform information for a slug.

        Args:
            slug: Universal platform slug

        Returns:
            Platform with Hasheous platform info including cross-provider IDs,
            or None if not supported
        """
        try:
            ups = UPS(slug)
        except ValueError:
            return None

        if ups not in HASHEOUS_PLATFORM_MAP:
            return None

        platform_info = HASHEOUS_PLATFORM_MAP[ups]
        provider_ids: dict[str, Any] = {"hasheous": platform_info["name"]}

        # Add cross-provider IDs if available
        if platform_info.get("igdb_id"):
            provider_ids["igdb"] = platform_info["igdb_id"]
        if platform_info.get("tgdb_id"):
            provider_ids["thegamesdb"] = platform_info["tgdb_id"]
        if platform_info.get("ra_id"):
            provider_ids["retroachievements"] = platform_info["ra_id"]

        return Platform(
            slug=slug,
            name=platform_info["name"],
            provider_ids=provider_ids,
        )

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()


# Hasheous Platform mapping from universal slugs to Hasheous platform info
# Includes cross-provider IDs for IGDB, TheGamesDB (TGDB), and RetroAchievements (RA)
# Also includes signature matching support info (TOSEC, NoIntro, Redump, etc.)
HASHEOUS_PLATFORM_MAP: dict[UPS, dict[str, Any]] = {
    # 3DO
    UPS._3DO: {"name": "3DO Interactive Multiplayer", "igdb_id": 50, "tgdb_id": 25, "ra_id": 43, "nointro": True, "redump": True},
    # Amstrad
    UPS.ACPC: {"name": "Amstrad CPC", "igdb_id": 25, "tgdb_id": 4914, "ra_id": 37, "tosec": True, "nointro": True},
    UPS.AMSTRAD_GX4000: {"name": "Amstrad GX4000", "igdb_id": 158, "tgdb_id": 4999, "nointro": True},
    # Android / iOS / Mobile
    UPS.ANDROID: {"name": "Android", "igdb_id": 34, "tgdb_id": 4916},
    UPS.IOS: {"name": "iOS", "igdb_id": 39},
    # Apple
    UPS.APPLEII: {"name": "Apple II", "igdb_id": 75, "tgdb_id": 4942, "ra_id": 38, "tosec": True, "nointro": True},
    UPS.APPLE_IIGS: {"name": "Apple IIGS", "igdb_id": 115, "tosec": True},
    UPS.MAC: {"name": "Macintosh", "igdb_id": 14, "tgdb_id": 37},
    # Arcade
    UPS.ARCADE: {"name": "Arcade", "igdb_id": 52, "tgdb_id": 23, "ra_id": 27, "fbneo": True, "mame": True},
    UPS.CPS1: {"name": "Capcom Play System", "igdb_id": 52, "fbneo": True},
    UPS.CPS2: {"name": "Capcom Play System 2", "igdb_id": 52, "fbneo": True},
    UPS.CPS3: {"name": "Capcom Play System 3", "igdb_id": 52, "fbneo": True},
    UPS.NEOGEOAES: {"name": "Neo Geo AES", "igdb_id": 80, "tgdb_id": 24, "ra_id": 27, "fbneo": True},
    UPS.NEOGEOMVS: {"name": "Neo Geo MVS", "igdb_id": 79, "fbneo": True},
    # Atari
    UPS.ATARI2600: {"name": "Atari 2600", "igdb_id": 59, "tgdb_id": 22, "ra_id": 25, "nointro": True, "tosec": True},
    UPS.ATARI5200: {"name": "Atari 5200", "igdb_id": 66, "tgdb_id": 26, "ra_id": 50, "nointro": True, "tosec": True},
    UPS.ATARI7800: {"name": "Atari 7800", "igdb_id": 60, "tgdb_id": 27, "ra_id": 51, "nointro": True, "tosec": True},
    UPS.ATARI8BIT: {"name": "Atari 8-bit", "igdb_id": 65, "tgdb_id": 4943, "tosec": True},
    UPS.ATARI800: {"name": "Atari 800", "igdb_id": 65, "tgdb_id": 4943, "tosec": True},
    UPS.ATARI_ST: {"name": "Atari ST", "igdb_id": 63, "tgdb_id": 4937, "ra_id": 36, "tosec": True},
    UPS.ATARI_XEGS: {"name": "Atari XEGS", "igdb_id": 111, "tgdb_id": 30},
    UPS.JAGUAR: {"name": "Atari Jaguar", "igdb_id": 62, "tgdb_id": 28, "ra_id": 17, "nointro": True},
    UPS.ATARI_JAGUAR_CD: {"name": "Atari Jaguar CD", "igdb_id": 171, "tgdb_id": 29, "ra_id": 77, "redump": True},
    UPS.LYNX: {"name": "Atari Lynx", "igdb_id": 61, "tgdb_id": 4924, "ra_id": 13, "nointro": True},
    # Bandai
    UPS.WONDERSWAN: {"name": "WonderSwan", "igdb_id": 57, "tgdb_id": 4925, "ra_id": 53, "nointro": True},
    UPS.WONDERSWAN_COLOR: {"name": "WonderSwan Color", "igdb_id": 123, "tgdb_id": 4926, "ra_id": 53, "nointro": True},
    # BBC
    UPS.BBCMICRO: {"name": "BBC Micro", "igdb_id": 69, "tgdb_id": 5013, "tosec": True},
    # ColecoVision
    UPS.COLECOVISION: {"name": "ColecoVision", "igdb_id": 68, "tgdb_id": 31, "ra_id": 44, "nointro": True, "tosec": True},
    # Commodore
    UPS.AMIGA: {"name": "Commodore Amiga", "igdb_id": 16, "tgdb_id": 4911, "tosec": True, "whdload": True},
    UPS.AMIGA_CD: {"name": "Amiga CD", "igdb_id": 114, "redump": True},
    UPS.AMIGA_CD32: {"name": "Amiga CD32", "igdb_id": 117, "tgdb_id": 4947, "redump": True},
    UPS.C64: {"name": "Commodore 64", "igdb_id": 15, "tgdb_id": 40, "ra_id": 52, "tosec": True, "nointro": True},
    UPS.C128: {"name": "Commodore 128", "igdb_id": 15, "tosec": True},
    UPS.VIC_20: {"name": "Commodore VIC-20", "igdb_id": 71, "tosec": True},
    UPS.COMMODORE_CDTV: {"name": "Commodore CDTV", "igdb_id": 116, "redump": True},
    # DOS / PC
    UPS.DOS: {"name": "DOS", "igdb_id": 13, "tgdb_id": 1, "exodos": True},
    UPS.WIN: {"name": "Windows", "igdb_id": 6},
    UPS.WIN3X: {"name": "Windows 3.x", "igdb_id": 6, "exodos": True},
    UPS.LINUX: {"name": "Linux", "igdb_id": 3},
    # Fairchild
    UPS.FAIRCHILD_CHANNEL_F: {"name": "Fairchild Channel F", "igdb_id": 127, "tgdb_id": 4928, "ra_id": 57, "nointro": True},
    # FM Towns
    UPS.FM_TOWNS: {"name": "FM Towns", "redump": True},
    # Intellivision
    UPS.INTELLIVISION: {"name": "Intellivision", "igdb_id": 67, "tgdb_id": 32, "ra_id": 45, "nointro": True, "tosec": True},
    # Microsoft Xbox
    UPS.XBOX: {"name": "Microsoft Xbox", "igdb_id": 11, "tgdb_id": 14, "redump": True},
    UPS.XBOX360: {"name": "Microsoft Xbox 360", "igdb_id": 12, "tgdb_id": 15, "redump": True},
    UPS.XBOXONE: {"name": "Xbox One", "igdb_id": 49},
    UPS.SERIES_X_S: {"name": "Xbox Series X|S", "igdb_id": 169},
    # MSX
    UPS.MSX: {"name": "MSX", "igdb_id": 27, "tgdb_id": 4929, "ra_id": 29, "nointro": True, "tosec": True},
    UPS.MSX2: {"name": "MSX2", "igdb_id": 53, "nointro": True, "tosec": True},
    UPS.MSX2PLUS: {"name": "MSX2+", "igdb_id": 161},
    UPS.MSX_TURBO: {"name": "MSX turboR"},
    # NEC
    UPS.PC_8800_SERIES: {"name": "NEC PC-8801", "igdb_id": 125, "ra_id": 47, "nointro": True},
    UPS.PC_9800_SERIES: {"name": "NEC PC-9801", "igdb_id": 149, "ra_id": 48, "nointro": True},
    UPS.PC_FX: {"name": "PC-FX", "igdb_id": 274, "tgdb_id": 4930, "ra_id": 49, "redump": True},
    UPS.TG16: {"name": "TurboGrafx-16", "igdb_id": 86, "tgdb_id": 34, "ra_id": 8, "nointro": True},
    UPS.TURBOGRAFX_CD: {"name": "TurboGrafx-CD", "igdb_id": 150, "tgdb_id": 4940, "ra_id": 8, "redump": True},
    UPS.SUPERGRAFX: {"name": "SuperGrafx", "igdb_id": 128, "tgdb_id": 4955, "ra_id": 76, "nointro": True},
    # Neo Geo
    UPS.NEO_GEO_CD: {"name": "Neo Geo CD", "igdb_id": 136, "tgdb_id": 4956, "ra_id": 56, "redump": True},
    UPS.NEO_GEO_POCKET: {"name": "Neo Geo Pocket", "igdb_id": 119, "tgdb_id": 4922, "ra_id": 14, "nointro": True},
    UPS.NEO_GEO_POCKET_COLOR: {"name": "Neo Geo Pocket Color", "igdb_id": 120, "tgdb_id": 4923, "ra_id": 14, "nointro": True},
    # Nintendo Consoles
    UPS.NES: {"name": "Nintendo Entertainment System", "igdb_id": 18, "tgdb_id": 7, "ra_id": 7, "nointro": True, "tosec": True},
    UPS.FAMICOM: {"name": "Famicom", "igdb_id": 99, "ra_id": 7, "nointro": True},
    UPS.FDS: {"name": "Famicom Disk System", "igdb_id": 51, "tgdb_id": 4936, "ra_id": 7, "nointro": True},
    UPS.SNES: {"name": "Super Nintendo Entertainment System", "igdb_id": 19, "tgdb_id": 6, "ra_id": 3, "nointro": True, "tosec": True},
    UPS.SFAM: {"name": "Super Famicom", "igdb_id": 58, "ra_id": 3, "nointro": True},
    UPS.SATELLAVIEW: {"name": "Satellaview", "igdb_id": 58, "nointro": True},
    UPS.SUFAMI_TURBO: {"name": "Sufami Turbo", "nointro": True},
    UPS.N64: {"name": "Nintendo 64", "igdb_id": 4, "tgdb_id": 3, "ra_id": 2, "nointro": True},
    UPS.N64DD: {"name": "Nintendo 64DD", "igdb_id": 416, "nointro": True},
    UPS.NGC: {"name": "Nintendo GameCube", "igdb_id": 21, "tgdb_id": 2, "ra_id": 16, "redump": True, "nkit": True},
    UPS.WII: {"name": "Nintendo Wii", "igdb_id": 5, "tgdb_id": 9, "redump": True, "nkit": True},
    UPS.WIIU: {"name": "Nintendo Wii U", "igdb_id": 41, "tgdb_id": 38, "redump": True},
    UPS.SWITCH: {"name": "Nintendo Switch", "igdb_id": 130, "tgdb_id": 4971},
    # Nintendo Handhelds
    UPS.GB: {"name": "Game Boy", "igdb_id": 33, "tgdb_id": 4, "ra_id": 4, "nointro": True, "tosec": True},
    UPS.GBC: {"name": "Game Boy Color", "igdb_id": 22, "tgdb_id": 41, "ra_id": 6, "nointro": True, "tosec": True},
    UPS.GBA: {"name": "Game Boy Advance", "igdb_id": 24, "tgdb_id": 5, "ra_id": 5, "nointro": True, "tosec": True},
    UPS.NDS: {"name": "Nintendo DS", "igdb_id": 20, "tgdb_id": 8, "ra_id": 18, "nointro": True},
    UPS.NINTENDO_DSI: {"name": "Nintendo DSi", "igdb_id": 20, "nointro": True},
    UPS.N3DS: {"name": "Nintendo 3DS", "igdb_id": 37, "tgdb_id": 4912, "nointro": True},
    UPS.NEW_NINTENDON3DS: {"name": "New Nintendo 3DS", "igdb_id": 137, "nointro": True},
    UPS.VIRTUALBOY: {"name": "Virtual Boy", "igdb_id": 87, "tgdb_id": 4918, "ra_id": 28, "nointro": True},
    UPS.POKEMON_MINI: {"name": "Pokémon mini", "igdb_id": 207, "ra_id": 24, "nointro": True},
    # Odyssey
    UPS.ODYSSEY_2: {"name": "Magnavox Odyssey 2", "igdb_id": 133, "tgdb_id": 4927, "ra_id": 23, "nointro": True},
    # Philips
    UPS.PHILIPS_CD_I: {"name": "Philips CD-i", "redump": True},
    # Sega
    UPS.SG1000: {"name": "Sega SG-1000", "igdb_id": 84, "tgdb_id": 4949, "ra_id": 33, "nointro": True},
    UPS.SMS: {"name": "Sega Master System", "igdb_id": 64, "tgdb_id": 35, "ra_id": 11, "nointro": True, "tosec": True},
    UPS.GENESIS: {"name": "Sega Genesis", "igdb_id": 29, "tgdb_id": 18, "ra_id": 1, "nointro": True, "tosec": True},
    UPS.SEGACD: {"name": "Sega CD", "igdb_id": 78, "tgdb_id": 21, "ra_id": 9, "redump": True},
    UPS.SEGACD32: {"name": "Sega CD 32X", "igdb_id": 78, "redump": True},
    UPS.SEGA32: {"name": "Sega 32X", "igdb_id": 30, "tgdb_id": 33, "ra_id": 10, "nointro": True},
    UPS.SATURN: {"name": "Sega Saturn", "igdb_id": 32, "tgdb_id": 17, "ra_id": 39, "redump": True, "tosec": True},
    UPS.DC: {"name": "Sega Dreamcast", "igdb_id": 23, "tgdb_id": 16, "ra_id": 40, "redump": True, "tosec": True},
    UPS.GAMEGEAR: {"name": "Sega Game Gear", "igdb_id": 35, "tgdb_id": 20, "ra_id": 15, "nointro": True, "tosec": True},
    UPS.SEGA_PICO: {"name": "Sega Pico", "igdb_id": 339, "nointro": True},
    # Sharp
    UPS.SHARP_X68000: {"name": "Sharp X68000", "igdb_id": 112, "ra_id": 52, "tosec": True},
    UPS.X1: {"name": "Sharp X1", "igdb_id": 77, "nointro": True},
    # Sinclair
    UPS.ZXS: {"name": "ZX Spectrum", "igdb_id": 26, "tgdb_id": 4913, "ra_id": 34, "tosec": True},
    UPS.ZX81: {"name": "ZX81", "igdb_id": 26, "tosec": True},
    # Sony PlayStation
    UPS.PSX: {"name": "Sony PlayStation", "igdb_id": 7, "tgdb_id": 10, "ra_id": 12, "redump": True, "tosec": True},
    UPS.PS2: {"name": "Sony PlayStation 2", "igdb_id": 8, "tgdb_id": 11, "ra_id": 21, "redump": True},
    UPS.PS3: {"name": "Sony PlayStation 3", "igdb_id": 9, "tgdb_id": 12, "redump": True},
    UPS.PS4: {"name": "Sony PlayStation 4", "igdb_id": 48},
    UPS.PS5: {"name": "Sony PlayStation 5", "igdb_id": 167},
    UPS.PSP: {"name": "Sony PSP", "igdb_id": 38, "tgdb_id": 13, "ra_id": 41, "redump": True, "nointro": True},
    UPS.PSVITA: {"name": "Sony PlayStation Vita", "igdb_id": 46, "tgdb_id": 39, "nointro": True},
    UPS.POCKETSTATION: {"name": "PocketStation", "igdb_id": 76},
    # Vectrex
    UPS.VECTREX: {"name": "Vectrex", "igdb_id": 70, "tgdb_id": 4939, "ra_id": 46, "nointro": True},
    # Other Consoles
    UPS.ARCADIA_2001: {"name": "Arcadia 2001", "igdb_id": None, "ra_id": 73, "nointro": True},
    UPS.ASTROCADE: {"name": "Bally Astrocade", "igdb_id": None, "tgdb_id": 4968, "nointro": True},
    UPS.CASIO_LOOPY: {"name": "Casio Loopy", "tgdb_id": 4991, "nointro": True},
    UPS.CASIO_PV_1000: {"name": "Casio PV-1000", "tgdb_id": 4964, "nointro": True},
    UPS.EPOCH_CASSETTE_VISION: {"name": "Epoch Cassette Vision", "nointro": True},
    UPS.EPOCH_SUPER_CASSETTE_VISION: {"name": "Epoch Super Cassette Vision", "nointro": True},
    UPS.INTERTON_VC_4000: {"name": "Interton VC 4000", "ra_id": 75, "nointro": True},
    UPS.VC_4000: {"name": "VC 4000", "nointro": True},
    UPS.ADVENTURE_VISION: {"name": "Entex Adventure Vision", "ra_id": 78, "nointro": True},
    UPS.CREATIVISION: {"name": "VTech CreatiVision", "nointro": True},
    # Other Handhelds
    UPS.GAMATE: {"name": "Gamate", "igdb_id": 340, "nointro": True},
    UPS.GAME_DOT_COM: {"name": "Game.com", "igdb_id": 122, "nointro": True},
    UPS.GIZMONDO: {"name": "Gizmondo", "igdb_id": 121, "nointro": True},
    UPS.SUPERVISION: {"name": "Watara Supervision", "igdb_id": 343, "ra_id": 63, "nointro": True},
    UPS.MEGA_DUCK_SLASH_COUGAR_BOY: {"name": "Mega Duck", "ra_id": 69, "nointro": True},
    UPS.NGAGE: {"name": "N-Gage", "igdb_id": 42},
    # Modern / Cloud
    UPS.STADIA: {"name": "Google Stadia", "igdb_id": 170},
    UPS.AMAZON_FIRE_TV: {"name": "Amazon Fire TV", "igdb_id": 132},
    UPS.OUYA: {"name": "Ouya", "igdb_id": 72},
    UPS.PLAYDATE: {"name": "Playdate", "igdb_id": 308},
    UPS.EVERCADE: {"name": "Evercade"},
    # Homebrew / Special
    UPS.ARDUBOY: {"name": "Arduboy", "ra_id": 71, "nointro": True},
    UPS.UZEBOX: {"name": "Uzebox", "ra_id": 80, "nointro": True},
    UPS.WASM_4: {"name": "WASM-4", "ra_id": 72, "nointro": True},
}
