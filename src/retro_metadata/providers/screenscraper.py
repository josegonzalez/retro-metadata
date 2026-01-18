"""ScreenScraper metadata provider implementation."""

from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# Default ScreenScraper developer credentials (from romm project)
SS_DEV_ID: Final = base64.b64decode("enVyZGkxNQ==").decode()
SS_DEV_PASSWORD: Final = base64.b64decode("eFRKd29PRmpPUUc=").decode()

from retro_metadata.core.exceptions import (
    ProviderAuthenticationError,
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

# Regex to detect ScreenScraper ID tags in filenames like (ssfr-12345)
SS_TAG_REGEX: Final = re.compile(r"\(ssfr-(\d+)\)", re.IGNORECASE)

# Sensitive query parameter keys to strip from URLs
SENSITIVE_KEYS: Final = {"ssid", "sspassword", "devid", "devpassword"}

# Default region priority
DEFAULT_REGIONS: Final = ["us", "wor", "ss", "eu", "jp", "unk"]

# Default language priority
DEFAULT_LANGUAGES: Final = ["en", "fr"]


def _strip_sensitive_params(url: str, keys: set[str]) -> str:
    """Strip sensitive query parameters from URL."""
    if "?" not in url:
        return url

    base, query = url.split("?", 1)
    params = []
    for param in query.split("&"):
        if "=" in param:
            key = param.split("=")[0]
            if key.lower() not in keys:
                params.append(param)
        else:
            params.append(param)

    if params:
        return f"{base}?{'&'.join(params)}"
    return base


class ScreenScraperProvider(MetadataProvider):
    """ScreenScraper metadata provider.

    Requires username and password credentials from ScreenScraper.

    Example:
        config = ProviderConfig(
            enabled=True,
            credentials={"username": "your_user", "password": "your_pass"}
        )
        provider = ScreenScraperProvider(config)
        results = await provider.search("Super Mario World", platform_id=4)
    """

    name = "screenscraper"

    def __init__(
        self,
        config: "ProviderConfig",
        cache: "CacheBackend | None" = None,
        user_agent: str = "retro-metadata/1.0",
        dev_id: str | None = None,
        dev_password: str | None = None,
        region_priority: list[str] | None = None,
        language_priority: list[str] | None = None,
    ) -> None:
        super().__init__(config, cache)
        self._base_url = "https://api.screenscraper.fr/api2"
        self._user_agent = user_agent
        # Use provided dev credentials or fall back to defaults from romm
        self._dev_id = dev_id if dev_id is not None else SS_DEV_ID
        self._dev_password = dev_password if dev_password is not None else SS_DEV_PASSWORD
        self._client: httpx.AsyncClient | None = None
        self._min_similarity_score = 0.6
        self._region_priority = region_priority or DEFAULT_REGIONS.copy()
        self._language_priority = language_priority or DEFAULT_LANGUAGES.copy()

    @property
    def username(self) -> str:
        return self.config.get_credential("username")

    @property
    def password(self) -> str:
        return self.config.get_credential("password")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": self._user_agent},
                timeout=self.config.timeout,
            )
        return self._client

    def _build_auth_params(self) -> dict[str, str]:
        """Build authentication parameters."""
        params = {
            "output": "json",
            "softname": "retro-metadata",
            "ssid": self.username,
            "sspassword": self.password,
        }
        if self._dev_id:
            params["devid"] = self._dev_id
        if self._dev_password:
            params["devpassword"] = self._dev_password
        return params

    def add_auth_to_url(self, url: str) -> str:
        """Add authentication parameters to a ScreenScraper media URL.

        Args:
            url: The media URL to authenticate

        Returns:
            URL with authentication parameters added
        """
        if not url:
            return url

        # Build auth params for media URLs (no output/softname needed)
        params = {
            "devid": self._dev_id,
            "devpassword": self._dev_password,
            "ssid": self.username,
            "sspassword": self.password,
        }

        # Add params to URL
        separator = "&" if "?" in url else "?"
        param_str = "&".join(f"{k}={quote(str(v))}" for k, v in params.items() if v)
        return f"{url}{separator}{param_str}"

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an API request to ScreenScraper."""
        client = await self._get_client()

        if params is None:
            params = {}
        params.update(self._build_auth_params())

        url = f"{self._base_url}/{endpoint}"

        # Log request (mask sensitive credentials)
        log_params = {
            k: v for k, v in params.items()
            if k not in SENSITIVE_KEYS and k not in ("ssid", "sspassword", "devid", "devpassword")
        }
        logger.debug("ScreenScraper API: GET %s", url)
        logger.debug("ScreenScraper API params: %s", log_params)

        try:
            response = await client.get(url, params=params)

            # Check for login error in response text
            if "Erreur de login" in response.text:
                logger.debug("ScreenScraper API: Login error in response")
                raise ProviderAuthenticationError(self.name, "Invalid credentials")

            if response.status_code == 401:
                logger.debug("ScreenScraper API: 401 Unauthorized")
                raise ProviderAuthenticationError(self.name, "Invalid credentials")
            elif response.status_code == 429:
                logger.debug("ScreenScraper API: 429 Rate limited")
                raise ProviderRateLimitError(self.name)

            response.raise_for_status()
            data = response.json()

            # Log full response body only when debug logging is enabled
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("ScreenScraper API response:\n%s", json.dumps(data, indent=2, ensure_ascii=False))

            return data
        except httpx.RequestError as e:
            logger.debug("ScreenScraper API error: %s", e)
            raise ProviderConnectionError(self.name, str(e)) from e

    def _get_preferred_name(self, names: list[dict[str, str]]) -> str:
        """Get the preferred name based on region priority."""
        for region in self._region_priority:
            for name in names:
                if name.get("region", "unk") == region:
                    return name.get("text", "")
        # Fallback to first name
        if names:
            return names[0].get("text", "")
        return ""

    def _get_preferred_text(
        self, items: list[dict[str, str]], key: str = "langue"
    ) -> str:
        """Get preferred text based on language priority."""
        for lang in self._language_priority:
            for item in items:
                if item.get(key) == lang:
                    return item.get("text", "")
        if items:
            return items[0].get("text", "")
        return ""

    def _get_media_url(
        self, medias: list[dict[str, Any]], media_type: str
    ) -> str:
        """Get media URL for a specific type with region preference."""
        for region in self._region_priority:
            for media in medias:
                if (
                    media.get("type") == media_type
                    and media.get("region", "unk") == region
                    and media.get("parent") == "jeu"
                ):
                    url = media.get("url", "")
                    return _strip_sensitive_params(url, SENSITIVE_KEYS)
        # Fallback without region
        for media in medias:
            if media.get("type") == media_type and media.get("parent") == "jeu":
                url = media.get("url", "")
                return _strip_sensitive_params(url, SENSITIVE_KEYS)
        return ""

    async def search(
        self,
        query: str,
        platform_id: int | None = None,
        limit: int = 30,
    ) -> list[SearchResult]:
        """Search for games by name.

        Args:
            query: Search query string
            platform_id: ScreenScraper system ID to filter by
            limit: Maximum number of results (SS API limits to 30)

        Returns:
            List of search results
        """
        if not self.is_enabled:
            return []

        params: dict[str, Any] = {"recherche": query}

        if platform_id:
            params["systemeid"] = str(platform_id)

        result = await self._request("jeuRecherche.php", params)

        games = result.get("response", {}).get("jeux", [])
        # SS returns [{}] when no results
        if len(games) == 1 and not games[0]:
            return []

        search_results = []
        for game in games[:limit]:
            if not game.get("id"):
                continue

            name = self._get_preferred_name(game.get("noms", []))
            cover_url = self._get_media_url(game.get("medias", []), "box-2D")

            # Get release year from dates
            release_year = None
            dates = game.get("dates", [])
            if dates:
                try:
                    date_text = dates[0].get("text", "")
                    if date_text:
                        release_year = int(date_text[:4])
                except (ValueError, IndexError):
                    pass

            search_results.append(
                SearchResult(
                    name=name.replace(" : ", ": "),
                    provider=self.name,
                    provider_id=int(game["id"]),
                    cover_url=cover_url,
                    platforms=[game.get("systeme", {}).get("text", "")],
                    release_year=release_year,
                )
            )

        return search_results

    async def get_by_id(self, game_id: int) -> GameResult | None:
        """Get game details by ScreenScraper ID.

        Args:
            game_id: ScreenScraper game ID

        Returns:
            GameResult with full details, or None if not found
        """
        if not self.is_enabled:
            return None

        result = await self._request("jeuInfos.php", {"gameid": str(game_id)})

        game = result.get("response", {}).get("jeu", {})
        if not game or not game.get("id"):
            return None

        return self._build_game_result(game)

    async def lookup_by_hash(
        self,
        platform_id: int,
        md5: str | None = None,
        sha1: str | None = None,
        crc: str | None = None,
        rom_size: int | None = None,
    ) -> GameResult | None:
        """Look up a game by ROM hash.

        Args:
            platform_id: ScreenScraper system ID
            md5: MD5 hash of the ROM
            sha1: SHA1 hash of the ROM
            crc: CRC hash of the ROM
            rom_size: Size of the ROM in bytes

        Returns:
            GameResult if found, None otherwise
        """
        if not self.is_enabled:
            return None

        if not (md5 or sha1 or crc):
            return None

        params: dict[str, Any] = {"systemeid": str(platform_id)}
        if md5:
            params["md5"] = md5
        if sha1:
            params["sha1"] = sha1
        if crc:
            params["crc"] = crc
        if rom_size:
            params["romtaille"] = str(rom_size)

        result = await self._request("jeuInfos.php", params)

        game = result.get("response", {}).get("jeu", {})
        if not game or not game.get("id"):
            return None

        return self._build_game_result(game)

    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Args:
            filename: ROM filename
            platform_id: ScreenScraper system ID

        Returns:
            GameResult if a match is found, None otherwise
        """
        if not self.is_enabled:
            return None

        # Check for ScreenScraper ID tag in filename
        tagged_id = self.extract_id_from_filename(filename, SS_TAG_REGEX)
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
            "recherche": quote(search_term, safe="/ "),
            "systemeid": str(platform_id),
        }

        result = await self._request("jeuRecherche.php", params)

        games = result.get("response", {}).get("jeux", [])
        if len(games) == 1 and not games[0]:
            games = []

        if not games:
            # Try splitting by special characters
            terms = self.split_search_term(search_term)
            if len(terms) > 1:
                params["recherche"] = quote(terms[-1], safe="/ ")
                result = await self._request("jeuRecherche.php", params)
                games = result.get("response", {}).get("jeux", [])
                if len(games) == 1 and not games[0]:
                    games = []

        if not games:
            return None

        # Build name mapping
        games_by_name: dict[str, dict[str, Any]] = {}
        for game in games:
            if not game.get("id"):
                continue
            for name in game.get("noms", []):
                name_text = name.get("text", "")
                if name_text and (
                    name_text not in games_by_name
                    or int(game["id"]) < int(games_by_name[name_text]["id"])
                ):
                    games_by_name[name_text] = game

        # Find best match
        best_match, score = self.find_best_match(
            search_term, list(games_by_name.keys())
        )

        if best_match and best_match in games_by_name:
            game_result = self._build_game_result(games_by_name[best_match])
            game_result.match_score = score
            return game_result

        return None

    def _clean_filename(self, filename: str) -> str:
        """Remove tags and extension from filename."""
        # Remove extension
        name = re.sub(r"\.[^.]+$", "", filename)
        # Remove common tags like (USA), [!], etc.
        name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name)
        return name.strip()

    def _build_game_result(self, game: dict[str, Any]) -> GameResult:
        """Build a GameResult from ScreenScraper game data."""
        name = self._get_preferred_name(game.get("noms", []))
        summary = self._get_preferred_text(game.get("synopsis", []))

        medias = game.get("medias", [])

        # Extract artwork
        cover_url = self._get_media_url(medias, "box-2D")
        screenshot_urls = []

        screenshot_url = self._get_media_url(medias, "ss")
        if screenshot_url:
            screenshot_urls.append(screenshot_url)

        title_screen = self._get_media_url(medias, "sstitle")
        if title_screen:
            screenshot_urls.append(title_screen)

        fanart = self._get_media_url(medias, "fanart")
        if fanart:
            screenshot_urls.append(fanart)

        logo_url = self._get_media_url(medias, "wheel-hd") or self._get_media_url(
            medias, "wheel"
        )
        banner_url = self._get_media_url(medias, "screenmarquee")

        # Extract metadata
        metadata = self._extract_metadata(game)

        return GameResult(
            name=name.replace(" : ", ": "),
            summary=summary,
            provider=self.name,
            provider_id=int(game["id"]),
            provider_ids={"screenscraper": int(game["id"])},
            artwork=Artwork(
                cover_url=cover_url,
                screenshot_urls=screenshot_urls,
                logo_url=logo_url,
                banner_url=banner_url,
            ),
            metadata=metadata,
            raw_response=game,
        )

    def _extract_metadata(self, game: dict[str, Any]) -> GameMetadata:
        """Extract GameMetadata from ScreenScraper game data."""
        # Extract genres (English names)
        genres = []
        for genre in game.get("genres", []):
            for name in genre.get("noms", []):
                if name.get("langue") == "en":
                    genres.append(name.get("text", ""))
                    break

        # Extract franchises
        franchises = []
        for franchise in game.get("familles", []):
            for name in franchise.get("noms", []):
                for lang in self._language_priority:
                    if name.get("langue") == lang:
                        franchises.append(name.get("text", ""))
                        break

        # Extract game modes
        game_modes = []
        for mode in game.get("modes", []):
            for name in mode.get("noms", []):
                for lang in self._language_priority:
                    if name.get("langue") == lang:
                        game_modes.append(name.get("text", ""))
                        break

        # Extract alternative names
        alt_names = [n.get("text", "") for n in game.get("noms", []) if n.get("text")]

        # Extract companies
        companies = []
        if game.get("editeur", {}).get("text"):
            companies.append(game["editeur"]["text"])
        if game.get("developpeur", {}).get("text"):
            companies.append(game["developpeur"]["text"])

        # Extract release date
        first_release_date = None
        dates = game.get("dates", [])
        if dates:
            # Find the earliest date
            earliest = min(dates, key=lambda d: d.get("text", "9999"), default=None)
            if earliest:
                date_text = earliest.get("text", "")
                try:
                    if len(date_text) == 10:  # YYYY-MM-DD
                        first_release_date = int(
                            datetime.strptime(date_text, "%Y-%m-%d").timestamp()
                        )
                    elif len(date_text) == 4:  # YYYY
                        first_release_date = int(
                            datetime.strptime(date_text, "%Y").timestamp()
                        )
                except ValueError:
                    pass

        # Extract rating
        total_rating = None
        note = game.get("note", {}).get("text", "")
        if note:
            try:
                # SS scores are out of 20, normalize to 100
                total_rating = float(note) * 5
            except ValueError:
                pass

        # Player count
        player_count = game.get("joueurs", {}).get("text", "1")
        if not player_count or player_count.lower() in ("null", "none"):
            player_count = "1"

        return GameMetadata(
            total_rating=total_rating,
            first_release_date=first_release_date,
            genres=genres,
            franchises=franchises,
            alternative_names=alt_names,
            companies=list(dict.fromkeys(companies)),  # Remove duplicates
            game_modes=game_modes,
            player_count=str(player_count),
            raw_data=game,
        )

    def get_platform(self, slug: str) -> Platform | None:
        """Get platform information for a slug.

        Args:
            slug: Universal platform slug

        Returns:
            Platform with ScreenScraper ID, or None if not supported
        """
        try:
            ups = UPS(slug)
        except ValueError:
            return None

        if ups not in SCREENSCRAPER_PLATFORM_MAP:
            return None

        platform_info = SCREENSCRAPER_PLATFORM_MAP[ups]
        return Platform(
            slug=slug,
            name=platform_info["name"],
            provider_ids={"screenscraper": platform_info["id"]},
        )

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()


# Platform mapping from universal slugs to ScreenScraper system IDs
SCREENSCRAPER_PLATFORM_MAP: dict[UPS, dict[str, Any]] = {
    UPS._3DO: {"id": 29, "name": "3DO"},
    UPS.AMIGA: {"id": 64, "name": "Amiga"},
    UPS.AMIGA_CD32: {"id": 130, "name": "Amiga CD32"},
    UPS.ACPC: {"id": 65, "name": "CPC"},
    UPS.ACTION_MAX: {"id": 81, "name": "Action Max"},
    UPS.ADVENTURE_VISION: {"id": 78, "name": "Entex Adventure Vision"},
    UPS.AMSTRAD_GX4000: {"id": 87, "name": "Amstrad GX4000"},
    UPS.ANDROID: {"id": 63, "name": "Android"},
    UPS.APPLEII: {"id": 86, "name": "Apple II"},
    UPS.APPLE_IIGS: {"id": 51, "name": "Apple IIGS"},
    UPS.ARCADE: {"id": 75, "name": "Arcade"},
    UPS.ARCADIA_2001: {"id": 94, "name": "Arcadia 2001"},
    UPS.ATARI2600: {"id": 26, "name": "Atari 2600"},
    UPS.ATARI5200: {"id": 40, "name": "Atari 5200"},
    UPS.ATARI7800: {"id": 41, "name": "Atari 7800"},
    UPS.ATARI800: {"id": 43, "name": "Atari 800"},
    UPS.ATARI_XEGS: {"id": 43, "name": "Atari XEGS"},
    UPS.ATARI_JAGUAR_CD: {"id": 171, "name": "Atari Jaguar CD"},
    UPS.ATARI_ST: {"id": 42, "name": "Atari ST"},
    UPS.ATOM: {"id": 36, "name": "Atom"},
    UPS.ACORN_ARCHIMEDES: {"id": 84, "name": "Acorn Archimedes"},
    UPS.BBCMICRO: {"id": 37, "name": "BBC Micro"},
    UPS.ASTROCADE: {"id": 44, "name": "Astrocade"},
    UPS.PHILIPS_CD_I: {"id": 133, "name": "CD-i"},
    UPS.COMMODORE_CDTV: {"id": 129, "name": "Amiga CDTV"},
    UPS.CAMPUTERS_LYNX: {"id": 88, "name": "Camputers Lynx"},
    UPS.CASIO_LOOPY: {"id": 98, "name": "Loopy"},
    UPS.CASIO_PV_1000: {"id": 74, "name": "PV-1000"},
    UPS.FAIRCHILD_CHANNEL_F: {"id": 80, "name": "Channel F"},
    UPS.COLECOVISION: {"id": 48, "name": "Colecovision"},
    UPS.C64: {"id": 66, "name": "Commodore 64"},
    UPS.DOS: {"id": 135, "name": "PC DOS"},
    UPS.DC: {"id": 23, "name": "Dreamcast"},
    UPS.ACORN_ELECTRON: {"id": 85, "name": "Electron"},
    UPS.FDS: {"id": 106, "name": "Famicom Disk System"},
    UPS.GB: {"id": 9, "name": "Game Boy"},
    UPS.GBA: {"id": 12, "name": "Game Boy Advance"},
    UPS.GBC: {"id": 10, "name": "Game Boy Color"},
    UPS.GAMEGEAR: {"id": 21, "name": "Game Gear"},
    UPS.GENESIS: {"id": 1, "name": "Mega Drive"},
    UPS.INTELLIVISION: {"id": 115, "name": "Intellivision"},
    UPS.JAGUAR: {"id": 27, "name": "Jaguar"},
    UPS.LYNX: {"id": 28, "name": "Lynx"},
    UPS.MSX: {"id": 113, "name": "MSX"},
    UPS.MSX2: {"id": 116, "name": "MSX2"},
    UPS.N64: {"id": 14, "name": "Nintendo 64"},
    UPS.N3DS: {"id": 17, "name": "Nintendo 3DS"},
    UPS.NDS: {"id": 15, "name": "Nintendo DS"},
    UPS.NES: {"id": 3, "name": "NES"},
    UPS.NGC: {"id": 13, "name": "GameCube"},
    UPS.NEO_GEO_CD: {"id": 70, "name": "Neo Geo CD"},
    UPS.NEO_GEO_POCKET: {"id": 25, "name": "Neo Geo Pocket"},
    UPS.NEO_GEO_POCKET_COLOR: {"id": 82, "name": "Neo Geo Pocket Color"},
    UPS.NEOGEOAES: {"id": 142, "name": "Neo Geo AES"},
    UPS.ODYSSEY_2: {"id": 104, "name": "Odyssey 2"},
    UPS.PC_FX: {"id": 72, "name": "PC-FX"},
    UPS.PC_8800_SERIES: {"id": 221, "name": "PC-88"},
    UPS.PC_9800_SERIES: {"id": 208, "name": "PC-98"},
    UPS.PSX: {"id": 57, "name": "PlayStation"},
    UPS.PS2: {"id": 58, "name": "PlayStation 2"},
    UPS.PS3: {"id": 59, "name": "PlayStation 3"},
    UPS.PSP: {"id": 61, "name": "PSP"},
    UPS.PSVITA: {"id": 62, "name": "PS Vita"},
    UPS.SATURN: {"id": 22, "name": "Saturn"},
    UPS.SEGA32: {"id": 19, "name": "32X"},
    UPS.SEGACD: {"id": 20, "name": "Mega CD"},
    UPS.SG1000: {"id": 109, "name": "SG-1000"},
    UPS.SMS: {"id": 2, "name": "Master System"},
    UPS.SNES: {"id": 4, "name": "Super Nintendo"},
    UPS.SUPERGRAFX: {"id": 105, "name": "SuperGrafx"},
    UPS.SWITCH: {"id": 225, "name": "Switch"},
    UPS.TG16: {"id": 31, "name": "TurboGrafx-16"},
    UPS.TURBOGRAFX_CD: {"id": 114, "name": "TurboGrafx-CD"},
    UPS.VECTREX: {"id": 102, "name": "Vectrex"},
    UPS.VIRTUALBOY: {"id": 11, "name": "Virtual Boy"},
    UPS.WII: {"id": 16, "name": "Wii"},
    UPS.WIIU: {"id": 18, "name": "Wii U"},
    UPS.WONDERSWAN: {"id": 45, "name": "WonderSwan"},
    UPS.WONDERSWAN_COLOR: {"id": 46, "name": "WonderSwan Color"},
    UPS.XBOX: {"id": 32, "name": "Xbox"},
    UPS.XBOX360: {"id": 33, "name": "Xbox 360"},
    UPS.ZXS: {"id": 76, "name": "ZX Spectrum"},
}
