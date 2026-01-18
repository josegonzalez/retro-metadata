"""Custom exceptions for artwork downloading."""

from __future__ import annotations


class ArtworkError(Exception):
    """Base exception for all artwork-related errors."""

    def __init__(self, message: str, provider: str | None = None) -> None:
        self.provider = provider
        super().__init__(message)


class ArtworkDownloadError(ArtworkError):
    """Raised when artwork download fails."""

    def __init__(
        self,
        url: str,
        provider: str | None = None,
        details: str | None = None,
    ) -> None:
        self.url = url
        message = f"Failed to download artwork from '{url}'"
        if details:
            message += f": {details}"
        super().__init__(message, provider)


class ArtworkCacheError(ArtworkError):
    """Raised when a cache operation fails."""

    def __init__(self, operation: str, details: str | None = None) -> None:
        message = f"Artwork cache {operation} failed"
        if details:
            message += f": {details}"
        super().__init__(message)


class ArtworkNotFoundError(ArtworkError):
    """Raised when artwork is not found for a game."""

    def __init__(
        self,
        game_name: str,
        artwork_type: str,
        provider: str | None = None,
    ) -> None:
        self.game_name = game_name
        self.artwork_type = artwork_type
        message = f"No {artwork_type} artwork found for '{game_name}'"
        if provider:
            message += f" from provider '{provider}'"
        super().__init__(message, provider)


class InvalidArtworkTypeError(ArtworkError):
    """Raised when an invalid artwork type is specified."""

    def __init__(self, artwork_type: str, valid_types: list[str]) -> None:
        self.artwork_type = artwork_type
        self.valid_types = valid_types
        message = f"Invalid artwork type '{artwork_type}'. Valid types: {', '.join(valid_types)}"
        super().__init__(message)


class ArtworkTimeoutError(ArtworkError):
    """Raised when artwork download times out."""

    def __init__(self, url: str, timeout: int) -> None:
        self.url = url
        self.timeout = timeout
        message = f"Artwork download timed out after {timeout}s: '{url}'"
        super().__init__(message)
