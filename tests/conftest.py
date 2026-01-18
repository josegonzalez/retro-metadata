"""Pytest configuration and fixtures."""

from __future__ import annotations

import pytest

from retro_metadata import CacheConfig, MetadataConfig, ProviderConfig


@pytest.fixture
def mock_config() -> MetadataConfig:
    """Create a mock configuration for testing."""
    return MetadataConfig(
        igdb=ProviderConfig(
            enabled=False,
            credentials={"client_id": "test", "client_secret": "test"},
        ),
        mobygames=ProviderConfig(
            enabled=False,
            credentials={"api_key": "test"},
        ),
        cache=CacheConfig(backend="memory", ttl=3600, max_size=100),
    )


@pytest.fixture
def enabled_config() -> MetadataConfig:
    """Create a configuration with mock-enabled providers."""
    return MetadataConfig(
        igdb=ProviderConfig(
            enabled=True,
            credentials={"client_id": "test", "client_secret": "test"},
        ),
        mobygames=ProviderConfig(
            enabled=True,
            credentials={"api_key": "test"},
        ),
        cache=CacheConfig(backend="memory", ttl=3600, max_size=100),
    )
