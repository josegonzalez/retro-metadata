"""MobyGames metadata provider implementation."""

from __future__ import annotations

import contextlib
import json
import logging
import re
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import quote

import httpx

from retro_metadata.core.exceptions import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderRateLimitError,
)
from retro_metadata.platforms.mappings import get_mobygames_platform_id
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

# Regex to detect MobyGames ID tags in filenames like (moby-12345)
MOBYGAMES_TAG_REGEX: Final = re.compile(r"\(moby-(\d+)\)", re.IGNORECASE)

# Sony serial format regex - matches PS1/PS2/PSP serial codes like SLUS-12345, SCUS-97328
# Format: 4 letters followed by hyphen and 5 digits
SONY_SERIAL_REGEX: Final = re.compile(r"([A-Z]{4})[_-](\d{5})", re.IGNORECASE)

# PS2 OPL format regex - matches formats like SLUS_123.45 or SCUS_973.28
# OPL uses underscore and dot notation
PS2_OPL_REGEX: Final = re.compile(r"([A-Z]{4})_(\d{3})\.(\d{2})", re.IGNORECASE)

# Nintendo Switch titleID format - matches 16-character hex IDs like 0100000000010000
SWITCH_TITLEDB_REGEX: Final = re.compile(r"([0-9A-Fa-f]{16})")

# Nintendo Switch productID format - matches product IDs like LA-H-AAAAA
SWITCH_PRODUCT_ID_REGEX: Final = re.compile(r"[A-Z]{2}-[A-Z]-([A-Z0-9]{5})", re.IGNORECASE)

# MAME arcade format - matches MAME ROM names (typically short alphanumeric identifiers)
MAME_ARCADE_REGEX: Final = re.compile(r"^([a-z0-9_]+)$", re.IGNORECASE)


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
        config: ProviderConfig,
        cache: CacheBackend | None = None,
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
                    with contextlib.suppress(ValueError, IndexError):
                        release_year = int(first_date[:4])

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

        Supports multiple identification methods:
        - MobyGames ID tags in filename: (moby-12345)
        - Sony serial codes: SLUS-12345, SCUS_973.28 (PS1/PS2/PSP)
        - Nintendo Switch IDs: titleID (16-char hex) or productID (LA-H-XXXXX)
        - MAME arcade ROM names
        - Standard name-based search

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

        search_term = None

        # Try Sony serial format for PS1/PS2/PSP platforms
        # MobyGames platform IDs: PS1=6, PS2=7, PSP=46
        if platform_id in (6, 7, 46):
            serial_code = self._extract_serial_code(filename)
            if serial_code:
                logger.debug("MobyGames: Searching by Sony serial code: %s", serial_code)
                search_term = serial_code

        # Try Nintendo Switch ID formats
        # MobyGames platform ID: Switch=203
        if platform_id == 203 and not search_term:
            title_id, product_id = self._extract_switch_id(filename)
            if product_id:
                logger.debug("MobyGames: Searching by Switch product ID: %s", product_id)
                search_term = product_id
            elif title_id:
                logger.debug("MobyGames: Searching by Switch title ID: %s", title_id)
                search_term = title_id

        # Try MAME format for arcade platform
        # MobyGames platform ID: Arcade=143
        if platform_id == 143 and not search_term and self._is_mame_format(filename):
            # For MAME, use the filename directly (without extension)
            mame_name = re.sub(r"\.[^.]+$", "", filename)
            logger.debug("MobyGames: Searching by MAME ROM name: %s", mame_name)
            search_term = mame_name

        # Fall back to cleaned filename if no special format detected
        if not search_term:
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

    def _extract_serial_code(self, filename: str) -> str | None:
        """Extract serial code from filename for Sony platforms (PS1/PS2/PSP).

        Supports:
        - Standard Sony serial format: SLUS-12345, SCUS-97328
        - PS2 OPL format: SLUS_123.45

        Args:
            filename: ROM filename

        Returns:
            Formatted serial code (e.g., "SLUS-12345") or None
        """
        # Try PS2 OPL format first (SLUS_123.45)
        opl_match = PS2_OPL_REGEX.search(filename)
        if opl_match:
            prefix = opl_match.group(1).upper()
            part1 = opl_match.group(2)
            part2 = opl_match.group(3)
            return f"{prefix}-{part1}{part2}"

        # Try standard Sony serial format (SLUS-12345 or SLUS_12345)
        serial_match = SONY_SERIAL_REGEX.search(filename)
        if serial_match:
            prefix = serial_match.group(1).upper()
            number = serial_match.group(2)
            return f"{prefix}-{number}"

        return None

    def _extract_switch_id(self, filename: str) -> tuple[str | None, str | None]:
        """Extract Nintendo Switch title ID or product ID from filename.

        Args:
            filename: ROM filename

        Returns:
            Tuple of (title_id, product_id) - either may be None
        """
        title_id = None
        product_id = None

        # Try titleID format (16-char hex)
        titledb_match = SWITCH_TITLEDB_REGEX.search(filename)
        if titledb_match:
            title_id = titledb_match.group(1).upper()

        # Try productID format (LA-H-AAAAA)
        product_match = SWITCH_PRODUCT_ID_REGEX.search(filename)
        if product_match:
            product_id = product_match.group(1).upper()

        return title_id, product_id

    def _is_mame_format(self, filename: str) -> bool:
        """Check if filename appears to be a MAME ROM name.

        MAME ROM names are typically short lowercase alphanumeric identifiers
        without spaces or special characters.

        Args:
            filename: ROM filename (without extension)

        Returns:
            True if filename matches MAME naming convention
        """
        # Remove extension first
        name = re.sub(r"\.[^.]+$", "", filename)
        # MAME names are typically short (under 20 chars) and alphanumeric
        if len(name) > 20:
            return False
        return bool(MAME_ARCADE_REGEX.match(name))

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
            with contextlib.suppress(ValueError, TypeError):
                total_rating = float(game["moby_score"]) * 10

        return GameMetadata(
            total_rating=total_rating,
            genres=genres,
            alternative_names=alt_names,
            platforms=platforms,
            raw_data=game,
        )

    def get_platform(self, slug: str) -> Platform | None:
        """Get platform information for a slug.

        Args:
            slug: Universal platform slug

        Returns:
            Platform with MobyGames ID, or None if not supported
        """
        try:
            ups = UPS(slug)
        except ValueError:
            return None

        platform_id = get_mobygames_platform_id(ups)
        if platform_id is None:
            return None

        # Get platform name from the mapping
        name = MOBYGAMES_PLATFORM_NAMES.get(platform_id, slug.replace("-", " ").title())

        return Platform(
            slug=slug,
            name=name,
            provider_ids={"mobygames": platform_id},
        )

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()


# MobyGames platform ID to name mapping
MOBYGAMES_PLATFORM_NAMES: dict[int, str] = {
    1: "Linux",
    2: "DOS",
    3: "Windows",
    4: "PC Booter",
    5: "Windows 3.x",
    6: "PlayStation",
    7: "PlayStation 2",
    8: "Dreamcast",
    9: "Nintendo 64",
    10: "Game Boy",
    11: "Game Boy Color",
    12: "Game Boy Advance",
    13: "Xbox",
    14: "GameCube",
    15: "SNES",
    16: "Genesis",
    17: "Jaguar",
    18: "Lynx",
    19: "Amiga",
    20: "SEGA CD",
    21: "SEGA 32X",
    22: "NES",
    23: "Saturn",
    24: "Atari ST",
    25: "Game Gear",
    26: "SEGA Master System",
    27: "Commodore 64",
    28: "Atari 2600",
    29: "ColecoVision",
    30: "Intellivision",
    31: "Apple II",
    32: "N-Gage",
    33: "Atari 5200",
    34: "Atari 7800",
    35: "3DO",
    36: "Neo Geo",
    37: "Vectrex",
    38: "Virtual Boy",
    39: "Atari 8-bit",
    40: "TurboGrafx-16",
    41: "ZX Spectrum",
    42: "Acorn 32-bit",
    43: "VIC-20",
    44: "Nintendo DS",
    45: "TurboGrafx CD",
    46: "PSP",
    47: "TI-99/4A",
    48: "WonderSwan",
    49: "WonderSwan Color",
    50: "Game.com",
    51: "Palm OS",
    52: "CP/M",
    53: "Neo Geo Pocket Color",
    54: "Neo Geo CD",
    55: "Gizmondo",
    56: "Windows Mobile",
    57: "MSX",
    58: "TRS-80",
    59: "PC-FX",
    60: "Amstrad CPC",
    61: "Commodore 128",
    62: "TRS-80 CoCo",
    63: "BREW",
    64: "J2ME",
    65: "Exidy Sorcerer",
    66: "Sharp Zaurus",
    67: "Symbian",
    68: "DVD Player",
    69: "Xbox 360",
    70: "Nuon",
    71: "Dedicated console",
    72: "Dedicated handheld",
    73: "CD-i",
    74: "Macintosh",
    75: "Apple IIgs",
    76: "Fairchild Channel F",
    77: "Sinclair QL",
    78: "Odyssey 2",
    79: "Dragon 32/64",
    80: "Memotech MTX",
    81: "PlayStation 3",
    82: "Wii",
    83: "Commodore CDTV",
    84: "Coleco Adam",
    85: "OS/2",
    86: "iOS",
    87: "Nintendo DSi",
    88: "Commodore PET/CBM",
    89: "Microvision",
    90: "BlackBerry",
    91: "Android",
    92: "BBC Micro",
    93: "Electron",
    94: "PC-8801",
    95: "PC-9801",
    96: "RCA Studio II",
    97: "Aquarius",
    98: "Game & Watch",
    99: "Camputers Lynx",
    100: "NewBrain",
    101: "Nintendo 3DS",
    102: "FM Towns",
    103: "Sega Pico",
    104: "APF MP1000/Imagination Machine",
    105: "PlayStation Vita",
    106: "Sharp X68000",
    107: "Tatung Einstein",
    108: "Casio Loopy",
    109: "Watara Supervision",
    110: "Casio PV-1000",
    111: "Oric",
    112: "Exelvision",
    113: "Enterprise",
    114: "SG-1000",
    115: "Commodore 16/Plus 4",
    116: "Mattel Aquarius",
    117: "Acorn Archimedes",
    118: "Laser 200",
    119: "ZX80",
    120: "ZX81",
    121: "Sharp X1",
    122: "Apogee BK-01",
    123: "Amiga CD32",
    124: "SAM Coupé",
    125: "Sharp MZ-80K",
    126: "FM-7",
    127: "PC Engine SuperGrafx",
    128: "Videopac+ G7400",
    129: "Atom",
    130: "Tomy Tutor",
    131: "PC-6001",
    132: "Wii U",
    133: "Spectravideo",
    134: "Thomson TO",
    135: "Thomson MO5",
    136: "Amstrad PCW",
    137: "Sord M5",
    138: "Colour Genie",
    139: "VC 4000",
    140: "CreatiVision",
    141: "PlayStation 4",
    142: "Xbox One",
    143: "Arcade",
    144: "Ouya",
    145: "Mega Duck",
    146: "Epoch Super Cassette Vision",
    147: "PocketStation",
    148: "Zeebo",
    149: "Leapster",
    150: "V.Smile",
    151: "Didj",
    152: "Pokemon Mini",
    153: "LeapFrog Explorer",
    154: "Leapster Explorer",
    155: "Leaptv",
    156: "ClickStart",
    157: "Digiblast",
    158: "HyperScan",
    159: "Amazon Fire TV",
    160: "Bally Astrocade",
    161: "Playdia",
    162: "Arcadia 2001",
    163: "LaserActive",
    164: "Philips VG 5000",
    165: "N-Gage (service)",
    166: "Jaguar CD",
    167: "Channel F",
    168: "Super A'Can",
    169: "Neo Geo Pocket",
    170: "Adventurevision",
    171: "GP32",
    172: "GP2X",
    173: "Dingoo",
    174: "New Nintendo 3DS",
    175: "Pandora",
    176: "Timex Sinclair 2068",
    177: "KC 85",
    178: "Robotron Z1013",
    179: "Vector-06C",
    180: "Elektronika BK",
    181: "Galaksija",
    182: "MSX Turbo-R",
    183: "Agat",
    184: "UKNC",
    185: "Orao",
    186: "Pecom 64",
    187: "Partner 01.01",
    188: "Radio 86RK",
    189: "Gamate",
    190: "Game Wave",
    191: "XaviXPORT",
    192: "Action Max",
    193: "Epoch Cassette Vision",
    194: "Epoch Game Pocket Computer",
    195: "Sony Ericsson",
    196: "RISC OS",
    197: "BeOS",
    198: "Amstrad GX4000",
    199: "Roku",
    200: "tvOS",
    201: "Fire OS",
    202: "KaiOS",
    203: "Nintendo Switch",
    204: "Stadia",
    205: "Luna",
    206: "HP 48",
    207: "TI-83",
    208: "TI-89",
    209: "Casio Calculator",
    210: "HP 49/50",
    211: "Apple III",
    212: "Super Cassette Vision",
    213: "Altair 8800",
    214: "IMSAI 8080",
    215: "Sol-20",
    216: "Nascom",
    217: "Ohio Scientific",
    218: "Compucolor",
    219: "Cromemco",
    220: "Interact",
    221: "VideoBrain",
    222: "Tiki-100",
    223: "Spectravideo 328",
    224: "Matra Alice",
    225: "Philips P2000",
    226: "Jupiter Ace",
    227: "EACA Colour Genie",
    228: "Laser 310",
    229: "Laser 500",
    230: "Sanyo MBC-55x",
    231: "Kaypro",
    232: "Heathkit H8/H89",
    233: "IMSAI 8080",
    234: "Processor Technology",
    235: "MITS Altair 680",
    236: "Ohio Scientific C1P/C4P",
    237: "SOL Terminal",
    238: "Hazeltine",
    239: "SWTP 6800",
    240: "Compustar",
    241: "MOS KIM-1",
    242: "SYM-1",
    243: "AIM-65",
    244: "Superboard II",
    245: "UK101",
    246: "Nascom 1/2",
    247: "DAI",
    248: "Sord M5",
    249: "Apple Lisa",
    250: "Xerox Alto",
    251: "Xerox Star",
    252: "HP 9830",
    253: "HP 3000",
    254: "Plato",
    255: "Plugged In",
    256: "OpenBOR",
    257: "ScummVM",
    258: "Flash",
    259: "HTML5",
    260: "Browser",
    261: "OnLive",
    262: "GameStick",
    263: "GamePop",
    264: "Shield Portable",
    265: "Shield TV",
    266: "Shield Tablet",
    267: "Oculus Go",
    268: "Oculus Quest",
    269: "Oculus Rift",
    270: "HTC Vive",
    271: "Valve Index",
    272: "Windows Mixed Reality",
    273: "Google Stadia",
    274: "Pico 4",
    275: "Meta Quest 2",
    276: "Meta Quest Pro",
    277: "Meta Quest 3",
    278: "Apple Vision Pro",
    279: "Intellivision Amico",
    280: "Atari VCS",
    281: "Playdate",
    282: "Analogue Pocket",
    283: "FPGAES",
    284: "MiSTer FPGA",
    285: "Polymega",
    286: "PlayStation VR",
    287: "PlayStation VR2",
    288: "PlayStation 5",
    289: "Xbox Series X|S",
    290: "Steam Deck",
    291: "AYANEO",
    292: "GPD Win",
    293: "OneXPlayer",
    294: "Evercade",
    295: "Evercade VS",
    296: "Evercade EXP",
    297: "Retroid Pocket",
    298: "Playdate",
    299: "Arduboy",
    300: "Thumby",
    301: "TIC-80",
    302: "PICO-8",
    303: "Lexaloffle Voxatron",
    304: "WASM-4",
    305: "GB Studio",
    306: "NES Maker",
    307: "Uzebox",
    308: "Commander X16",
    309: "Agon Light",
    310: "Colour Maximite 2",
    311: "ZX Spectrum Next",
    312: "Mega65",
    313: "TheC64",
    314: "A500 Mini",
    315: "Atari 400/800 Mini",
    316: "THE400 Mini",
    317: "Atari 2600+",
    318: "Super Pocket",
    319: "RG35XX",
    320: "Miyoo Mini",
}
