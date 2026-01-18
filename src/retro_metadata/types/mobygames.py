"""MobyGames-specific type definitions.

Based on the MobyGames API: https://www.mobygames.com/info/api/
"""

from __future__ import annotations

from typing import Literal, TypedDict

MobyOutputFormat = Literal["id", "brief", "normal"]


class MobyGameAlternateTitle(TypedDict):
    """MobyGames alternate title."""

    description: str
    title: str


class MobyGenre(TypedDict):
    """MobyGames genre."""

    genre_category: str
    genre_category_id: int
    genre_id: int
    genre_name: str


class MobyPlatform(TypedDict):
    """MobyGames platform."""

    first_release_date: str
    platform_id: int
    platform_name: str


class MobyGameCover(TypedDict):
    """MobyGames game cover."""

    height: int
    image: str
    platforms: list[str]
    thumbnail_image: str
    width: int


class MobyGameScreenshot(TypedDict):
    """MobyGames game screenshot."""

    caption: str
    height: int
    image: str
    thumbnail_image: str
    width: int


class MobyGameBrief(TypedDict):
    """MobyGames game in brief format."""

    game_id: int
    moby_url: str
    title: str


class MobyGame(TypedDict):
    """MobyGames game in full format."""

    alternate_titles: list[MobyGameAlternateTitle]
    description: str
    game_id: int
    genres: list[MobyGenre]
    moby_score: float
    moby_url: str
    num_votes: int
    official_url: str | None
    platforms: list[MobyPlatform]
    sample_cover: MobyGameCover
    sample_screenshots: list[MobyGameScreenshot]
    title: str


class MobyGroup(TypedDict):
    """MobyGames group/series."""

    group_id: int
    group_description: str
    group_name: str
