"""Test data loader for shared JSON test files."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# Root directory for test data
TESTDATA_DIR = Path(__file__).parent.parent.parent / "testdata"


class SharedTestDataLoader:
    """Loader for shared test data files.

    This class provides methods to load and access test data from JSON files
    that are shared between Python and Go implementations.

    Example:
        loader = SharedTestDataLoader("filename", "get_file_extension")
        for case in loader.test_cases:
            result = get_file_extension(case["input"])
            assert result == case["expected"]
    """

    def __init__(self, category: str, test_suite: str) -> None:
        """Initialize the test data loader.

        Args:
            category: The category directory (e.g., "filename", "matching")
            test_suite: The test suite name (e.g., "get_file_extension")
        """
        self.category = category
        self.test_suite = test_suite
        self._data: dict[str, Any] | None = None

    @property
    def data(self) -> dict[str, Any]:
        """Load and return the test data."""
        if self._data is None:
            self._data = self._load_data()
        return self._data

    def _load_data(self) -> dict[str, Any]:
        """Load test data from the JSON file."""
        file_path = TESTDATA_DIR / self.category / f"{self.test_suite}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Test data file not found: {file_path}")

        with open(file_path) as f:
            return json.load(f)

    @property
    def version(self) -> str:
        """Get the test data version."""
        return self.data["version"]

    @property
    def description(self) -> str:
        """Get the test suite description."""
        return self.data["description"]

    @property
    def test_cases(self) -> list[dict[str, Any]]:
        """Get all test cases."""
        return self.data["test_cases"]

    def get_test_cases(
        self,
        category: str | None = None,
        skip_python: bool = True,
    ) -> list[dict[str, Any]]:
        """Get test cases with optional filtering.

        Args:
            category: Filter by category (e.g., "basic", "edge_case")
            skip_python: If True, exclude tests marked to skip in Python

        Returns:
            List of test case dictionaries
        """
        cases = self.test_cases

        if category:
            cases = [c for c in cases if c.get("category") == category]

        if skip_python:
            cases = [c for c in cases if not c.get("skip", {}).get("python")]

        return cases

    def get_test_case(self, test_id: str) -> dict[str, Any] | None:
        """Get a specific test case by ID.

        Args:
            test_id: The unique test case ID

        Returns:
            The test case dictionary or None if not found
        """
        for case in self.test_cases:
            if case["id"] == test_id:
                return case
        return None

    def get_pytest_params(
        self,
        category: str | None = None,
        skip_python: bool = True,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Get test cases formatted for pytest.mark.parametrize.

        Args:
            category: Filter by category
            skip_python: If True, exclude tests marked to skip in Python

        Returns:
            List of (test_id, test_case) tuples for parametrize
        """
        cases = self.get_test_cases(category=category, skip_python=skip_python)
        return [(c["id"], c) for c in cases]


@lru_cache(maxsize=32)
def load_test_data(category: str, test_suite: str) -> SharedTestDataLoader:
    """Load test data with caching.

    Args:
        category: The category directory
        test_suite: The test suite name

    Returns:
        A SharedTestDataLoader instance
    """
    return SharedTestDataLoader(category, test_suite)


def pytest_generate_tests_from_data(
    category: str,
    test_suite: str,
    filter_category: str | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    """Generate pytest parameters from test data.

    This is a convenience function for use with pytest.mark.parametrize.

    Example:
        @pytest.mark.parametrize(
            "test_id, test_case",
            pytest_generate_tests_from_data("filename", "get_file_extension")
        )
        def test_get_file_extension(test_id, test_case):
            result = get_file_extension(test_case["input"])
            assert result == test_case["expected"]

    Args:
        category: The category directory
        test_suite: The test suite name
        filter_category: Optional category filter

    Returns:
        List of (test_id, test_case) tuples
    """
    loader = load_test_data(category, test_suite)
    return loader.get_pytest_params(category=filter_category)
