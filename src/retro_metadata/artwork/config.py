"""Configuration classes for artwork downloading."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


def _get_default_cache_dir() -> Path:
    """Get the default artwork cache directory."""
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        cache_dir = Path(xdg_cache) / "retro-metadata" / "artwork"
    elif os.name == "nt":
        cache_dir = Path(os.environ.get("LOCALAPPDATA", "~")) / "retro-metadata" / "artwork"
    else:
        cache_dir = Path.home() / ".cache" / "retro-metadata" / "artwork"
    return cache_dir.expanduser()


@dataclass
class ArtworkConfig:
    """Configuration for artwork downloading.

    Attributes:
        cache_dir: Directory for artwork cache. None uses default (~/.cache/retro-metadata/artwork)
        cache_enabled: Whether to use caching
        cache_ttl: Cache time-to-live in seconds (default: 30 days)
        max_width: Maximum image width (None = no limit)
        max_height: Maximum image height (None = no limit)
        filename_format: Output filename format ("extended" or "simple")
        artwork_types: List of artwork types to download
        timeout: HTTP request timeout in seconds
        max_concurrent: Maximum concurrent downloads
    """

    cache_dir: Path | None = None
    cache_enabled: bool = True
    cache_ttl: int = 2592000  # 30 days
    max_width: int | None = None
    max_height: int | None = None
    filename_format: Literal["extended", "simple"] = "extended"
    artwork_types: list[str] = field(default_factory=lambda: ["cover"])
    timeout: int = 30
    max_concurrent: int = 5

    def get_cache_dir(self) -> Path:
        """Get the resolved cache directory path."""
        if self.cache_dir is not None:
            return self.cache_dir
        return _get_default_cache_dir()

    def ensure_cache_dir(self) -> Path:
        """Ensure cache directory exists and return its path."""
        cache_dir = self.get_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir


# Valid artwork types
ARTWORK_TYPES = frozenset([
    "cover",
    "screenshots",
    "banner",
    "icon",
    "logo",
    "background",
])
