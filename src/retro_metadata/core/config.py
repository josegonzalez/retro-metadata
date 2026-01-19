"""Configuration classes for the retro-metadata library."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderConfig:
    """Configuration for an individual metadata provider.

    Attributes:
        enabled: Whether this provider is enabled
        credentials: Provider-specific credentials (API keys, secrets, etc.)
        priority: Priority order for this provider (lower = higher priority)
        timeout: Request timeout in seconds
        rate_limit: Maximum requests per second (0 = unlimited)
        options: Additional provider-specific options
    """

    enabled: bool = False
    credentials: dict[str, str] = field(default_factory=dict)
    priority: int = 100
    timeout: int = 30
    rate_limit: float = 0.0
    options: dict[str, Any] = field(default_factory=dict)

    def get_credential(self, key: str, default: str = "") -> str:
        """Get a credential value by key."""
        return self.credentials.get(key, default)

    @property
    def is_configured(self) -> bool:
        """Check if the provider has credentials configured."""
        return self.enabled and bool(self.credentials)


@dataclass
class CacheConfig:
    """Configuration for the cache backend.

    Attributes:
        backend: Cache backend type ("memory", "redis", "sqlite")
        ttl: Default time-to-live for cache entries in seconds
        max_size: Maximum number of entries for memory cache
        connection_string: Connection string for redis/sqlite backends
        options: Additional backend-specific options
    """

    backend: str = "memory"
    ttl: int = 3600  # 1 hour default
    max_size: int = 10000
    connection_string: str = ""
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class MetadataConfig:
    """Main configuration for the MetadataClient.

    Attributes:
        igdb: IGDB provider configuration
        mobygames: MobyGames provider configuration
        screenscraper: ScreenScraper provider configuration
        retroachievements: RetroAchievements provider configuration
        steamgriddb: SteamGridDB provider configuration
        hltb: HowLongToBeat provider configuration
        launchbox: LaunchBox provider configuration
        hasheous: Hasheous provider configuration
        thegamesdb: TheGamesDB provider configuration
        flashpoint: Flashpoint provider configuration
        playmatch: Playmatch provider configuration
        gamelist: Gamelist.xml parser configuration
        cache: Cache configuration
        default_timeout: Default request timeout in seconds
        max_concurrent_requests: Maximum concurrent requests across all providers
        user_agent: User agent string for HTTP requests
        preferred_locale: Preferred locale for localized content (e.g., "ja-JP")
        region_priority: List of region codes in priority order
    """

    igdb: ProviderConfig = field(default_factory=ProviderConfig)
    mobygames: ProviderConfig = field(default_factory=ProviderConfig)
    screenscraper: ProviderConfig = field(default_factory=ProviderConfig)
    retroachievements: ProviderConfig = field(default_factory=ProviderConfig)
    steamgriddb: ProviderConfig = field(default_factory=ProviderConfig)
    hltb: ProviderConfig = field(default_factory=ProviderConfig)
    launchbox: ProviderConfig = field(default_factory=ProviderConfig)
    hasheous: ProviderConfig = field(default_factory=ProviderConfig)
    thegamesdb: ProviderConfig = field(default_factory=ProviderConfig)
    flashpoint: ProviderConfig = field(default_factory=ProviderConfig)
    playmatch: ProviderConfig = field(default_factory=ProviderConfig)
    gamelist: ProviderConfig = field(default_factory=ProviderConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    default_timeout: int = 30
    max_concurrent_requests: int = 10
    user_agent: str = "retro-metadata/1.0"
    preferred_locale: str | None = None
    region_priority: list[str] = field(default_factory=lambda: ["us", "wor", "eu", "jp"])

    def get_enabled_providers(self) -> list[str]:
        """Get a list of enabled provider names sorted by priority."""
        providers = []
        provider_configs = {
            "igdb": self.igdb,
            "mobygames": self.mobygames,
            "screenscraper": self.screenscraper,
            "retroachievements": self.retroachievements,
            "steamgriddb": self.steamgriddb,
            "hltb": self.hltb,
            "launchbox": self.launchbox,
            "hasheous": self.hasheous,
            "thegamesdb": self.thegamesdb,
            "flashpoint": self.flashpoint,
            "playmatch": self.playmatch,
            "gamelist": self.gamelist,
        }

        for name, config in provider_configs.items():
            if config.enabled:
                providers.append((name, config.priority))

        # Sort by priority (lower = higher priority)
        providers.sort(key=lambda x: x[1])
        return [name for name, _ in providers]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetadataConfig:
        """Create a MetadataConfig from a dictionary."""
        provider_fields = [
            "igdb",
            "mobygames",
            "screenscraper",
            "retroachievements",
            "steamgriddb",
            "hltb",
            "launchbox",
            "hasheous",
            "thegamesdb",
            "flashpoint",
            "playmatch",
            "gamelist",
        ]

        kwargs: dict[str, Any] = {}

        for field_name in provider_fields:
            if field_name in data:
                kwargs[field_name] = ProviderConfig(**data[field_name])

        if "cache" in data:
            kwargs["cache"] = CacheConfig(**data["cache"])

        # Copy simple fields
        for key in [
            "default_timeout",
            "max_concurrent_requests",
            "user_agent",
            "preferred_locale",
            "region_priority",
        ]:
            if key in data:
                kwargs[key] = data[key]

        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration to a dictionary."""
        from dataclasses import asdict

        return asdict(self)
