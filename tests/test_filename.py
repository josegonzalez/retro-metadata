"""Tests for the filename parsing utilities."""

import pytest

from retro_metadata.utils.filename import (
    clean_filename,
    extract_region,
    extract_tags,
    get_file_extension,
    is_bios_file,
    is_demo_file,
    is_unlicensed,
    parse_no_intro_filename,
)
from tests.helpers.test_data_loader import pytest_generate_tests_from_data


class TestGetFileExtension:
    """Tests for get_file_extension function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("filename", "get_file_extension"),
    )
    def test_get_file_extension(self, test_id, test_case):
        """Test getting file extension."""
        result = get_file_extension(test_case["input"])
        assert result == test_case["expected"], f"Test {test_id}: expected {test_case['expected']}, got {result}"


class TestExtractTags:
    """Tests for extract_tags function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("filename", "extract_tags"),
    )
    def test_extract_tags(self, test_id, test_case):
        """Test extracting tags from filenames."""
        result = extract_tags(test_case["input"])
        expected = test_case["expected"]

        # Check all expected tags are present
        for tag in expected:
            assert tag in result, f"Test {test_id}: expected tag '{tag}' not found in {result}"

        # Check count matches
        assert len(result) == len(expected), f"Test {test_id}: expected {len(expected)} tags, got {len(result)}"


class TestExtractRegion:
    """Tests for extract_region function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("filename", "extract_region"),
    )
    def test_extract_region(self, test_id, test_case):
        """Test extracting region codes from filenames."""
        result = extract_region(test_case["input"])
        expected = test_case["expected"]
        assert result == expected, f"Test {test_id}: expected {expected}, got {result}"


class TestCleanFilename:
    """Tests for clean_filename function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("filename", "clean_filename"),
    )
    def test_clean_filename(self, test_id, test_case):
        """Test cleaning filenames."""
        input_data = test_case["input"]
        filename = input_data["filename"]
        remove_extension = input_data.get("remove_extension", True)

        result = clean_filename(filename, remove_extension=remove_extension)
        expected = test_case["expected"]
        assert result == expected, f"Test {test_id}: expected '{expected}', got '{result}'"


class TestParseNoIntroFilename:
    """Tests for parse_no_intro_filename function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("filename", "parse_no_intro_filename"),
    )
    def test_parse_no_intro_filename(self, test_id, test_case):
        """Test parsing No-Intro filenames."""
        result = parse_no_intro_filename(test_case["input"])
        expected = test_case["expected"]

        # Check name
        assert result["name"] == expected["name"], f"Test {test_id}: name mismatch"

        # Check region
        assert result["region"] == expected["region"], f"Test {test_id}: region mismatch"

        # Check extension
        assert result["extension"] == expected["extension"], f"Test {test_id}: extension mismatch"

        # Check version (can be null)
        if expected["version"] is not None:
            assert result["version"] == expected["version"], f"Test {test_id}: version mismatch"

        # Check all expected tags are present
        for tag in expected["tags"]:
            assert tag in result["tags"], f"Test {test_id}: expected tag '{tag}' not found in {result['tags']}"


class TestIsBiosFile:
    """Tests for is_bios_file function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("filename", "is_bios_file"),
    )
    def test_is_bios_file(self, test_id, test_case):
        """Test detecting BIOS files."""
        result = is_bios_file(test_case["input"])
        expected = test_case["expected"]
        assert result == expected, f"Test {test_id}: expected {expected}, got {result}"


class TestIsDemoFile:
    """Tests for is_demo_file function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("filename", "is_demo_file"),
    )
    def test_is_demo_file(self, test_id, test_case):
        """Test detecting demo files."""
        result = is_demo_file(test_case["input"])
        expected = test_case["expected"]
        assert result == expected, f"Test {test_id}: expected {expected}, got {result}"


class TestIsUnlicensed:
    """Tests for is_unlicensed function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("filename", "is_unlicensed"),
    )
    def test_is_unlicensed(self, test_id, test_case):
        """Test detecting unlicensed files."""
        result = is_unlicensed(test_case["input"])
        expected = test_case["expected"]
        assert result == expected, f"Test {test_id}: expected {expected}, got {result}"
