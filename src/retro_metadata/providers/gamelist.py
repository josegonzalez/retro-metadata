"""Gamelist.xml metadata provider implementation.

Gamelist.xml is the metadata format used by EmulationStation and ES-DE.
This provider reads from local gamelist.xml files.
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
from glob import glob
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final
from xml.etree import ElementTree as ET

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

# Regex to detect Gamelist ID tags (UUID format typically)
GAMELIST_TAG_REGEX: Final = re.compile(r"\(gamelist-([a-f0-9-]+)\)", re.IGNORECASE)

# Mapping of XML tags to media URL keys
XML_TAG_MAP: Final = {
    "image_url": "image",
    "box2d_url": "cover",
    "box2d_back_url": "backcover",
    "box3d_url": "box3d",
    "fanart_url": "fanart",
    "manual_url": "manual",
    "marquee_url": "marquee",
    "miximage_url": "miximage",
    "physical_url": "physicalmedia",
    "screenshot_url": "screenshot",
    "title_screen_url": "title_screen",
    "thumbnail_url": "thumbnail",
    "video_url": "video",
}

# ES-DE media folder mapping
ESDE_MEDIA_MAP: Final = {
    "image_url": "images",
    "box2d_url": "covers",
    "box2d_back_url": "backcovers",
    "box3d_url": "3dboxes",
    "fanart_url": "fanart",
    "manual_url": "manuals",
    "marquee_url": "marquees",
    "miximage_url": "miximages",
    "physical_url": "physicalmedia",
    "screenshot_url": "screenshots",
    "title_screen_url": "titlescreens",
    "thumbnail_url": "thumbnails",
    "video_url": "videos",
}


class GamelistProvider(MetadataProvider):
    """Gamelist.xml metadata provider.

    Reads metadata from EmulationStation/ES-DE gamelist.xml files.

    Example:
        config = ProviderConfig(
            enabled=True,
            settings={"roms_path": "/path/to/roms"}
        )
        provider = GamelistProvider(config)
        await provider.load_gamelist("/path/to/roms/snes/gamelist.xml")
        result = await provider.identify("Super Mario World.sfc")
    """

    name = "gamelist"

    def __init__(
        self,
        config: ProviderConfig,
        cache: CacheBackend | None = None,
        roms_path: str | Path | None = None,
    ) -> None:
        super().__init__(config, cache)
        self._roms_path = Path(roms_path) if roms_path else None
        self._min_similarity_score = 0.6

        # In-memory cache
        self._games_by_filename: dict[str, dict[str, Any]] = {}
        self._games_by_path: dict[str, dict[str, Any]] = {}
        self._platform_dir: str = ""
        self._loaded = False

    async def load_gamelist(
        self,
        gamelist_path: str | Path,
        platform_dir: str | Path | None = None,
    ) -> bool:
        """Load games from a gamelist.xml file.

        Args:
            gamelist_path: Path to gamelist.xml
            platform_dir: Base directory for the platform (for resolving relative paths)

        Returns:
            True if loaded successfully
        """
        path = Path(gamelist_path)
        if not path.exists():
            return False

        if platform_dir:
            self._platform_dir = str(platform_dir)
        else:
            self._platform_dir = str(path.parent)

        try:
            tree = ET.parse(path)
            root = tree.getroot()

            if root is None:
                return False

            for game_elem in root.findall("game"):
                game = self._parse_game_element(game_elem)
                if game:
                    # Index by filename
                    path_elem = game.get("path", "")
                    if path_elem:
                        filename = os.path.basename(path_elem)
                        self._games_by_filename[filename] = game
                        self._games_by_path[path_elem] = game

            self._loaded = True
            return True
        except ET.ParseError:
            return False

    def _parse_game_element(self, elem: ET.Element) -> dict[str, Any]:
        """Parse a game XML element into a dictionary."""
        game: dict[str, Any] = {}

        # Core fields
        for tag in [
            "path",
            "name",
            "desc",
            "rating",
            "releasedate",
            "developer",
            "publisher",
            "genre",
            "players",
            "md5",
            "lang",
            "region",
            "family",
        ]:
            child = elem.find(tag)
            if child is not None and child.text:
                game[tag] = child.text

        # Media fields
        for media_key, xml_tag in XML_TAG_MAP.items():
            child = elem.find(xml_tag)
            if child is not None and child.text:
                game[media_key] = self._resolve_path(child.text)

        # Try to find media in ES-DE folder structure if not in XML
        rom_path = game.get("path", "")
        if rom_path:
            rom_stem = os.path.splitext(os.path.basename(rom_path))[0]
            for media_key, folder_name in ESDE_MEDIA_MAP.items():
                if media_key not in game:
                    media_path = self._find_media_file(rom_stem, folder_name)
                    if media_path:
                        game[media_key] = media_path

        return game

    def _resolve_path(self, path: str) -> str:
        """Resolve a relative path from gamelist to absolute/file URI."""
        if path.startswith("./"):
            path = path[2:]

        if self._platform_dir:
            full_path = os.path.join(self._platform_dir, path)
            if os.path.exists(full_path):
                return f"file://{os.path.abspath(full_path)}"

        return path

    def _find_media_file(self, rom_stem: str, folder_name: str) -> str:
        """Find media file for a ROM in ES-DE folder structure."""
        if not self._platform_dir:
            return ""

        search_pattern = os.path.join(self._platform_dir, folder_name, f"{rom_stem}.*")
        found_files = glob(search_pattern)
        if found_files:
            return f"file://{os.path.abspath(found_files[0])}"
        return ""

    async def search(
        self,
        query: str,
        platform_id: int | None = None,  # noqa: ARG002
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search for games by name.

        Args:
            query: Search query string
            platform_id: Not used for gamelist
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if not self.is_enabled:
            return []

        if not self._loaded:
            return []

        query_lower = query.lower()
        results = []

        for filename, game in self._games_by_filename.items():
            name = game.get("name", "")
            if query_lower in name.lower() or query_lower in filename.lower():
                cover_url = game.get("box2d_url", "") or game.get("image_url", "")

                results.append(
                    SearchResult(
                        name=name,
                        provider=self.name,
                        provider_id=hash(filename) & 0xFFFFFFFF,  # Generate numeric ID
                        cover_url=cover_url,
                        platforms=[],
                    )
                )

                if len(results) >= limit:
                    break

        return results

    async def get_by_id(self, game_id: int) -> GameResult | None:
        """Get game details by ID.

        Note: Gamelist doesn't have persistent IDs. Use identify() instead.

        Args:
            game_id: Game ID (hash of filename)

        Returns:
            GameResult if found, None otherwise
        """
        if not self.is_enabled or not self._loaded:
            return None

        # Find by matching hash
        for filename, game in self._games_by_filename.items():
            if (hash(filename) & 0xFFFFFFFF) == game_id:
                return self._build_game_result(game, filename)

        return None

    async def identify(
        self,
        filename: str,
        platform_id: int | None = None,  # noqa: ARG002
    ) -> GameResult | None:
        """Identify a game from a ROM filename.

        Args:
            filename: ROM filename
            platform_id: Not used for gamelist

        Returns:
            GameResult if a match is found, None otherwise
        """
        if not self.is_enabled or not self._loaded:
            return None

        # Try exact match first
        if filename in self._games_by_filename:
            game = self._games_by_filename[filename]
            return self._build_game_result(game, filename)

        # Try fuzzy match
        all_names = list(self._games_by_filename.keys())
        best_match, score = self.find_best_match(filename, all_names)

        if best_match and best_match in self._games_by_filename:
            game = self._games_by_filename[best_match]
            result = self._build_game_result(game, best_match)
            result.match_score = score
            return result

        return None

    def _build_game_result(self, game: dict[str, Any], filename: str) -> GameResult:
        """Build a GameResult from gamelist game data."""
        # Get artwork
        cover_url = game.get("box2d_url", "") or game.get("image_url", "")

        screenshot_urls = []
        for key in ["screenshot_url", "title_screen_url", "fanart_url"]:
            if game.get(key):
                screenshot_urls.append(game[key])

        # Extract metadata
        metadata = self._extract_metadata(game)

        return GameResult(
            name=game.get("name", ""),
            summary=game.get("desc", ""),
            provider=self.name,
            provider_id=hash(filename) & 0xFFFFFFFF,
            provider_ids={"gamelist": hash(filename) & 0xFFFFFFFF},
            artwork=Artwork(
                cover_url=cover_url,
                screenshot_urls=screenshot_urls,
                logo_url=game.get("marquee_url", ""),
            ),
            metadata=metadata,
            raw_response=game,
        )

    def _extract_metadata(self, game: dict[str, Any]) -> GameMetadata:
        """Extract GameMetadata from gamelist game data."""
        # Rating (gamelist uses 0-1 scale)
        total_rating = None
        rating = game.get("rating")
        if rating:
            with contextlib.suppress(ValueError):
                total_rating = float(rating) * 100

        # Release date
        first_release_date = None
        release_year = None
        releasedate = game.get("releasedate")
        if releasedate:
            try:
                # ES-DE uses YYYYMMDD format
                if len(releasedate) >= 8:
                    year = int(releasedate[:4])
                    release_year = year
            except (ValueError, IndexError):
                pass

        # Genres
        genres = []
        genre = game.get("genre")
        if genre:
            genres = [g.strip() for g in genre.split(",")]

        # Companies
        companies = []
        if game.get("developer"):
            companies.append(game["developer"])
        if game.get("publisher") and game["publisher"] not in companies:
            companies.append(game["publisher"])

        # Franchises
        franchises = []
        family = game.get("family")
        if family:
            franchises = [family]

        # Player count
        player_count = game.get("players", "1")

        return GameMetadata(
            total_rating=total_rating,
            first_release_date=first_release_date,
            genres=genres,
            franchises=franchises,
            companies=list(dict.fromkeys(companies)),
            player_count=str(player_count),
            developer=game.get("developer", ""),
            publisher=game.get("publisher", ""),
            release_year=release_year,
            raw_data=game,
        )

    def clear_cache(self) -> None:
        """Clear the loaded gamelist data."""
        self._games_by_filename.clear()
        self._games_by_path.clear()
        self._platform_dir = ""
        self._loaded = False

    async def close(self) -> None:
        """Clear loaded data."""
        self.clear_cache()
