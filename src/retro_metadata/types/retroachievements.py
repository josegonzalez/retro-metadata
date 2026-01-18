"""RetroAchievements-specific type definitions.

Based on the RetroAchievements API: https://api-docs.retroachievements.org/
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from typing import NotRequired, TypedDict


class PaginatedResponse[T: Mapping](TypedDict):
    """Generic paginated response."""

    Count: int
    Total: int
    Results: list[T]


class RAGameAchievementType(enum.StrEnum):
    """RetroAchievements achievement type."""

    PROGRESSION = "progression"
    WIN_CONDITION = "win_condition"
    MISSABLE = "missable"


class RAGameReleasedAtGranularity(enum.StrEnum):
    """RetroAchievements release date granularity."""

    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class RAUserCompletionProgressKind(enum.StrEnum):
    """RetroAchievements user completion progress kind."""

    COMPLETED = "completed"
    MASTERED = "mastered"
    BEATEN_HARDCORE = "beaten-hardcore"
    BEATEN_SOFTCORE = "beaten-softcore"


class RAGameExtendedDetailsAchievement(TypedDict):
    """RetroAchievements achievement in extended game details."""

    ID: int
    NumAwarded: int
    NumAwardedHardcore: int
    Title: str
    Description: str
    Points: int
    TrueRatio: int
    Author: str
    AuthorULID: str
    DateModified: str
    DateCreated: str
    BadgeName: str
    DisplayOrder: int
    MemAddr: str
    type: RAGameAchievementType | None


class RAGameExtendedDetails(TypedDict):
    """RetroAchievements extended game details."""

    ID: int
    Title: str
    ConsoleID: int
    ForumTopicID: int | None
    ImageIcon: str
    ImageTitle: str
    ImageIngame: str
    ImageBoxArt: str
    Publisher: str
    Developer: str
    Genre: str
    Released: str
    ReleasedAtGranularity: RAGameReleasedAtGranularity
    RichPresencePatch: str
    GuideURL: str | None
    Updated: str
    ConsoleName: str
    ParentGameID: int | None
    NumDistinctPlayers: int
    NumAchievements: int
    Achievements: dict[str, RAGameExtendedDetailsAchievement]
    NumDistinctPlayersCasual: int
    NumDistinctPlayersHardcore: int


class RAUserCompletionProgressResult(TypedDict):
    """RetroAchievements user completion progress result."""

    GameID: int
    Title: str
    ImageIcon: str
    ConsoleID: int
    ConsoleName: str
    MaxPossible: int
    NumAwarded: int
    NumAwardedHardcore: int
    MostRecentAwardedDate: str
    HighestAwardKind: RAUserCompletionProgressKind
    HighestAwardDate: str


RAUserCompletionProgress = PaginatedResponse[RAUserCompletionProgressResult]


class RAGameInfoAndUserProgressAchievement(TypedDict):
    """RetroAchievements achievement with user progress."""

    ID: int
    NumAwarded: int
    NumAwardedHardcore: int
    Title: str
    Description: str
    Points: int
    TrueRatio: int
    Author: str
    AuthorULID: str
    DateModified: str
    DateCreated: str
    BadgeName: str
    DisplayOrder: int
    MemAddr: str
    type: RAGameAchievementType | None
    DateEarnedHardcore: NotRequired[str]
    DateEarned: NotRequired[str]


class RAGameInfoAndUserProgress(TypedDict):
    """RetroAchievements game info with user progress."""

    ID: int
    Title: str
    ConsoleID: int
    ForumTopicID: int | None
    ImageIcon: str
    ImageTitle: str
    ImageIngame: str
    ImageBoxArt: str
    Publisher: str
    Developer: str
    Genre: str
    Released: str
    ReleasedAtGranularity: RAGameReleasedAtGranularity
    RichPresencePatch: str
    GuideURL: str | None
    ConsoleName: str
    ParentGameID: int | None
    NumDistinctPlayers: int
    NumAchievements: int
    Achievements: dict[str, RAGameInfoAndUserProgressAchievement]
    NumAwardedToUser: int
    NumAwardedToUserHardcore: int
    NumDistinctPlayersCasual: int
    NumDistinctPlayersHardcore: int
    UserCompletion: str
    UserCompletionHardcore: str
    HighestAwardKind: NotRequired[RAUserCompletionProgressKind]
    HighestAwardDate: NotRequired[str]


class RAGameListItem(TypedDict):
    """RetroAchievements game list item."""

    Title: str
    ID: int
    ConsoleID: int
    ConsoleName: str
    ImageIcon: str
    NumAchievements: int
    NumLeaderboards: int
    Points: int
    DateModified: str
    ForumTopicID: int | None
    Hashes: NotRequired[list[str]]


class RAConsole(TypedDict):
    """RetroAchievements console/system."""

    ID: int
    Name: str
    IconURL: str
    Active: bool
    IsGameSystem: bool
