"""HowLongToBeat-specific type definitions."""

from __future__ import annotations

from typing import TypedDict


class HLTBGame(TypedDict):
    """HowLongToBeat game."""

    game_id: int
    game_name: str
    game_name_date: int
    game_alias: str
    game_type: str
    game_image: str
    comp_lvl_combine: int
    comp_lvl_sp: int
    comp_lvl_co: int
    comp_lvl_mp: int
    comp_lvl_spd: int
    comp_main: int
    comp_plus: int
    comp_100: int
    comp_all: int
    comp_main_count: int
    comp_plus_count: int
    comp_100_count: int
    comp_all_count: int
    invested_co: int
    invested_mp: int
    invested_co_count: int
    invested_mp_count: int
    count_comp: int
    count_speedrun: int
    count_backlog: int
    count_review: int
    review_score: int
    count_playing: int
    count_retired: int
    profile_dev: str
    profile_popular: int
    profile_steam: int
    profile_platform: str
    release_world: int


class HLTBSearchResult(TypedDict):
    """HowLongToBeat search result."""

    color: str
    title: str
    category: str
    count: int
    pageCurrent: int
    pageTotal: int
    pageSize: int
    data: list[HLTBGame]
    userData: list
    displayModifier: str | None


class HLTBTimeToBeat(TypedDict):
    """HowLongToBeat time to beat data."""

    main_story: int | None
    main_extra: int | None
    completionist: int | None
    all_styles: int | None
    co_op: int | None
    multiplayer: int | None
