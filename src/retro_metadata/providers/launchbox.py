"""LaunchBox metadata provider implementation.

LaunchBox provides metadata through downloadable XML files that need to be
loaded locally. This provider supports both pre-loaded data and lazy loading
from XML files.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final
from xml.etree import ElementTree as ET

from retro_metadata.platforms.slugs import UniversalPlatformSlug as UPS
from retro_metadata.providers.base import MetadataProvider
from retro_metadata.types.common import (
    AgeRating,
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

# Regex to detect LaunchBox ID tags in filenames like (launchbox-12345)
LAUNCHBOX_TAG_REGEX: Final = re.compile(r"\(launchbox-(\d+)\)", re.IGNORECASE)

# Base URL for LaunchBox images
LAUNCHBOX_IMAGE_URL: Final = "https://images.launchbox-app.com"

# Cover image type priority
COVER_PRIORITY: Final = [
    "Box - Front",
    "Box - 3D",
    "Fanart - Box - Front",
    "Cart - Front",
    "Cart - 3D",
]


def _extract_video_id(url: str | None) -> str:
    """Extract YouTube video ID from URL."""
    if not url:
        return ""

    if "youtube.com/watch?v=" in url:
        return url.split("v=")[-1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("/")[-1].split("?")[0]

    return ""


class LaunchBoxProvider(MetadataProvider):
    """LaunchBox metadata provider.

    Uses locally stored LaunchBox metadata XML files.
    Metadata can be downloaded from: https://gamesdb.launchbox-app.com/

    Example:
        config = ProviderConfig(
            enabled=True,
            settings={"metadata_path": "/path/to/launchbox/Metadata.xml"}
        )
        provider = LaunchBoxProvider(config)
        await provider.load_metadata()
        results = await provider.search("Super Mario World", platform_id=31)
    """

    name = "launchbox"

    def __init__(
        self,
        config: ProviderConfig,
        cache: CacheBackend | None = None,
        metadata_path: str | Path | None = None,
    ) -> None:
        super().__init__(config, cache)
        self._metadata_path = metadata_path or config.settings.get("metadata_path")
        self._min_similarity_score = 0.6

        # In-memory indices
        self._games_by_id: dict[int, dict[str, Any]] = {}
        self._games_by_name: dict[str, dict[int, dict[str, Any]]] = {}  # name -> platform_id -> game
        self._images_by_game_id: dict[int, list[dict[str, Any]]] = {}
        self._loaded = False

    async def load_metadata(self, metadata_path: str | Path | None = None) -> bool:
        """Load metadata from LaunchBox XML files.

        Args:
            metadata_path: Path to Metadata.xml file (optional, uses config if not provided)

        Returns:
            True if loaded successfully
        """
        path = metadata_path or self._metadata_path
        if not path:
            return False

        path = Path(path)
        if not path.exists():
            return False

        try:
            tree = ET.parse(path)
            root = tree.getroot()

            # Parse games
            for game_elem in root.findall(".//Game"):
                game = self._parse_game_element(game_elem)
                if game and game.get("DatabaseID"):
                    db_id = int(game["DatabaseID"])
                    self._games_by_id[db_id] = game

                    # Index by name and platform
                    name_lower = game.get("Name", "").lower()
                    if name_lower:
                        if name_lower not in self._games_by_name:
                            self._games_by_name[name_lower] = {}
                        platform_name = game.get("Platform", "")
                        platform_id = self._get_platform_id_by_name(platform_name)
                        if platform_id:
                            self._games_by_name[name_lower][platform_id] = game

            # Parse images (if in same file or separate file)
            images_path = path.parent / "Images.xml"
            if images_path.exists():
                images_tree = ET.parse(images_path)
                images_root = images_tree.getroot()
                for image_elem in images_root.findall(".//GameImage"):
                    image = self._parse_image_element(image_elem)
                    if image and image.get("DatabaseID"):
                        db_id = int(image["DatabaseID"])
                        if db_id not in self._images_by_game_id:
                            self._images_by_game_id[db_id] = []
                        self._images_by_game_id[db_id].append(image)

            self._loaded = True
            return True
        except ET.ParseError:
            return False

    def _parse_game_element(self, elem: ET.Element) -> dict[str, Any]:
        """Parse a Game XML element into a dictionary."""
        game: dict[str, Any] = {}
        for child in elem:
            if child.text:
                game[child.tag] = child.text
        return game

    def _parse_image_element(self, elem: ET.Element) -> dict[str, Any]:
        """Parse a GameImage XML element into a dictionary."""
        image: dict[str, Any] = {}
        for child in elem:
            if child.text:
                image[child.tag] = child.text
        return image

    def _get_platform_id_by_name(self, platform_name: str) -> int | None:
        """Get LaunchBox platform ID by platform name."""
        for _ups, info in LAUNCHBOX_PLATFORM_MAP.items():
            if info["name"] == platform_name:
                return info["id"]
        return None

    async def search(
        self,
        query: str,
        platform_id: int | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search for games by name.

        Args:
            query: Search query string
            platform_id: LaunchBox platform ID to filter by
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.is_enabled:
            return []

        if not self._loaded:
            await self.load_metadata()

        query_lower = query.lower()
        results = []

        for name, platforms in self._games_by_name.items():
            if query_lower in name:
                for plat_id, game in platforms.items():
                    if platform_id and plat_id != platform_id:
                        continue

                    db_id = int(game.get("DatabaseID", 0))
                    cover_url = self._get_best_cover(db_id)

                    release_year = None
                    try:
                        date_str = game.get("ReleaseDate", "")
                        if date_str:
                            release_year = int(date_str[:4])
                    except (ValueError, IndexError):
                        pass

                    results.append(
                        SearchResult(
                            name=game.get("Name", ""),
                            provider=self.name,
                            provider_id=db_id,
                            cover_url=cover_url,
                            platforms=[game.get("Platform", "")],
                            release_year=release_year,
                        )
                    )

                    if len(results) >= limit:
                        break

            if len(results) >= limit:
                break

        return results

    async def get_by_id(self, game_id: int) -> GameResult | None:
        """Get game details by LaunchBox database ID.

        Args:
            game_id: LaunchBox database ID

        Returns:
            GameResult with full details, or None if not found
        """
        if not self.is_enabled:
            return None

        if not self._loaded:
            await self.load_metadata()

        game = self._games_by_id.get(game_id)
        if not game:
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
            platform_id: LaunchBox platform ID

        Returns:
            GameResult if a match is found, None otherwise
        """
        if not self.is_enabled:
            return None

        # Check for LaunchBox ID tag in filename
        tagged_id = self.extract_id_from_filename(filename, LAUNCHBOX_TAG_REGEX)
        if tagged_id:
            result = await self.get_by_id(tagged_id)
            if result:
                return result

        if not self._loaded:
            await self.load_metadata()

        # Clean the filename
        search_term = self._clean_filename(filename)
        # LaunchBox uses ": " instead of " - "
        search_term = re.sub(r"\s?-\s", ": ", search_term)
        search_term_lower = search_term.lower()

        # Look for exact match first
        if search_term_lower in self._games_by_name:
            platforms = self._games_by_name[search_term_lower]
            if platform_id and platform_id in platforms:
                return self._build_game_result(platforms[platform_id])
            elif platforms:
                # Return first match if no platform specified
                game = next(iter(platforms.values()))
                return self._build_game_result(game)

        # Fuzzy match
        all_names = list(self._games_by_name.keys())
        best_match, score = self.find_best_match(search_term_lower, all_names)

        if best_match and best_match in self._games_by_name:
            platforms = self._games_by_name[best_match]
            if platform_id and platform_id in platforms:
                game = platforms[platform_id]
            else:
                game = next(iter(platforms.values()))

            result = self._build_game_result(game)
            result.match_score = score
            return result

        return None

    def _clean_filename(self, filename: str) -> str:
        """Remove tags and extension from filename."""
        name = re.sub(r"\.[^.]+$", "", filename)
        name = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name)
        return name.strip()

    def _get_best_cover(self, game_id: int) -> str:
        """Get the best cover image URL for a game."""
        images = self._images_by_game_id.get(game_id, [])

        for cover_type in COVER_PRIORITY:
            for image in images:
                if image.get("Type") == cover_type:
                    filename = image.get("FileName", "")
                    if filename:
                        return f"{LAUNCHBOX_IMAGE_URL}/{filename}"

        return ""

    def _get_screenshots(self, game_id: int) -> list[str]:
        """Get screenshot URLs for a game."""
        images = self._images_by_game_id.get(game_id, [])
        screenshots = []

        for image in images:
            if "Screenshot" in image.get("Type", ""):
                filename = image.get("FileName", "")
                if filename:
                    screenshots.append(f"{LAUNCHBOX_IMAGE_URL}/{filename}")

        return screenshots

    def _build_game_result(self, game: dict[str, Any]) -> GameResult:
        """Build a GameResult from LaunchBox game data."""
        db_id = int(game.get("DatabaseID", 0))

        cover_url = self._get_best_cover(db_id)
        screenshot_urls = self._get_screenshots(db_id)

        # Extract metadata
        metadata = self._extract_metadata(game, db_id)

        return GameResult(
            name=game.get("Name", ""),
            summary=game.get("Overview", ""),
            provider=self.name,
            provider_id=db_id,
            provider_ids={"launchbox": db_id},
            artwork=Artwork(
                cover_url=cover_url,
                screenshot_urls=screenshot_urls,
            ),
            metadata=metadata,
            raw_response=game,
        )

    def _extract_metadata(self, game: dict[str, Any], game_id: int) -> GameMetadata:  # noqa: ARG002
        """Extract GameMetadata from LaunchBox game data."""
        # Extract release date
        first_release_date = None
        try:
            date_str = game.get("ReleaseDate", "")
            if date_str:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
                first_release_date = int(parsed_date.timestamp())
        except (ValueError, TypeError):
            pass

        # Release year
        release_year = None
        if first_release_date:
            release_year = datetime.fromtimestamp(first_release_date).year

        # Genres
        genres = []
        genres_str = game.get("Genres", "")
        if genres_str:
            genres = genres_str.split(";")

        # Companies
        companies = []
        if game.get("Publisher"):
            companies.append(game["Publisher"])
        if game.get("Developer"):
            companies.append(game["Developer"])

        # Age rating
        age_ratings = []
        esrb = game.get("ESRB", "")
        if esrb:
            rating = esrb.split(" - ")[0].strip()
            age_ratings.append(AgeRating(rating=rating, category="ESRB"))

        # Player count
        max_players = game.get("MaxPlayers", "1")
        player_count = str(max_players) if max_players else "1"

        # YouTube video
        youtube_video_id = _extract_video_id(game.get("VideoURL"))

        # Rating
        total_rating = None
        try:
            rating = game.get("CommunityRating")
            if rating:
                # LaunchBox ratings are 0-5, convert to 0-100
                total_rating = float(rating) * 20
        except (ValueError, TypeError):
            pass

        # Wikipedia URL
        wikipedia_url = game.get("WikipediaURL", "")

        # Cooperative mode
        cooperative = game.get("Cooperative", "").lower() == "true"

        # Game modes (derive from MaxPlayers and Cooperative)
        game_modes = []
        if max_players and int(max_players) == 1:
            game_modes.append("Single player")
        if max_players and int(max_players) > 1:
            game_modes.append("Multiplayer")
        if cooperative:
            game_modes.append("Co-op")

        return GameMetadata(
            total_rating=total_rating,
            first_release_date=first_release_date,
            youtube_video_id=youtube_video_id if youtube_video_id else None,
            genres=genres,
            game_modes=game_modes,
            companies=list(dict.fromkeys(companies)),
            age_ratings=age_ratings,
            player_count=player_count,
            developer=game.get("Developer", ""),
            publisher=game.get("Publisher", ""),
            release_year=release_year,
            raw_data={
                **game,
                "wikipedia_url": wikipedia_url,
                "cooperative": cooperative,
            },
        )

    def get_platform(self, slug: str) -> Platform | None:
        """Get platform information for a slug.

        Args:
            slug: Universal platform slug

        Returns:
            Platform with LaunchBox ID, or None if not supported
        """
        try:
            ups = UPS(slug)
        except ValueError:
            return None

        if ups not in LAUNCHBOX_PLATFORM_MAP:
            return None

        platform_info = LAUNCHBOX_PLATFORM_MAP[ups]
        return Platform(
            slug=slug,
            name=platform_info["name"],
            provider_ids={"launchbox": platform_info["id"]},
        )

    async def close(self) -> None:
        """Clear loaded data."""
        self._games_by_id.clear()
        self._games_by_name.clear()
        self._images_by_game_id.clear()
        self._loaded = False


# Platform mapping from universal slugs to LaunchBox platform IDs
LAUNCHBOX_PLATFORM_MAP: dict[UPS, dict[str, Any]] = {
    UPS._3DO: {"id": 1, "name": "3DO Interactive Multiplayer"},
    UPS.N3DS: {"id": 24, "name": "Nintendo 3DS"},
    UPS.ACORN_ARCHIMEDES: {"id": 74, "name": "Acorn Archimedes"},
    UPS.ACORN_ELECTRON: {"id": 65, "name": "Acorn Electron"},
    UPS.ACPC: {"id": 3, "name": "Amstrad CPC"},
    UPS.ACTION_MAX: {"id": 154, "name": "WoW Action Max"},
    UPS.ADVENTURE_VISION: {"id": 67, "name": "Entex Adventure Vision"},
    UPS.AMIGA: {"id": 2, "name": "Commodore Amiga"},
    UPS.AMIGA_CD32: {"id": 119, "name": "Commodore Amiga CD32"},
    UPS.AMSTRAD_GX4000: {"id": 109, "name": "Amstrad GX4000"},
    UPS.ANDROID: {"id": 4, "name": "Android"},
    UPS.APPLEII: {"id": 110, "name": "Apple II"},
    UPS.APPLE_IIGS: {"id": 112, "name": "Apple IIGS"},
    UPS.ARCADE: {"id": 5, "name": "Arcade"},
    UPS.ARCADIA_2001: {"id": 79, "name": "Emerson Arcadia 2001"},
    UPS.ASTROCADE: {"id": 77, "name": "Bally Astrocade"},
    UPS.ATARI2600: {"id": 6, "name": "Atari 2600"},
    UPS.ATARI5200: {"id": 7, "name": "Atari 5200"},
    UPS.ATARI7800: {"id": 8, "name": "Atari 7800"},
    UPS.ATARI800: {"id": 102, "name": "Atari 800"},
    UPS.ATARI_JAGUAR_CD: {"id": 10, "name": "Atari Jaguar CD"},
    UPS.ATARI_ST: {"id": 76, "name": "Atari ST"},
    UPS.ATARI_XEGS: {"id": 12, "name": "Atari XEGS"},
    UPS.BBCMICRO: {"id": 59, "name": "BBC Microcomputer System"},
    UPS.C64: {"id": 14, "name": "Commodore 64"},
    UPS.CAMPUTERS_LYNX: {"id": 61, "name": "Camputers Lynx"},
    UPS.CASIO_LOOPY: {"id": 114, "name": "Casio Loopy"},
    UPS.CASIO_PV_1000: {"id": 115, "name": "Casio PV-1000"},
    UPS.COLECOVISION: {"id": 13, "name": "ColecoVision"},
    UPS.COMMODORE_CDTV: {"id": 120, "name": "Commodore CDTV"},
    UPS.DOS: {"id": 16, "name": "DOS"},
    UPS.DC: {"id": 52, "name": "Sega Dreamcast"},
    UPS.FAIRCHILD_CHANNEL_F: {"id": 113, "name": "Fairchild Channel F"},
    UPS.FDS: {"id": 75, "name": "Nintendo Famicom Disk System"},
    UPS.GB: {"id": 17, "name": "Nintendo Game Boy"},
    UPS.GBA: {"id": 18, "name": "Nintendo Game Boy Advance"},
    UPS.GBC: {"id": 19, "name": "Nintendo Game Boy Color"},
    UPS.GAMEGEAR: {"id": 47, "name": "Sega Game Gear"},
    UPS.GENESIS: {"id": 49, "name": "Sega Genesis"},
    UPS.INTELLIVISION: {"id": 21, "name": "Mattel Intellivision"},
    UPS.JAGUAR: {"id": 9, "name": "Atari Jaguar"},
    UPS.LYNX: {"id": 11, "name": "Atari Lynx"},
    UPS.MSX: {"id": 22, "name": "Microsoft MSX"},
    UPS.MSX2: {"id": 23, "name": "Microsoft MSX2"},
    UPS.N64: {"id": 25, "name": "Nintendo 64"},
    UPS.NDS: {"id": 26, "name": "Nintendo DS"},
    UPS.NES: {"id": 27, "name": "Nintendo Entertainment System"},
    UPS.NGC: {"id": 20, "name": "Nintendo GameCube"},
    UPS.NEO_GEO_CD: {"id": 91, "name": "SNK Neo Geo CD"},
    UPS.NEO_GEO_POCKET: {"id": 92, "name": "SNK Neo Geo Pocket"},
    UPS.NEO_GEO_POCKET_COLOR: {"id": 93, "name": "SNK Neo Geo Pocket Color"},
    UPS.NEOGEOAES: {"id": 54, "name": "SNK Neo Geo AES"},
    UPS.ODYSSEY_2: {"id": 81, "name": "Magnavox Odyssey 2"},
    UPS.PC_8800_SERIES: {"id": 94, "name": "NEC PC-8801"},
    UPS.PC_9800_SERIES: {"id": 95, "name": "NEC PC-9801"},
    UPS.PC_FX: {"id": 96, "name": "NEC PC-FX"},
    UPS.PSX: {"id": 55, "name": "Sony Playstation"},
    UPS.PS2: {"id": 56, "name": "Sony Playstation 2"},
    UPS.PS3: {"id": 57, "name": "Sony Playstation 3"},
    UPS.PSP: {"id": 58, "name": "Sony PSP"},
    UPS.PSVITA: {"id": 59, "name": "Sony Playstation Vita"},
    UPS.SATURN: {"id": 51, "name": "Sega Saturn"},
    UPS.SEGA32: {"id": 44, "name": "Sega 32X"},
    UPS.SEGACD: {"id": 45, "name": "Sega CD"},
    UPS.SG1000: {"id": 46, "name": "Sega SG-1000"},
    UPS.SMS: {"id": 48, "name": "Sega Master System"},
    UPS.SNES: {"id": 60, "name": "Super Nintendo Entertainment System"},
    UPS.SUPERGRAFX: {"id": 100, "name": "NEC SuperGrafx"},
    UPS.SWITCH: {"id": 61, "name": "Nintendo Switch"},
    UPS.TG16: {"id": 98, "name": "NEC TurboGrafx-16"},
    UPS.TURBOGRAFX_CD: {"id": 99, "name": "NEC TurboGrafx-CD"},
    UPS.VECTREX: {"id": 80, "name": "GCE Vectrex"},
    UPS.VIRTUALBOY: {"id": 28, "name": "Nintendo Virtual Boy"},
    UPS.WII: {"id": 29, "name": "Nintendo Wii"},
    UPS.WIIU: {"id": 30, "name": "Nintendo Wii U"},
    UPS.WONDERSWAN: {"id": 62, "name": "Bandai WonderSwan"},
    UPS.WONDERSWAN_COLOR: {"id": 63, "name": "Bandai WonderSwan Color"},
    UPS.XBOX: {"id": 31, "name": "Microsoft Xbox"},
    UPS.XBOX360: {"id": 32, "name": "Microsoft Xbox 360"},
    UPS.ZXS: {"id": 65, "name": "Sinclair ZX Spectrum"},
}
