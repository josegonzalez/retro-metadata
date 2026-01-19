"""Integration tests for metadata providers using shared fixture data."""

import json
import re
from pathlib import Path

import httpx
import pytest
import respx
from aioresponses import aioresponses

from retro_metadata.core.config import ProviderConfig
from retro_metadata.providers.igdb import IGDBProvider
from retro_metadata.providers.mobygames import MobyGamesProvider


def load_fixture(provider: str, filename: str) -> dict | list:
    """Load a fixture file from testdata/fixtures."""
    # Find the testdata directory by walking up
    current_dir = Path(__file__).parent
    while current_dir.name != "" and not (current_dir / "testdata").exists():
        current_dir = current_dir.parent

    fixture_path = current_dir / "testdata" / "fixtures" / provider / filename
    if not fixture_path.exists():
        pytest.skip(f"Fixture file not found: {fixture_path}")

    with open(fixture_path) as f:
        return json.load(f)


class TestIGDBProviderIntegration:
    """Integration tests for IGDB provider using mocked HTTP responses."""

    @pytest.fixture
    def igdb_config(self):
        """Create a test IGDB configuration."""
        return ProviderConfig(
            enabled=True,
            credentials={
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
            },
            timeout=30,
        )

    @pytest.fixture
    def oauth_response(self):
        """Return the OAuth token response."""
        return {
            "access_token": "test_token",
            "expires_in": 3600,
            "token_type": "bearer",
        }

    async def test_igdb_search(self, igdb_config, oauth_response):
        """Test IGDB search returns expected results."""
        search_response = load_fixture("igdb", "search_mario.json")

        with aioresponses() as mocked:
            # Mock OAuth token endpoint (use pattern to match URL with query params)
            mocked.post(
                re.compile(r"https://id\.twitch\.tv/oauth2/token.*"),
                payload=oauth_response,
            )

            # Mock IGDB search endpoint
            mocked.post(
                re.compile(r"https://api\.igdb\.com/v4/games.*"),
                payload=search_response,
            )

            provider = IGDBProvider(igdb_config)

            try:
                results = await provider.search("Super Mario", limit=10)

                assert len(results) > 0, "Expected results, got none"
                assert results[0].name == "Super Mario World"
                assert results[0].provider == "igdb"
                assert results[0].provider_id == 1074
            finally:
                await provider.close()

    async def test_igdb_get_by_id(self, igdb_config, oauth_response):
        """Test IGDB get_by_id returns expected game details."""
        game_response = load_fixture("igdb", "game_1074.json")

        with aioresponses() as mocked:
            # Mock OAuth token endpoint (use pattern to match URL with query params)
            mocked.post(
                re.compile(r"https://id\.twitch\.tv/oauth2/token.*"),
                payload=oauth_response,
            )

            # Mock IGDB games endpoint
            mocked.post(
                re.compile(r"https://api\.igdb\.com/v4/games.*"),
                payload=game_response,
            )

            provider = IGDBProvider(igdb_config)

            try:
                result = await provider.get_by_id(1074)

                assert result is not None, "Expected result, got None"
                assert result.name == "Super Mario World"
                assert result.summary is not None and len(result.summary) > 0

                # Verify metadata
                assert len(result.metadata.genres) > 0, "Expected genres"
                assert len(result.metadata.companies) > 0, "Expected companies"

                # Verify artwork
                assert result.artwork.cover_url != "", "Expected cover URL"
                assert len(result.artwork.screenshot_urls) > 0, "Expected screenshots"
            finally:
                await provider.close()


class TestMobyGamesProviderIntegration:
    """Integration tests for MobyGames provider using mocked HTTP responses."""

    @pytest.fixture
    def mobygames_config(self):
        """Create a test MobyGames configuration."""
        return ProviderConfig(
            enabled=True,
            credentials={
                "api_key": "test_api_key",
            },
            timeout=30,
        )

    @respx.mock
    async def test_mobygames_search(self, mobygames_config):
        """Test MobyGames search returns expected results."""
        search_response = load_fixture("mobygames", "search_zelda.json")

        # Mock MobyGames search endpoint using respx for httpx
        respx.get(re.compile(r"https://api\.mobygames\.com/v1/games.*")).mock(
            return_value=httpx.Response(200, json=search_response)
        )

        provider = MobyGamesProvider(mobygames_config)

        try:
            results = await provider.search("Legend of Zelda", limit=10)

            assert len(results) > 0, "Expected results, got none"
            assert results[0].name == "The Legend of Zelda: A Link to the Past"
            assert results[0].provider == "mobygames"
            assert results[0].provider_id == 564
        finally:
            await provider.close()


class TestProviderErrorHandling:
    """Test error handling across providers."""

    @pytest.fixture
    def igdb_config(self):
        """Create a test IGDB configuration."""
        return ProviderConfig(
            enabled=True,
            credentials={
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
            },
            timeout=30,
        )

    @pytest.fixture
    def mobygames_config(self):
        """Create a test MobyGames configuration."""
        return ProviderConfig(
            enabled=True,
            credentials={
                "api_key": "test_api_key",
            },
            timeout=30,
        )

    async def test_igdb_500_error(self, igdb_config):
        """Test IGDB provider handles server errors."""
        oauth_response = {
            "access_token": "test_token",
            "expires_in": 3600,
            "token_type": "bearer",
        }

        with aioresponses() as mocked:
            # Mock OAuth token endpoint
            mocked.post(
                re.compile(r"https://id\.twitch\.tv/oauth2/token.*"),
                payload=oauth_response,
            )

            # Mock IGDB endpoint with 500 error
            mocked.post(
                re.compile(r"https://api\.igdb\.com/v4/games.*"),
                status=500,
            )

            provider = IGDBProvider(igdb_config)

            try:
                with pytest.raises(Exception):  # noqa: B017
                    await provider.search("Test", limit=10)
            finally:
                await provider.close()

    @respx.mock
    async def test_mobygames_500_error(self, mobygames_config):
        """Test MobyGames provider handles server errors."""
        # Mock MobyGames endpoint with 500 error using respx for httpx
        respx.get(re.compile(r"https://api\.mobygames\.com/v1/games.*")).mock(
            return_value=httpx.Response(500)
        )

        provider = MobyGamesProvider(mobygames_config)

        try:
            with pytest.raises(Exception):  # noqa: B017
                await provider.search("Test", limit=10)
        finally:
            await provider.close()


class TestDisabledProvider:
    """Test disabled provider behavior."""

    async def test_disabled_mobygames_provider(self):
        """Test that disabled provider returns empty results."""
        config = ProviderConfig(
            enabled=False,
            credentials={
                "api_key": "test_api_key",
            },
            timeout=30,
        )

        provider = MobyGamesProvider(config)

        try:
            results = await provider.search("Test", limit=10)

            # Disabled provider should return empty list without making any requests
            assert results == [] or results is None
        finally:
            await provider.close()
