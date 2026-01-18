"""ScreenScraper-specific type definitions.

Based on the ScreenScraper API: https://api.screenscraper.fr/
"""

from __future__ import annotations

from typing import Literal, TypedDict


class SSText(TypedDict):
    """ScreenScraper simple text field."""

    text: str


class SSTextID(TypedDict):
    """ScreenScraper text field with ID."""

    id: str
    text: str


class SSRegionalText(TypedDict):
    """ScreenScraper regional text."""

    region: str
    text: str


class SSLanguageText(TypedDict):
    """ScreenScraper language-specific text."""

    langue: str
    text: str


class SSGameClassification(TypedDict):
    """ScreenScraper game classification."""

    type: str
    text: str


class SSGameDate(TypedDict):
    """ScreenScraper game release date."""

    region: str
    text: str


class SSGameGenre(TypedDict):
    """ScreenScraper game genre."""

    id: str
    nomcourt: str
    principale: str
    parentid: str
    noms: list[SSLanguageText]


class SSGameMode(TypedDict):
    """ScreenScraper game mode."""

    id: str
    nomcourt: str
    principale: str
    parentid: str
    noms: list[SSLanguageText]


class SSGameFranchise(TypedDict):
    """ScreenScraper game franchise/family."""

    id: str
    nomcourt: str
    principale: str
    parentid: str
    noms: list[SSLanguageText]


class SSGameMedia(TypedDict):
    """ScreenScraper game media (images, videos)."""

    type: str
    parent: str
    url: str
    region: str
    crc: str
    md5: str
    sha1: str
    size: str
    format: str


class SSGame(TypedDict):
    """ScreenScraper game entity."""

    id: int
    romid: str
    notgame: Literal["true", "false"]
    noms: list[SSRegionalText]
    cloneof: str
    systeme: SSTextID
    editeur: SSTextID
    developpeur: SSTextID
    joueurs: SSText
    note: SSText
    topstaff: str
    rotation: str
    synopsis: list[SSLanguageText]
    classifications: list[SSGameClassification]
    dates: list[SSGameDate]
    genres: list[SSGameGenre]
    modes: list[SSGameMode]
    familles: list[SSGameFranchise]
    medias: list[SSGameMedia]


class SSSystem(TypedDict):
    """ScreenScraper system/platform."""

    id: str
    text: str
    parentid: str
    type: str
    noms: list[SSLanguageText]


class SSUserInfo(TypedDict):
    """ScreenScraper user info from response."""

    id: str
    niveau: str
    contribution: str
    uploadsysteme: str
    uploadinfos: str
    romasso: str
    uploadmedia: str
    maxthreads: str
    maxdownloadspeed: str
    requeststoday: str
    requestskotoday: str
    maxrequestsperday: str
    maxrequestspermin: str
    maxrequestskoperday: str
    visites: str
    datedernierevisite: str
    favregion: str


class SSResponse(TypedDict):
    """ScreenScraper API response wrapper."""

    header: dict
    response: dict


class SSGameResponse(TypedDict):
    """ScreenScraper game info response."""

    serveurs: dict
    ssuser: SSUserInfo
    jeu: SSGame
