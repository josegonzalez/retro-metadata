"""Custom exceptions for the retro-metadata library."""

from __future__ import annotations


class MetadataError(Exception):
    """Base exception for all metadata-related errors."""

    def __init__(self, message: str, provider: str | None = None) -> None:
        self.provider = provider
        super().__init__(message)


class ProviderNotFoundError(MetadataError):
    """Raised when a requested provider is not found or not configured."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"Provider '{provider}' is not found or not configured", provider)


class ProviderAuthenticationError(MetadataError):
    """Raised when provider authentication fails."""

    def __init__(self, provider: str, details: str | None = None) -> None:
        message = f"Authentication failed for provider '{provider}'"
        if details:
            message += f": {details}"
        super().__init__(message, provider)


class ProviderConnectionError(MetadataError):
    """Raised when connection to a provider fails."""

    def __init__(self, provider: str, details: str | None = None) -> None:
        message = f"Connection failed for provider '{provider}'"
        if details:
            message += f": {details}"
        super().__init__(message, provider)


class ProviderRateLimitError(MetadataError):
    """Raised when a provider rate limit is exceeded."""

    def __init__(
        self, provider: str, retry_after: int | None = None, details: str | None = None
    ) -> None:
        self.retry_after = retry_after
        message = f"Rate limit exceeded for provider '{provider}'"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        if details:
            message += f": {details}"
        super().__init__(message, provider)


class GameNotFoundError(MetadataError):
    """Raised when a game is not found in any provider."""

    def __init__(self, search_term: str, provider: str | None = None) -> None:
        message = f"Game not found: '{search_term}'"
        if provider:
            message += f" in provider '{provider}'"
        super().__init__(message, provider)


class InvalidConfigurationError(MetadataError):
    """Raised when configuration is invalid."""

    def __init__(self, details: str) -> None:
        super().__init__(f"Invalid configuration: {details}")


class CacheError(MetadataError):
    """Raised when a cache operation fails."""

    def __init__(self, operation: str, details: str | None = None) -> None:
        message = f"Cache {operation} failed"
        if details:
            message += f": {details}"
        super().__init__(message)
