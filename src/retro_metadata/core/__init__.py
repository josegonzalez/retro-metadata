"""Core functionality for retro-metadata."""

from retro_metadata.core.client import MetadataClient
from retro_metadata.core.config import MetadataConfig, ProviderConfig
from retro_metadata.core.exceptions import (
    MetadataError,
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderNotFoundError,
    ProviderRateLimitError,
)
from retro_metadata.core.hashing import (
    FileHashes,
    calculate_crc32,
    calculate_hashes,
    calculate_md5,
    calculate_sha1,
)
from retro_metadata.core.matching import find_best_match
from retro_metadata.core.normalization import normalize_search_term

__all__ = [
    "MetadataClient",
    "MetadataConfig",
    "ProviderConfig",
    "MetadataError",
    "ProviderAuthenticationError",
    "ProviderConnectionError",
    "ProviderNotFoundError",
    "ProviderRateLimitError",
    "FileHashes",
    "calculate_hashes",
    "calculate_md5",
    "calculate_sha1",
    "calculate_crc32",
    "find_best_match",
    "normalize_search_term",
]
