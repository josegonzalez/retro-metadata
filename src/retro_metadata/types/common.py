"""Common type definitions used across the retro-metadata library.

These types provide a unified representation of game metadata that can be
populated from any provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Platform:
    """Represents a gaming platform.

    Attributes:
        slug: Universal platform slug (e.g., "snes", "ps2")
        name: Human-readable platform name
        provider_ids: Provider-specific IDs for this platform
    """

    slug: str
    name: str = ""
    provider_ids: dict[str, int] = field(default_factory=dict)


@dataclass
class AgeRating:
    """Represents an age rating for a game.

    Attributes:
        rating: The rating value (e.g., "E", "T", "M", "PEGI 12")
        category: Rating system (e.g., "ESRB", "PEGI", "CERO")
        cover_url: URL to the rating icon/image
    """

    rating: str
    category: str
    cover_url: str = ""


@dataclass
class MultiplayerMode:
    """Represents multiplayer capabilities for a game on a specific platform.

    Attributes:
        platform: The platform this multiplayer info applies to
        campaign_coop: Supports campaign co-op
        drop_in: Supports drop-in multiplayer
        lan_coop: Supports LAN co-op
        offline_coop: Supports offline co-op
        offline_coop_max: Maximum offline co-op players
        offline_max: Maximum offline players
        online_coop: Supports online co-op
        online_coop_max: Maximum online co-op players
        online_max: Maximum online players
        split_screen: Supports split-screen
        split_screen_online: Supports split-screen online
    """

    platform: Platform | None = None
    campaign_coop: bool = False
    drop_in: bool = False
    lan_coop: bool = False
    offline_coop: bool = False
    offline_coop_max: int = 0
    offline_max: int = 0
    online_coop: bool = False
    online_coop_max: int = 0
    online_max: int = 0
    split_screen: bool = False
    split_screen_online: bool = False


@dataclass
class RelatedGame:
    """Represents a related game (DLC, expansion, remake, etc.).

    Attributes:
        id: Provider-specific ID
        name: Game name
        slug: URL-friendly slug
        relation_type: Type of relation (expansion, dlc, remaster, remake, port, similar)
        cover_url: URL to cover art
        provider: Provider name this came from
    """

    id: int
    name: str
    slug: str = ""
    relation_type: str = ""
    cover_url: str = ""
    provider: str = ""


@dataclass
class Artwork:
    """Container for game artwork URLs.

    Attributes:
        cover_url: URL to the main cover art
        screenshot_urls: List of screenshot URLs
        banner_url: URL to a banner image
        icon_url: URL to an icon image
        logo_url: URL to the game logo
        background_url: URL to a background image
    """

    cover_url: str = ""
    screenshot_urls: list[str] = field(default_factory=list)
    banner_url: str = ""
    icon_url: str = ""
    logo_url: str = ""
    background_url: str = ""


@dataclass
class GameMetadata:
    """Extended metadata for a game.

    Attributes:
        total_rating: Aggregated user rating (0-100)
        aggregated_rating: Critic aggregated rating (0-100)
        first_release_date: First release timestamp
        youtube_video_id: YouTube video ID for trailer
        genres: List of genre names
        franchises: List of franchise names
        alternative_names: Alternative titles
        collections: Game collections/series
        companies: Companies involved (developers, publishers)
        game_modes: Game modes (single player, multiplayer, etc.)
        age_ratings: Age ratings across different systems
        platforms: Platforms the game is available on
        multiplayer_modes: Multiplayer capabilities per platform
        player_count: Human-readable player count string
        expansions: Related expansion games
        dlcs: Related DLC content
        remasters: Related remastered versions
        remakes: Related remakes
        expanded_games: Related expanded editions
        ports: Related ports to other platforms
        similar_games: Similar games
        developer: Primary developer name
        publisher: Primary publisher name
        release_year: Release year
        raw_data: Original provider-specific data
    """

    total_rating: float | None = None
    aggregated_rating: float | None = None
    first_release_date: int | None = None
    youtube_video_id: str | None = None
    genres: list[str] = field(default_factory=list)
    franchises: list[str] = field(default_factory=list)
    alternative_names: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    companies: list[str] = field(default_factory=list)
    game_modes: list[str] = field(default_factory=list)
    age_ratings: list[AgeRating] = field(default_factory=list)
    platforms: list[Platform] = field(default_factory=list)
    multiplayer_modes: list[MultiplayerMode] = field(default_factory=list)
    player_count: str = "1"
    expansions: list[RelatedGame] = field(default_factory=list)
    dlcs: list[RelatedGame] = field(default_factory=list)
    remasters: list[RelatedGame] = field(default_factory=list)
    remakes: list[RelatedGame] = field(default_factory=list)
    expanded_games: list[RelatedGame] = field(default_factory=list)
    ports: list[RelatedGame] = field(default_factory=list)
    similar_games: list[RelatedGame] = field(default_factory=list)
    developer: str = ""
    publisher: str = ""
    release_year: int | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameResult:
    """Represents a game result from metadata lookup.

    This is the main type returned by the MetadataClient for game lookups.

    Attributes:
        name: Game name
        summary: Game description/summary
        provider: Provider name this result came from
        provider_id: Provider-specific game ID
        provider_ids: Dictionary mapping provider names to IDs
        slug: URL-friendly slug
        artwork: Game artwork URLs
        metadata: Extended metadata
        match_score: Similarity score if result was from a search (0-1)
        raw_response: Raw provider response for debugging
    """

    name: str
    summary: str = ""
    provider: str = ""
    provider_id: int | None = None
    provider_ids: dict[str, int] = field(default_factory=dict)
    slug: str = ""
    artwork: Artwork = field(default_factory=Artwork)
    metadata: GameMetadata = field(default_factory=GameMetadata)
    match_score: float = 0.0
    match_type: str = ""  # hash+filename, hash, filename, filename_unique, filename_best
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def cover_url(self) -> str:
        """Convenience accessor for cover URL."""
        return self.artwork.cover_url

    @property
    def screenshot_urls(self) -> list[str]:
        """Convenience accessor for screenshot URLs."""
        return self.artwork.screenshot_urls

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        from dataclasses import asdict

        return asdict(self)


@dataclass
class SearchResult:
    """Represents a search result with minimal information.

    Used for displaying search results before fetching full details.

    Attributes:
        name: Game name
        provider: Provider name
        provider_id: Provider-specific ID
        slug: URL-friendly slug
        cover_url: URL to cover art thumbnail
        platforms: Platforms the game is available on
        release_year: Release year if known
        match_score: Similarity score (0-1)
    """

    name: str
    provider: str
    provider_id: int
    slug: str = ""
    cover_url: str = ""
    platforms: list[str] = field(default_factory=list)
    release_year: int | None = None
    match_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        from dataclasses import asdict

        return asdict(self)
