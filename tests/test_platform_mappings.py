"""Tests for the platform mapping utilities."""

import pytest

from retro_metadata.platforms.mappings import (
    get_igdb_platform_id,
    get_mobygames_platform_id,
    get_platform_info,
    get_retroachievements_platform_id,
    get_screenscraper_platform_id,
)

from tests.helpers.test_data_loader import pytest_generate_tests_from_data


class TestGetIGDBPlatformID:
    """Tests for get_igdb_platform_id function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("platform", "get_igdb_platform_id"),
    )
    def test_get_igdb_platform_id(self, test_id, test_case):
        """Test getting IGDB platform ID."""
        result = get_igdb_platform_id(test_case["input"])
        expected = test_case["expected"]
        assert result == expected, f"Test {test_id}: expected {expected}, got {result}"


class TestGetMobyGamesPlatformID:
    """Tests for get_mobygames_platform_id function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("platform", "get_mobygames_platform_id"),
    )
    def test_get_mobygames_platform_id(self, test_id, test_case):
        """Test getting MobyGames platform ID."""
        result = get_mobygames_platform_id(test_case["input"])
        expected = test_case["expected"]
        assert result == expected, f"Test {test_id}: expected {expected}, got {result}"


class TestGetScreenScraperPlatformID:
    """Tests for get_screenscraper_platform_id function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("platform", "get_screenscraper_platform_id"),
    )
    def test_get_screenscraper_platform_id(self, test_id, test_case):
        """Test getting ScreenScraper platform ID."""
        result = get_screenscraper_platform_id(test_case["input"])
        expected = test_case["expected"]
        assert result == expected, f"Test {test_id}: expected {expected}, got {result}"


class TestGetRetroAchievementsPlatformID:
    """Tests for get_retroachievements_platform_id function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("platform", "get_retroachievements_platform_id"),
    )
    def test_get_retroachievements_platform_id(self, test_id, test_case):
        """Test getting RetroAchievements platform ID."""
        result = get_retroachievements_platform_id(test_case["input"])
        expected = test_case["expected"]
        assert result == expected, f"Test {test_id}: expected {expected}, got {result}"


class TestGetPlatformInfo:
    """Tests for get_platform_info function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("platform", "get_platform_info"),
    )
    def test_get_platform_info(self, test_id, test_case):
        """Test getting comprehensive platform info."""
        result = get_platform_info(test_case["input"])
        expected = test_case["expected"]

        if expected is None:
            assert result is None, f"Test {test_id}: expected None, got {result}"
        else:
            assert result is not None, f"Test {test_id}: expected PlatformInfo, got None"

            # Check slug
            assert result.slug == expected["slug"], (
                f"Test {test_id}: slug mismatch - expected {expected['slug']}, got {result.slug}"
            )

            # Check IGDB ID
            assert result.igdb_id == expected["igdb_id"], (
                f"Test {test_id}: igdb_id mismatch - expected {expected['igdb_id']}, got {result.igdb_id}"
            )

            # Check MobyGames ID
            assert result.mobygames_id == expected["mobygames_id"], (
                f"Test {test_id}: mobygames_id mismatch - expected {expected['mobygames_id']}, got {result.mobygames_id}"
            )

            # Check ScreenScraper ID
            assert result.screenscraper_id == expected["screenscraper_id"], (
                f"Test {test_id}: screenscraper_id mismatch - expected {expected['screenscraper_id']}, got {result.screenscraper_id}"
            )

            # Check RetroAchievements ID
            assert result.retroachievements_id == expected["retroachievements_id"], (
                f"Test {test_id}: retroachievements_id mismatch - expected {expected['retroachievements_id']}, got {result.retroachievements_id}"
            )
