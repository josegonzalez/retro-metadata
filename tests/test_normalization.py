"""Tests for the normalization module."""

import pytest

from retro_metadata.core.normalization import normalize_search_term
from tests.helpers.test_data_loader import pytest_generate_tests_from_data


class TestNormalizeSearchTerm:
    """Tests for normalize_search_term function using shared test data."""

    @pytest.mark.parametrize(
        "test_id, test_case",
        pytest_generate_tests_from_data("normalization", "normalize_search_term"),
    )
    def test_normalize_search_term(self, test_id, test_case):
        """Test normalizing search terms."""
        input_data = test_case["input"]
        name = input_data["name"]
        remove_articles = input_data.get("remove_articles", True)
        remove_punctuation = input_data.get("remove_punctuation", True)

        result = normalize_search_term(
            name,
            remove_articles=remove_articles,
            remove_punctuation=remove_punctuation,
        )

        # Handle different assertion types
        if "expected" in test_case:
            assert result == test_case["expected"], (
                f"Test {test_id}: expected '{test_case['expected']}', got '{result}'"
            )
        elif "expected_contains" in test_case:
            assert test_case["expected_contains"] in result, (
                f"Test {test_id}: expected '{test_case['expected_contains']}' in result, got '{result}'"
            )
        elif "expected_not_contains" in test_case:
            assert test_case["expected_not_contains"] not in result, (
                f"Test {test_id}: expected '{test_case['expected_not_contains']}' not in result, got '{result}'"
            )
