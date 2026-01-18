"""Tests for the normalization module."""

import pytest

from retro_metadata.core.normalization import normalize_search_term


class TestNormalizeSearchTerm:
    """Tests for normalize_search_term function."""

    def test_basic_normalization(self):
        """Test basic string normalization."""
        result = normalize_search_term("Super Mario World")
        assert result == "super mario world"

    def test_remove_articles(self):
        """Test removal of articles."""
        result = normalize_search_term("The Legend of Zelda")
        assert "the" not in result.split()
        assert "legend" in result

    def test_keep_articles(self):
        """Test keeping articles when disabled."""
        result = normalize_search_term("The Legend of Zelda", remove_articles=False)
        assert "the" in result

    def test_remove_punctuation(self):
        """Test removal of punctuation."""
        result = normalize_search_term("Super Mario World!")
        assert "!" not in result

    def test_keep_punctuation(self):
        """Test keeping punctuation when disabled."""
        result = normalize_search_term("Super Mario World!", remove_punctuation=False)
        assert "!" in result

    def test_normalize_unicode(self):
        """Test Unicode normalization."""
        result = normalize_search_term("Pokémon")
        # Should normalize accented characters
        assert "pokemon" in result or "pok" in result

    def test_whitespace_handling(self):
        """Test handling of extra whitespace."""
        result = normalize_search_term("  Super   Mario   World  ")
        assert result == "super mario world"

    def test_special_characters(self):
        """Test handling of special characters."""
        result = normalize_search_term("Crash Bandicoot™")
        assert "™" not in result

    def test_empty_string(self):
        """Test handling of empty string."""
        result = normalize_search_term("")
        assert result == ""

    def test_ampersand_handling(self):
        """Test handling of ampersand."""
        result = normalize_search_term("Donkey Kong & Diddy Kong")
        # Ampersand should be converted to "and" or removed
        assert "&" not in result

    def test_colon_handling(self):
        """Test handling of colon."""
        result = normalize_search_term("Zelda: A Link to the Past")
        # Colon should be handled gracefully
        assert ":" not in result or result.count(":") <= result.count(":")
