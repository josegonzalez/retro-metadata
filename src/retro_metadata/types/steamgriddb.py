"""SteamGridDB-specific type definitions.

Based on the SteamGridDB API: https://www.steamgriddb.com/api/v2
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from typing import TypedDict


@enum.unique
class SGDBStyle(enum.StrEnum):
    """SteamGridDB grid style."""

    ALTERNATE = "alternate"
    BLURRED = "blurred"
    WHITE_LOGO = "white_logo"
    MATERIAL = "material"
    NO_LOGO = "no_logo"


@enum.unique
class SGDBDimension(enum.StrEnum):
    """SteamGridDB grid dimensions."""

    STEAM_HORIZONTAL = "460x215"
    STEAM_HORIZONTAL_2X = "920x430"
    STEAM_VERTICAL = "600x900"
    GOG_GALAXY_TILE = "342x482"
    GOG_GALAXY_COVER = "660x930"
    SQUARE_512 = "512x512"
    SQUARE_1024 = "1024x1024"


@enum.unique
class SGDBMime(enum.StrEnum):
    """SteamGridDB image mime types."""

    PNG = "image/png"
    JPEG = "image/jpeg"
    WEBP = "image/webp"


@enum.unique
class SGDBType(enum.StrEnum):
    """SteamGridDB image types."""

    STATIC = "static"
    ANIMATED = "animated"


@enum.unique
class SGDBTag(enum.StrEnum):
    """SteamGridDB content tags."""

    HUMOR = "humor"
    NSFW = "nsfw"
    EPILEPSY = "epilepsy"


class PaginatedResponse[T: Mapping](TypedDict):
    """SteamGridDB paginated response."""

    page: int
    total: int
    limit: int
    data: list[T]


class SGDBGridAuthor(TypedDict):
    """SteamGridDB grid author."""

    name: str
    steam64: str
    avatar: str


class SGDBGrid(TypedDict):
    """SteamGridDB grid image."""

    id: int
    score: int
    style: SGDBStyle
    url: str
    thumb: str
    tags: list[str]
    author: SGDBGridAuthor


class SGDBGame(TypedDict):
    """SteamGridDB game."""

    id: int
    name: str
    types: list[str]
    verified: bool


class SGDBHero(TypedDict):
    """SteamGridDB hero image."""

    id: int
    score: int
    style: SGDBStyle
    url: str
    thumb: str
    tags: list[str]
    author: SGDBGridAuthor
    width: int
    height: int
    notes: str | None


class SGDBLogo(TypedDict):
    """SteamGridDB logo image."""

    id: int
    score: int
    style: SGDBStyle
    url: str
    thumb: str
    tags: list[str]
    author: SGDBGridAuthor
    width: int
    height: int
    notes: str | None


class SGDBIcon(TypedDict):
    """SteamGridDB icon image."""

    id: int
    score: int
    style: SGDBStyle
    url: str
    thumb: str
    tags: list[str]
    author: SGDBGridAuthor
    width: int
    height: int
    notes: str | None


SGDBGridList = PaginatedResponse[SGDBGrid]
SGDBHeroList = PaginatedResponse[SGDBHero]
SGDBLogoList = PaginatedResponse[SGDBLogo]
SGDBIconList = PaginatedResponse[SGDBIcon]
