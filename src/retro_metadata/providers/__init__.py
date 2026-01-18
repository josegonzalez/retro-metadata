"""Metadata providers for retro-metadata."""

from retro_metadata.providers.base import MetadataProvider
from retro_metadata.providers.flashpoint import FlashpointProvider
from retro_metadata.providers.gamelist import GamelistProvider
from retro_metadata.providers.hasheous import HasheousProvider
from retro_metadata.providers.hltb import HLTBProvider
from retro_metadata.providers.igdb import IGDBProvider
from retro_metadata.providers.launchbox import LaunchBoxProvider
from retro_metadata.providers.mobygames import MobyGamesProvider
from retro_metadata.providers.playmatch import PlaymatchProvider
from retro_metadata.providers.retroachievements import RetroAchievementsProvider
from retro_metadata.providers.screenscraper import ScreenScraperProvider
from retro_metadata.providers.steamgriddb import SteamGridDBProvider
from retro_metadata.providers.thegamesdb import TheGamesDBProvider

__all__ = [
    "MetadataProvider",
    "FlashpointProvider",
    "GamelistProvider",
    "HasheousProvider",
    "HLTBProvider",
    "IGDBProvider",
    "LaunchBoxProvider",
    "MobyGamesProvider",
    "PlaymatchProvider",
    "RetroAchievementsProvider",
    "ScreenScraperProvider",
    "SteamGridDBProvider",
    "TheGamesDBProvider",
]

# Provider registry for easy lookup by name
PROVIDERS = {
    "flashpoint": FlashpointProvider,
    "gamelist": GamelistProvider,
    "hasheous": HasheousProvider,
    "hltb": HLTBProvider,
    "igdb": IGDBProvider,
    "launchbox": LaunchBoxProvider,
    "mobygames": MobyGamesProvider,
    "playmatch": PlaymatchProvider,
    "retroachievements": RetroAchievementsProvider,
    "screenscraper": ScreenScraperProvider,
    "steamgriddb": SteamGridDBProvider,
    "thegamesdb": TheGamesDBProvider,
}


def get_provider_class(name: str) -> type[MetadataProvider] | None:
    """Get a provider class by name.

    Args:
        name: Provider name (e.g., "igdb", "screenscraper")

    Returns:
        Provider class or None if not found
    """
    return PROVIDERS.get(name.lower())
