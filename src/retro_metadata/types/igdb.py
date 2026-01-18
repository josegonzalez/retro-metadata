"""IGDB-specific type definitions.

Based on the IGDB API documentation: https://api-docs.igdb.com/
"""

from __future__ import annotations

import enum
from typing import Literal, NewType, TypedDict, TypeGuard


# Type for expandable fields - can be an ID or the full object
type ExpandableField[T] = T | int


def mark_expanded[T](value: ExpandableField[T]) -> TypeGuard[T]:
    """Type guard to narrow an `ExpandableField` to its expanded type."""
    return True


def mark_list_expanded[T](value: list[ExpandableField[T]]) -> TypeGuard[list[T]]:
    """Type guard to narrow an `ExpandableField` list to its expanded type."""
    return True


# Placeholder for unimplemented entity types
UnimplementedEntity = NewType("UnimplementedEntity", dict)
AgeRatingContentDescription = UnimplementedEntity
Artwork = UnimplementedEntity
CollectionRelation = UnimplementedEntity
ExternalGame = UnimplementedEntity
GameEngine = UnimplementedEntity
GameMode = UnimplementedEntity
InvolvedCompany = UnimplementedEntity
Keyword = UnimplementedEntity
LanguageSupport = UnimplementedEntity
PlatformVersionReleaseDate = UnimplementedEntity
PlatformWebsite = UnimplementedEntity
PlayerPerspective = UnimplementedEntity
ReleaseDate = UnimplementedEntity
TagNumber = UnimplementedEntity
Theme = UnimplementedEntity
Website = UnimplementedEntity


class IGDBEntity(TypedDict):
    """Base class for all IGDB entities.

    All IGDB entities include an ID field.
    """

    id: int


class AgeRatingCategory(enum.IntEnum):
    """IGDB age rating categories."""

    ESRB = 1
    PEGI = 2
    CERO = 3
    USK = 4
    GRAC = 5
    CLASS_IND = 6
    ACB = 7


class AgeRatingRating(enum.IntEnum):
    """IGDB age rating values."""

    THREE = 1
    SEVEN = 2
    TWELVE = 3
    SIXTEEN = 4
    EIGHTEEN = 5
    RP = 6
    EC = 7
    E = 8
    E10 = 9
    T = 10
    M = 11
    AO = 12
    CERO_A = 13
    CERO_B = 14
    CERO_C = 15
    CERO_D = 16
    CERO_Z = 17
    USK_0 = 18
    USK_6 = 19
    USK_12 = 20
    USK_16 = 21
    USK_18 = 22
    GRAC_ALL = 23
    GRAC_TWELVE = 24
    GRAC_FIFTEEN = 25
    GRAC_EIGHTEEN = 26
    GRAC_TESTING = 27
    CLASS_IND_L = 28
    CLASS_IND_TEN = 29
    CLASS_IND_TWELVE = 30
    CLASS_IND_FOURTEEN = 31
    CLASS_IND_SIXTEEN = 32
    CLASS_IND_EIGHTEEN = 33
    ACB_G = 34
    ACB_PG = 35
    ACB_M = 36
    ACB_MA15 = 37
    ACB_R18 = 38
    ACB_RC = 39


class AgeRating(IGDBEntity, total=False):
    """IGDB age rating."""

    category: AgeRatingCategory
    checksum: str
    content_descriptions: list[ExpandableField[AgeRatingContentDescription]]
    rating_category: AgeRatingRating
    rating_cover_url: str
    synopsis: str


class AlternativeName(IGDBEntity, total=False):
    """IGDB alternative name."""

    checksum: str
    comment: str
    game: ExpandableField["Game"]
    name: str


class Collection(IGDBEntity, total=False):
    """IGDB collection (game series)."""

    as_child_relations: list[ExpandableField[CollectionRelation]]
    as_parent_relations: list[ExpandableField[CollectionRelation]]
    checksum: str
    created_at: int
    games: list[ExpandableField["Game"]]
    name: str
    slug: str
    type: ExpandableField["CollectionType"]
    updated_at: int
    url: str


class CollectionType(IGDBEntity, total=False):
    """IGDB collection type."""

    checksum: str
    created_at: int
    description: str
    name: str
    updated_at: int


class Company(IGDBEntity, total=False):
    """IGDB company."""

    change_date: int
    change_date_category: "CompanyChangeDateCategory"
    changed_company_id: ExpandableField["Company"]
    checksum: str
    country: int
    created_at: int
    description: str
    developed: list[ExpandableField["Game"]]
    logo: ExpandableField["CompanyLogo"]
    name: str
    parent: ExpandableField["Company"]
    published: list[ExpandableField["Game"]]
    slug: str
    start_date: int
    start_date_category: "CompanyStartDateCategory"
    updated_at: int
    url: str
    websites: list[ExpandableField["CompanyWebsite"]]


class CompanyChangeDateCategory(enum.IntEnum):
    """IGDB company change date category."""

    YYYYMMMMDD = 0
    YYYYMMMM = 1
    YYYY = 2
    YYYYQ1 = 3
    YYYYQ2 = 4
    YYYYQ3 = 5
    YYYYQ4 = 6
    TBD = 7


class CompanyLogo(IGDBEntity, total=False):
    """IGDB company logo."""

    alpha_channel: bool
    animated: bool
    checksum: str
    height: int
    image_id: str
    url: str
    width: int


class CompanyStartDateCategory(enum.IntEnum):
    """IGDB company start date category."""

    YYYYMMMMDD = 0
    YYYYMMMM = 1
    YYYY = 2
    YYYYQ1 = 3
    YYYYQ2 = 4
    YYYYQ3 = 5
    YYYYQ4 = 6
    TBD = 7


class CompanyWebsite(IGDBEntity, total=False):
    """IGDB company website."""

    category: "CompanyWebsiteCategory"
    checksum: str
    trusted: bool
    url: str


class CompanyWebsiteCategory(enum.IntEnum):
    """IGDB company website category."""

    OFFICIAL = 1
    WIKIA = 2
    WIKIPEDIA = 3
    FACEBOOK = 4
    TWITTER = 5
    TWITCH = 6
    INSTAGRAM = 8
    YOUTUBE = 9
    IPHONE = 10
    IPAD = 11
    ANDROID = 12
    STEAM = 13
    REDDIT = 14
    ITCH = 15
    EPICGAMES = 16
    GOG = 17
    DISCORD = 18


class Cover(IGDBEntity, total=False):
    """IGDB cover image."""

    alpha_channel: bool
    animated: bool
    checksum: str
    game: ExpandableField["Game"]
    game_localization: ExpandableField["GameLocalization"]
    height: int
    image_id: str
    url: str
    width: int


class Franchise(IGDBEntity, total=False):
    """IGDB franchise."""

    checksum: str
    created_at: int
    games: list[ExpandableField["Game"]]
    name: str
    slug: str
    updated_at: int
    url: str


class GameType(enum.IntEnum):
    """IGDB game type/category."""

    MAIN_GAME = 0
    DLC_ADDON = 1
    EXPANSION = 2
    BUNDLE = 3
    STANDALONE_EXPANSION = 4
    MOD = 5
    EPISODE = 6
    SEASON = 7
    REMAKE = 8
    REMASTER = 9
    EXPANDED_GAME = 10
    PORT = 11
    FORK = 12
    PACK = 13
    UPDATE = 14


class GameStatus(enum.IntEnum):
    """IGDB game status."""

    RELEASED = 0
    ALPHA = 2
    BETA = 3
    EARLY_ACCESS = 4
    OFFLINE = 5
    CANCELLED = 6
    RUMORED = 7
    DELISTED = 8


class Game(IGDBEntity, total=False):
    """IGDB game entity."""

    age_ratings: list[ExpandableField[AgeRating]]
    aggregated_rating: float
    aggregated_rating_count: int
    alternative_names: list[ExpandableField[AlternativeName]]
    artworks: list[ExpandableField[Artwork]]
    bundles: list[ExpandableField["Game"]]
    category: GameType
    checksum: str
    collections: list[ExpandableField[Collection]]
    cover: ExpandableField[Cover]
    created_at: int
    dlcs: list[ExpandableField["Game"]]
    expanded_games: list[ExpandableField["Game"]]
    expansions: list[ExpandableField["Game"]]
    external_games: list[ExpandableField[ExternalGame]]
    first_release_date: int
    forks: list[ExpandableField["Game"]]
    franchise: ExpandableField[Franchise]
    franchises: list[ExpandableField[Franchise]]
    game_engines: list[ExpandableField[GameEngine]]
    game_localizations: list[ExpandableField["GameLocalization"]]
    game_modes: list[ExpandableField[GameMode]]
    genres: list[ExpandableField["Genre"]]
    hypes: int
    involved_companies: list[ExpandableField[InvolvedCompany]]
    keywords: list[ExpandableField[Keyword]]
    language_supports: list[ExpandableField[LanguageSupport]]
    multiplayer_modes: list[ExpandableField["MultiplayerMode"]]
    name: str
    parent_game: ExpandableField["Game"]
    platforms: list[ExpandableField["Platform"]]
    player_perspectives: list[ExpandableField[PlayerPerspective]]
    ports: list[ExpandableField["Game"]]
    rating: float
    rating_count: int
    release_dates: list[ExpandableField[ReleaseDate]]
    remakes: list[ExpandableField["Game"]]
    remasters: list[ExpandableField["Game"]]
    screenshots: list[ExpandableField["Screenshot"]]
    similar_games: list[ExpandableField["Game"]]
    slug: str
    standalone_expansions: list[ExpandableField["Game"]]
    status: GameStatus
    storyline: str
    summary: str
    tags: list[TagNumber]
    themes: list[ExpandableField[Theme]]
    total_rating: float
    total_rating_count: int
    updated_at: int
    url: str
    version_parent: ExpandableField["Game"]
    version_title: str
    videos: list[ExpandableField["GameVideo"]]
    websites: list[ExpandableField[Website]]


class GameLocalization(IGDBEntity, total=False):
    """IGDB game localization."""

    checksum: str
    cover: ExpandableField[Cover]
    created_at: int
    game: ExpandableField[Game]
    name: str
    region: ExpandableField["Region"]
    updated_at: int


class GameTimeToBeat(IGDBEntity, total=False):
    """IGDB game time to beat."""

    checksum: str
    completely: int
    count: int
    created_at: int
    game_id: int
    hastily: int
    normally: int
    updated_at: int


class GameVideo(IGDBEntity, total=False):
    """IGDB game video."""

    checksum: str
    game: ExpandableField[Game]
    name: str
    video_id: str


class Genre(IGDBEntity, total=False):
    """IGDB genre."""

    checksum: str
    created_at: int
    name: str
    slug: str
    updated_at: int
    url: str


class MultiplayerMode(IGDBEntity, total=False):
    """IGDB multiplayer mode."""

    campaigncoop: bool
    checksum: str
    dropin: bool
    game: ExpandableField[Game]
    lancoop: bool
    offlinecoop: bool
    offlinecoopmax: int
    offlinemax: int
    onlinecoop: bool
    onlinecoopmax: int
    onlinemax: int
    platform: ExpandableField["Platform"]
    splitscreen: bool
    splitscreenonline: bool


class PlatformCategory(enum.IntEnum):
    """IGDB platform category."""

    CONSOLE = 1
    ARCADE = 2
    PLATFORM = 3
    OPERATING_SYSTEM = 4
    PORTABLE_CONSOLE = 5
    COMPUTER = 6


class Platform(IGDBEntity, total=False):
    """IGDB platform."""

    abbreviation: str
    alternative_name: str
    category: PlatformCategory
    checksum: str
    created_at: int
    generation: int
    name: str
    platform_family: ExpandableField["PlatformFamily"]
    platform_logo: ExpandableField["PlatformLogo"]
    slug: str
    summary: str
    updated_at: int
    url: str
    versions: list[ExpandableField["PlatformVersion"]]
    websites: list[ExpandableField[PlatformWebsite]]


class PlatformFamily(IGDBEntity, total=False):
    """IGDB platform family."""

    checksum: str
    name: str
    slug: str


class PlatformLogo(IGDBEntity, total=False):
    """IGDB platform logo."""

    alpha_channel: bool
    animated: bool
    checksum: str
    height: int
    image_id: str
    url: str
    width: int


class PlatformVersion(IGDBEntity, total=False):
    """IGDB platform version."""

    checksum: str
    companies: list[ExpandableField["PlatformVersionCompany"]]
    connectivity: str
    cpu: str
    graphics: str
    main_manufacturer: ExpandableField["PlatformVersionCompany"]
    media: str
    memory: str
    name: str
    os: str
    output: str
    platform_logo: ExpandableField[PlatformLogo]
    platform_version_release_dates: list[ExpandableField[PlatformVersionReleaseDate]]
    resolutions: str
    slug: str
    sound: str
    storage: str
    summary: str
    url: str


class PlatformVersionCompany(IGDBEntity, total=False):
    """IGDB platform version company."""

    checksum: str
    comment: str
    company: ExpandableField[Company]
    developer: bool
    manufacturer: bool


class Region(IGDBEntity, total=False):
    """IGDB region."""

    category: Literal["locale", "continent"]
    checksum: str
    created_at: int
    identifier: str
    name: str
    updated_at: int


class Screenshot(IGDBEntity, total=False):
    """IGDB screenshot."""

    alpha_channel: bool
    animated: bool
    checksum: str
    game: ExpandableField[Game]
    height: int
    image_id: str
    url: str
    width: int
