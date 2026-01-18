"""IGDB metadata provider implementation."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any, Final

import aiohttp
import yarl
from aiohttp.client import ClientTimeout

logger = logging.getLogger(__name__)

from retro_metadata.core.exceptions import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderRateLimitError,
)
from retro_metadata.platforms.mappings import get_igdb_platform_id
from retro_metadata.platforms.slugs import UniversalPlatformSlug as UPS
from retro_metadata.providers.base import MetadataProvider
from retro_metadata.types.common import (
    AgeRating,
    Artwork,
    GameMetadata,
    GameResult,
    MultiplayerMode,
    Platform,
    RelatedGame,
    SearchResult,
)

# Forward declaration for age rating functions used below
# The actual mappings are defined at module level after the class
from retro_metadata.types.igdb import Game, GameType

if TYPE_CHECKING:
    from retro_metadata.cache.base import CacheBackend
    from retro_metadata.core.config import ProviderConfig

# Regex to detect IGDB ID tags in filenames like (igdb-12345)
IGDB_TAG_REGEX: Final = re.compile(r"\(igdb-(\d+)\)", re.IGNORECASE)

# Fields to fetch for full game details
GAMES_FIELDS: Final = (
    "id",
    "name",
    "slug",
    "summary",
    "total_rating",
    "aggregated_rating",
    "first_release_date",
    "cover.url",
    "screenshots.url",
    "platforms.id",
    "platforms.name",
    "alternative_names.name",
    "genres.name",
    "franchise.name",
    "franchises.name",
    "collections.name",
    "game_modes.name",
    "involved_companies.company.name",
    "expansions.id",
    "expansions.slug",
    "expansions.name",
    "expansions.cover.url",
    "dlcs.id",
    "dlcs.name",
    "dlcs.slug",
    "dlcs.cover.url",
    "remakes.id",
    "remakes.slug",
    "remakes.name",
    "remakes.cover.url",
    "remasters.id",
    "remasters.slug",
    "remasters.name",
    "remasters.cover.url",
    "ports.id",
    "ports.slug",
    "ports.name",
    "ports.cover.url",
    "similar_games.id",
    "similar_games.slug",
    "similar_games.name",
    "similar_games.cover.url",
    "age_ratings.rating_category",
    "videos.video_id",
    "multiplayer_modes.campaigncoop",
    "multiplayer_modes.dropin",
    "multiplayer_modes.lancoop",
    "multiplayer_modes.offlinecoop",
    "multiplayer_modes.offlinecoopmax",
    "multiplayer_modes.offlinemax",
    "multiplayer_modes.onlinecoop",
    "multiplayer_modes.onlinecoopmax",
    "multiplayer_modes.onlinemax",
    "multiplayer_modes.splitscreen",
    "multiplayer_modes.splitscreenonline",
    "multiplayer_modes.platform.id",
    "multiplayer_modes.platform.name",
)

SEARCH_FIELDS: Final = ("game.id", "name")


class IGDBProvider(MetadataProvider):
    """IGDB metadata provider.

    Requires client_id and client_secret credentials from Twitch.

    Example:
        config = ProviderConfig(
            enabled=True,
            credentials={
                "client_id": "your_client_id",
                "client_secret": "your_client_secret",
            }
        )
        provider = IGDBProvider(config)
        results = await provider.search("Super Mario World", platform_id=19)
    """

    name = "igdb"

    def __init__(
        self,
        config: "ProviderConfig",
        cache: "CacheBackend | None" = None,
        user_agent: str = "retro-metadata/1.0",
    ) -> None:
        super().__init__(config, cache)
        self._base_url = yarl.URL("https://api.igdb.com/v4")
        self._twitch_url = "https://id.twitch.tv/oauth2/token"
        self._user_agent = user_agent
        self._session: aiohttp.ClientSession | None = None
        self._oauth_token: str | None = None
        self._pagination_limit = 200

    @property
    def client_id(self) -> str:
        return self.config.get_credential("client_id")

    @property
    def client_secret(self) -> str:
        return self.config.get_credential("client_secret")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _get_oauth_token(self) -> str:
        """Get or refresh the OAuth token from Twitch."""
        # Check cache first
        cached_token = await self._get_cached("oauth_token")
        if cached_token:
            return cached_token

        session = await self._get_session()
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        try:
            async with session.post(self._twitch_url, params=params) as response:
                if response.status == 400:
                    raise ProviderAuthenticationError(
                        self.name, "Invalid client_id or client_secret"
                    )
                response.raise_for_status()
                data = await response.json()

                token = data.get("access_token", "")
                expires_in = data.get("expires_in", 0)

                if token and expires_in > 0:
                    # Cache the token
                    await self._set_cached("oauth_token", token, expires_in - 60)
                    self._oauth_token = token
                    return token

                raise ProviderAuthenticationError(
                    self.name, "Failed to obtain OAuth token"
                )
        except aiohttp.ClientError as e:
            raise ProviderConnectionError(self.name, str(e)) from e

    async def _request(
        self,
        endpoint: str,
        search_term: str | None = None,
        fields: tuple[str, ...] | None = None,
        where: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Make an API request to IGDB."""
        token = await self._get_oauth_token()
        session = await self._get_session()
        url = str(self._base_url.joinpath(endpoint))

        # Build query
        query_parts = []
        if search_term:
            # Use unidecode for ASCII conversion
            try:
                from unidecode import unidecode
                query_parts.append(f'search "{unidecode(search_term)}";')
            except ImportError:
                query_parts.append(f'search "{search_term}";')
        if fields:
            query_parts.append(f"fields {','.join(fields)};")
        if where:
            query_parts.append(f"where {where};")
        if limit is not None:
            query_parts.append(f"limit {limit};")

        body = " ".join(query_parts)

        logger.debug("IGDB API: POST %s", url)
        logger.debug("IGDB API query: %s", body)

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Client-ID": self.client_id,
            "User-Agent": self._user_agent,
        }

        try:
            async with session.post(
                url,
                data=body,
                headers=headers,
                timeout=ClientTimeout(total=self.config.timeout),
            ) as response:
                if response.status == 401:
                    # Token expired, clear cache and retry once
                    logger.debug("IGDB API: 401 Unauthorized, token expired")
                    self._oauth_token = None
                    if self.cache:
                        await self.cache.delete(f"{self.name}:oauth_token")
                    raise ProviderAuthenticationError(self.name, "Token expired")
                elif response.status == 429:
                    logger.debug("IGDB API: 429 Rate limited")
                    raise ProviderRateLimitError(self.name, retry_after=2)
                response.raise_for_status()
                data = await response.json()

                # Log full response body only when debug logging is enabled
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("IGDB API response:\n%s", json.dumps(data, indent=2, ensure_ascii=False))

                return data
        except aiohttp.ClientError as e:
            logger.debug("IGDB API error: %s", e)
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
            platform_id: IGDB platform ID to filter by
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.is_enabled:
            return []

        where = f"platforms=[{platform_id}]" if platform_id else None

        results = await self._request(
            "games",
            search_term=query,
            fields=("id", "name", "slug", "cover.url", "platforms.name", "first_release_date"),
            where=where,
            limit=limit,
        )

        search_results = []
        for game in results:
            cover_url = ""
            if "cover" in game and isinstance(game["cover"], dict):
                cover_url = self.normalize_cover_url(game["cover"].get("url", ""))

            platforms = []
            if "platforms" in game:
                platforms = [p.get("name", "") for p in game["platforms"] if isinstance(p, dict)]

            release_year = None
            if "first_release_date" in game:
                from datetime import datetime
                try:
                    release_year = datetime.fromtimestamp(game["first_release_date"]).year
                except (ValueError, OSError):
                    pass

            search_results.append(SearchResult(
                name=game.get("name", ""),
                provider=self.name,
                provider_id=game["id"],
                slug=game.get("slug", ""),
                cover_url=cover_url.replace("t_thumb", "t_cover_big") if cover_url else "",
                platforms=platforms,
                release_year=release_year,
            ))

        return search_results

    async def get_by_id(self, game_id: int) -> GameResult | None:
        """Get game details by IGDB ID.

        Args:
            game_id: IGDB game ID

        Returns:
            GameResult with full details, or None if not found
        """
        if not self.is_enabled:
            return None

        results = await self._request(
            "games",
            fields=GAMES_FIELDS,
            where=f"id={game_id}",
            limit=1,
        )

        if not results:
            return None

        return self._build_game_result(results[0])

    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Args:
            filename: ROM filename
            platform_id: IGDB platform ID

        Returns:
            GameResult if a match is found, None otherwise
        """
        if not self.is_enabled:
            return None

        # Check for IGDB ID tag in filename
        tagged_id = self.extract_id_from_filename(filename, IGDB_TAG_REGEX)
        if tagged_id:
            result = await self.get_by_id(tagged_id)
            if result:
                return result

        # Clean the filename
        search_term = self._clean_filename(filename)
        search_term = self.normalize_search_term(search_term)

        if not platform_id:
            return None

        # Search with game type filter first
        categories = (
            GameType.MAIN_GAME,
            GameType.EXPANDED_GAME,
            GameType.PORT,
            GameType.REMAKE,
            GameType.REMASTER,
        )
        game_type_filter = f"& category=({','.join(map(str, categories))})"
        where = f"platforms=[{platform_id}] {game_type_filter}"

        results = await self._request(
            "games",
            search_term=search_term,
            fields=GAMES_FIELDS,
            where=where,
            limit=self._pagination_limit,
        )

        if not results:
            # Try without game type filter
            where = f"platforms=[{platform_id}]"
            results = await self._request(
                "games",
                search_term=search_term,
                fields=GAMES_FIELDS,
                where=where,
                limit=self._pagination_limit,
            )

        if not results:
            return None

        # Find best match
        games_by_name = {g.get("name", ""): g for g in results}
        best_match, score = self.find_best_match(search_term, list(games_by_name.keys()))

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
        """Build a GameResult from IGDB game data."""
        # Extract cover URL
        cover_url = ""
        if "cover" in game and isinstance(game["cover"], dict):
            cover_url = self.normalize_cover_url(game["cover"].get("url", ""))
            cover_url = cover_url.replace("t_thumb", "t_1080p")

        # Extract screenshots
        screenshot_urls = []
        if "screenshots" in game:
            for s in game["screenshots"]:
                if isinstance(s, dict) and "url" in s:
                    url = self.normalize_cover_url(s["url"])
                    screenshot_urls.append(url.replace("t_thumb", "t_720p"))

        # Extract metadata
        metadata = self._extract_metadata(game)

        return GameResult(
            name=game.get("name", ""),
            summary=game.get("summary", ""),
            provider=self.name,
            provider_id=game["id"],
            provider_ids={"igdb": game["id"]},
            slug=game.get("slug", ""),
            artwork=Artwork(
                cover_url=cover_url,
                screenshot_urls=screenshot_urls,
            ),
            metadata=metadata,
            raw_response=game,
        )

    def _extract_metadata(self, game: dict[str, Any]) -> GameMetadata:
        """Extract GameMetadata from IGDB game data."""
        # Extract genres
        genres = []
        if "genres" in game:
            genres = [g.get("name", "") for g in game["genres"] if isinstance(g, dict) and g.get("name")]

        # Extract franchises
        franchises = []
        if "franchise" in game and isinstance(game["franchise"], dict):
            franchises.append(game["franchise"].get("name", ""))
        if "franchises" in game:
            franchises.extend([f.get("name", "") for f in game["franchises"] if isinstance(f, dict) and f.get("name")])

        # Extract alternative names
        alt_names = []
        if "alternative_names" in game:
            alt_names = [n.get("name", "") for n in game["alternative_names"] if isinstance(n, dict) and n.get("name")]

        # Extract collections
        collections = []
        if "collections" in game:
            collections = [c.get("name", "") for c in game["collections"] if isinstance(c, dict) and c.get("name")]

        # Extract companies
        companies = []
        if "involved_companies" in game:
            for ic in game["involved_companies"]:
                if isinstance(ic, dict) and "company" in ic:
                    company = ic["company"]
                    if isinstance(company, dict) and "name" in company:
                        companies.append(company["name"])

        # Extract game modes
        game_modes = []
        if "game_modes" in game:
            game_modes = [g.get("name", "") for g in game["game_modes"] if isinstance(g, dict) and g.get("name")]

        # Extract platforms
        platforms = []
        if "platforms" in game:
            for p in game["platforms"]:
                if isinstance(p, dict):
                    platforms.append(Platform(
                        slug="",
                        name=p.get("name", ""),
                        provider_ids={"igdb": p.get("id", 0)},
                    ))

        # Extract related games
        def extract_related(key: str, rel_type: str) -> list[RelatedGame]:
            related = []
            if key in game:
                for r in game[key]:
                    if isinstance(r, dict):
                        cover_url = ""
                        if "cover" in r and isinstance(r["cover"], dict):
                            cover_url = self.normalize_cover_url(r["cover"].get("url", ""))
                            cover_url = cover_url.replace("t_thumb", "t_1080p")
                        related.append(RelatedGame(
                            id=r.get("id", 0),
                            name=r.get("name", ""),
                            slug=r.get("slug", ""),
                            relation_type=rel_type,
                            cover_url=cover_url,
                            provider=self.name,
                        ))
            return related

        # Extract video
        youtube_video_id = None
        if "videos" in game and game["videos"]:
            first_video = game["videos"][0]
            if isinstance(first_video, dict):
                youtube_video_id = first_video.get("video_id")

        # Extract age ratings
        age_ratings = []
        if "age_ratings" in game:
            for ar in game["age_ratings"]:
                if isinstance(ar, dict):
                    category_id = ar.get("category") or ar.get("rating_category", 0)
                    rating_id = ar.get("rating", 0)
                    category_name = IGDB_AGE_RATING_CATEGORIES.get(category_id, "Unknown")
                    rating_name = IGDB_AGE_RATINGS.get(rating_id, str(rating_id))
                    age_ratings.append(AgeRating(rating=rating_name, category=category_name))

        return GameMetadata(
            total_rating=game.get("total_rating"),
            aggregated_rating=game.get("aggregated_rating"),
            first_release_date=game.get("first_release_date"),
            youtube_video_id=youtube_video_id,
            genres=genres,
            franchises=[f for f in franchises if f],
            alternative_names=alt_names,
            collections=collections,
            companies=companies,
            game_modes=game_modes,
            platforms=platforms,
            age_ratings=age_ratings,
            expansions=extract_related("expansions", "expansion"),
            dlcs=extract_related("dlcs", "dlc"),
            remasters=extract_related("remasters", "remaster"),
            remakes=extract_related("remakes", "remake"),
            expanded_games=extract_related("expanded_games", "expanded"),
            ports=extract_related("ports", "port"),
            similar_games=extract_related("similar_games", "similar"),
            raw_data=game,
        )

    def get_platform(self, slug: str) -> Platform | None:
        """Get platform information for a slug.

        Args:
            slug: Universal platform slug

        Returns:
            Platform with IGDB ID, or None if not supported
        """
        try:
            ups = UPS(slug)
        except ValueError:
            return None

        platform_id = get_igdb_platform_id(ups)
        if platform_id is None:
            return None

        # Get platform name from the mapping
        name = IGDB_PLATFORM_NAMES.get(platform_id, slug.replace("-", " ").title())

        return Platform(
            slug=slug,
            name=name,
            provider_ids={"igdb": platform_id},
        )

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()


# IGDB age rating mappings
# Rating category IDs from IGDB API
IGDB_AGE_RATING_CATEGORIES: dict[int, str] = {
    1: "ESRB",
    2: "PEGI",
    3: "CERO",
    4: "USK",
    5: "GRAC",
    6: "CLASS_IND",
    7: "ACB",
}

# Rating value IDs from IGDB API
IGDB_AGE_RATINGS: dict[int, str] = {
    # ESRB
    1: "Three",
    2: "Seven",
    3: "Twelve",
    4: "Sixteen",
    5: "Eighteen",
    6: "RP (Rating Pending)",
    7: "EC (Early Childhood)",
    8: "E (Everyone)",
    9: "E10+ (Everyone 10+)",
    10: "T (Teen)",
    11: "M (Mature 17+)",
    12: "AO (Adults Only 18+)",
    # PEGI
    13: "PEGI 3",
    14: "PEGI 7",
    15: "PEGI 12",
    16: "PEGI 16",
    17: "PEGI 18",
    # CERO
    18: "CERO A",
    19: "CERO B",
    20: "CERO C",
    21: "CERO D",
    22: "CERO Z",
    # USK
    23: "USK 0",
    24: "USK 6",
    25: "USK 12",
    26: "USK 16",
    27: "USK 18",
    # GRAC
    28: "GRAC All",
    29: "GRAC 12",
    30: "GRAC 15",
    31: "GRAC 18",
    32: "GRAC Testing",
    # CLASS_IND
    33: "CLASS_IND L",
    34: "CLASS_IND 10",
    35: "CLASS_IND 12",
    36: "CLASS_IND 14",
    37: "CLASS_IND 16",
    38: "CLASS_IND 18",
    # ACB
    39: "ACB G",
    40: "ACB PG",
    41: "ACB M",
    42: "ACB MA15+",
    43: "ACB R18+",
    44: "ACB RC",
}

# Preferred locale mappings for region-based localization
IGDB_LOCALE_MAP: dict[str, int] = {
    "en-US": 1,  # English (United States)
    "en-GB": 2,  # English (United Kingdom)
    "ja-JP": 3,  # Japanese
    "de-DE": 4,  # German
    "fr-FR": 5,  # French
    "es-ES": 6,  # Spanish (Spain)
    "it-IT": 7,  # Italian
    "pt-BR": 8,  # Portuguese (Brazil)
    "ko-KR": 9,  # Korean
    "zh-CN": 10, # Chinese (Simplified)
    "zh-TW": 11, # Chinese (Traditional)
    "ru-RU": 12, # Russian
    "pl-PL": 13, # Polish
    "nl-NL": 14, # Dutch
    "sv-SE": 15, # Swedish
    "da-DK": 16, # Danish
    "fi-FI": 17, # Finnish
    "no-NO": 18, # Norwegian
}


def get_igdb_preferred_locale(region: str | None = None) -> int | None:
    """Get the IGDB locale ID for a given region code.

    Args:
        region: Region/locale code (e.g., "en-US", "ja-JP")

    Returns:
        IGDB locale ID or None if not found
    """
    if not region:
        return None
    return IGDB_LOCALE_MAP.get(region)


def get_age_rating_string(category: int, rating: int) -> str:
    """Get human-readable age rating string.

    Args:
        category: IGDB age rating category ID
        rating: IGDB age rating value ID

    Returns:
        Human-readable string like "ESRB: M (Mature 17+)"
    """
    category_name = IGDB_AGE_RATING_CATEGORIES.get(category, "Unknown")
    rating_name = IGDB_AGE_RATINGS.get(rating, "Unknown")
    return f"{category_name}: {rating_name}"


# IGDB platform ID to name mapping
IGDB_PLATFORM_NAMES: dict[int, str] = {
    3: "Linux",
    4: "Nintendo 64",
    5: "Wii",
    6: "PC (Microsoft Windows)",
    7: "PlayStation",
    8: "PlayStation 2",
    9: "PlayStation 3",
    11: "Xbox",
    12: "Xbox 360",
    13: "DOS",
    14: "Mac",
    15: "Commodore C64/128/MAX",
    16: "Amiga",
    18: "NES",
    19: "Super Nintendo Entertainment System",
    20: "Nintendo DS",
    21: "Nintendo GameCube",
    22: "Game Boy Color",
    23: "Dreamcast",
    24: "Game Boy Advance",
    25: "Amstrad CPC",
    26: "ZX Spectrum",
    27: "MSX",
    29: "Sega Mega Drive/Genesis",
    30: "Sega 32X",
    32: "Sega Saturn",
    33: "Game Boy",
    34: "Android",
    35: "Sega Game Gear",
    37: "Nintendo 3DS",
    38: "PlayStation Portable",
    39: "iOS",
    41: "Wii U",
    42: "N-Gage",
    46: "PlayStation Vita",
    48: "PlayStation 4",
    49: "Xbox One",
    50: "3DO Interactive Multiplayer",
    51: "Family Computer Disk System",
    52: "Arcade",
    53: "MSX2",
    57: "WonderSwan",
    58: "Super Famicom",
    59: "Atari 2600",
    60: "Atari 7800",
    61: "Atari Lynx",
    62: "Atari Jaguar",
    63: "Atari ST/STE",
    64: "Sega Master System/Mark III",
    65: "Atari 8-bit",
    66: "Atari 5200",
    67: "Intellivision",
    68: "ColecoVision",
    69: "BBC Micro",
    70: "Vectrex",
    71: "Commodore VIC-20",
    72: "Ouya",
    75: "Apple II",
    76: "PocketStation",
    77: "Sharp X1",
    78: "Sega CD",
    79: "Neo Geo MVS",
    80: "Neo Geo AES",
    84: "SG-1000",
    86: "TurboGrafx-16/PC Engine",
    87: "Virtual Boy",
    93: "Commodore 16",
    94: "Commodore Plus/4",
    99: "Family Computer (Famicom)",
    111: "Atari XEGS",
    112: "Sharp X68000",
    114: "Amiga CD",
    115: "Apple IIGS",
    116: "Commodore CDTV",
    117: "Amiga CD32",
    119: "Neo Geo Pocket",
    120: "Neo Geo Pocket Color",
    121: "Gizmondo",
    122: "Game.com",
    123: "WonderSwan Color",
    125: "PC-8801",
    127: "Fairchild Channel F",
    128: "PC Engine SuperGrafx",
    130: "Nintendo Switch",
    132: "Amazon Fire TV",
    133: "Magnavox Odyssey 2",
    136: "Neo Geo CD",
    137: "New Nintendo 3DS",
    149: "PC-9801",
    150: "Turbografx-16/PC Engine CD",
    158: "Amstrad GX4000",
    161: "MSX2+",
    165: "PlayStation VR",
    167: "PlayStation 5",
    169: "Xbox Series X|S",
    170: "Google Stadia",
    171: "Atari Jaguar CD",
    207: "Pokemon mini",
    274: "PC-FX",
    308: "Playdate",
    339: "Sega Pico",
    340: "Gamate",
    343: "Watara Supervision",
    390: "PlayStation VR2",
    416: "Nintendo 64DD",
}
