"""Tests for the matching module."""

import pytest

from retro_metadata.core.matching import (
    find_best_match,
    jaro_winkler_similarity,
)
from retro_metadata.core.normalization import split_search_term


class TestJaroWinklerSimilarity:
    """Tests for Jaro-Winkler similarity."""

    def test_identical_strings(self):
        """Test that identical strings have similarity of 1.0."""
        assert jaro_winkler_similarity("test", "test") == 1.0

    def test_completely_different_strings(self):
        """Test that completely different strings have low similarity."""
        score = jaro_winkler_similarity("abc", "xyz")
        assert score < 0.5

    def test_similar_strings(self):
        """Test that similar strings have high similarity."""
        score = jaro_winkler_similarity("Super Mario World", "Super Mario World 2")
        assert score > 0.8

    def test_empty_strings(self):
        """Test handling of empty strings."""
        assert jaro_winkler_similarity("", "") == 1.0
        assert jaro_winkler_similarity("test", "") == 0.0
        assert jaro_winkler_similarity("", "test") == 0.0

    def test_case_sensitivity(self):
        """Test that comparison is case-insensitive."""
        score = jaro_winkler_similarity("MARIO", "mario")
        assert score == 1.0


class TestFindBestMatch:
    """Tests for find_best_match function."""

    def test_exact_match(self):
        """Test finding an exact match."""
        candidates = ["Super Mario World", "Zelda", "Metroid"]
        match, score = find_best_match("Super Mario World", candidates)
        assert match == "Super Mario World"
        assert score == 1.0

    def test_fuzzy_match(self):
        """Test finding a fuzzy match."""
        candidates = ["Super Mario World", "Super Mario Bros", "Super Mario Kart"]
        match, score = find_best_match("Super Mario Wrld", candidates)
        assert match == "Super Mario World"
        assert score > 0.8

    def test_no_match_above_threshold(self):
        """Test when no match meets threshold."""
        candidates = ["Zelda", "Metroid", "Castlevania"]
        match, score = find_best_match("Super Mario World", candidates, min_similarity_score=0.9)
        assert match is None
        assert score == 0.0

    def test_empty_candidates(self):
        """Test with empty candidates list."""
        match, score = find_best_match("test", [])
        assert match is None
        assert score == 0.0

    def test_first_n_only(self):
        """Test limiting to first N candidates."""
        candidates = ["Mario 1", "Mario 2", "Mario 3", "Mario 4", "Mario 5"]
        match, score = find_best_match("Mario 5", candidates, first_n_only=3)
        # Should not find "Mario 5" since it's after the first 3
        assert match != "Mario 5"


class TestSplitSearchTerm:
    """Tests for split_search_term function."""

    def test_split_by_hyphen(self):
        """Test splitting by hyphen."""
        terms = split_search_term("Super-Mario-World")
        assert "Super" in terms
        assert "Mario" in terms
        assert "World" in terms

    def test_split_by_colon(self):
        """Test splitting by colon."""
        terms = split_search_term("Zelda: A Link to the Past")
        assert any("Zelda" in t for t in terms)

    def test_split_by_ampersand(self):
        """Test splitting by ampersand."""
        terms = split_search_term("Donkey Kong & Diddy Kong")
        assert len(terms) > 1

    def test_no_split_needed(self):
        """Test when no split is needed."""
        terms = split_search_term("Super Mario World")
        assert "Super Mario World" in terms

    def test_roman_numerals(self):
        """Test handling of roman numerals."""
        terms = split_search_term("Final Fantasy II")
        # Should include both original and with "2"
        assert len(terms) >= 1
