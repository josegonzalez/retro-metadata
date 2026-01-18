"""Game name matching utilities using Jaro-Winkler similarity.

This module provides functions for finding the best matching game name
from a list of candidates using string similarity algorithms.
"""

from __future__ import annotations

import re
from typing import Final

from strsimpy.jaro_winkler import JaroWinkler

from retro_metadata.core.normalization import normalize_search_term

# Create a single instance for reuse
_jarowinkler: Final = JaroWinkler()

# Default minimum similarity score for a match
DEFAULT_MIN_SIMILARITY: Final[float] = 0.75

# Pattern for splitting game names
SEARCH_TERM_SPLIT_PATTERN: Final = re.compile(r"[\:\-\/]")


def jaro_winkler_similarity(s1: str, s2: str) -> float:
    """Calculate the Jaro-Winkler similarity between two strings.

    Jaro-Winkler is particularly effective for short strings like game titles.
    It returns a value between 0 and 1, where 1 indicates an exact match.

    Args:
        s1: First string to compare
        s2: Second string to compare

    Returns:
        Similarity score between 0 and 1
    """
    return _jarowinkler.similarity(s1, s2)


def find_best_match(
    search_term: str,
    candidates: list[str],
    min_similarity_score: float = DEFAULT_MIN_SIMILARITY,
    split_candidate_name: bool = False,
    normalize: bool = True,
) -> tuple[str | None, float]:
    """Find the best matching name from a list of candidates.

    Uses Jaro-Winkler similarity to find the closest match to the search term.
    Both the search term and candidates are normalized before comparison.

    Args:
        search_term: The search term to match against
        candidates: List of candidate names to check
        min_similarity_score: Minimum similarity score to consider a match (default: 0.75)
        split_candidate_name: If True, also try matching against the last part of
            candidate names split by colons/dashes/slashes (default: False)
        normalize: Whether to normalize strings before comparison (default: True)

    Returns:
        Tuple of (best_match_name, similarity_score) or (None, 0.0) if no good match

    Examples:
        >>> find_best_match("Super Mario Bros", ["Super Mario Bros.", "Mario Kart"])
        ('Super Mario Bros.', 0.98)
        >>> find_best_match("Zelda", ["The Legend of Zelda", "Zelda II"])
        ('Zelda II', 0.92)
        >>> find_best_match("Unknown Game", ["Mario", "Zelda"])
        (None, 0.0)
    """
    if not candidates:
        return None, 0.0

    best_match: str | None = None
    best_score: float = 0.0

    # Normalize the search term once
    if normalize:
        search_term_normalized = normalize_search_term(search_term)
    else:
        search_term_normalized = search_term.lower().strip()

    for candidate in candidates:
        # Normalize the candidate name
        if normalize:
            candidate_normalized = normalize_search_term(candidate)
        else:
            candidate_normalized = candidate.lower().strip()

        # If split mode is enabled and candidate contains delimiters, try the last part
        if split_candidate_name and re.search(SEARCH_TERM_SPLIT_PATTERN, candidate):
            parts = SEARCH_TERM_SPLIT_PATTERN.split(candidate)
            if normalize:
                candidate_normalized = normalize_search_term(parts[-1])
            else:
                candidate_normalized = parts[-1].lower().strip()

        # Calculate similarity
        score = _jarowinkler.similarity(search_term_normalized, candidate_normalized)

        if score > best_score:
            best_score = score
            best_match = candidate

            # Early exit for perfect match
            if score == 1.0:
                break

    if best_score >= min_similarity_score:
        return best_match, best_score

    return None, 0.0


def find_all_matches(
    search_term: str,
    candidates: list[str],
    min_similarity_score: float = DEFAULT_MIN_SIMILARITY,
    normalize: bool = True,
    max_results: int = 10,
) -> list[tuple[str, float]]:
    """Find all matching names above the minimum similarity threshold.

    Unlike find_best_match, this returns all candidates that exceed the
    minimum similarity threshold, sorted by score in descending order.

    Args:
        search_term: The search term to match against
        candidates: List of candidate names to check
        min_similarity_score: Minimum similarity score to include in results
        normalize: Whether to normalize strings before comparison
        max_results: Maximum number of results to return

    Returns:
        List of (name, score) tuples sorted by score descending
    """
    if not candidates:
        return []

    # Normalize the search term once
    if normalize:
        search_term_normalized = normalize_search_term(search_term)
    else:
        search_term_normalized = search_term.lower().strip()

    matches: list[tuple[str, float]] = []

    for candidate in candidates:
        # Normalize the candidate name
        if normalize:
            candidate_normalized = normalize_search_term(candidate)
        else:
            candidate_normalized = candidate.lower().strip()

        # Calculate similarity
        score = _jarowinkler.similarity(search_term_normalized, candidate_normalized)

        if score >= min_similarity_score:
            matches.append((candidate, score))

    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches[:max_results]


def is_exact_match(s1: str, s2: str, normalize: bool = True) -> bool:
    """Check if two strings are an exact match after normalization.

    Args:
        s1: First string to compare
        s2: Second string to compare
        normalize: Whether to normalize strings before comparison

    Returns:
        True if the strings match exactly after normalization
    """
    if normalize:
        return normalize_search_term(s1) == normalize_search_term(s2)
    return s1.lower().strip() == s2.lower().strip()


def calculate_match_confidence(
    search_term: str,
    matched_name: str,
    normalize: bool = True,
) -> str:
    """Calculate a human-readable confidence level for a match.

    Args:
        search_term: The original search term
        matched_name: The matched game name
        normalize: Whether to normalize strings

    Returns:
        One of "exact", "high", "medium", "low", or "none"
    """
    if normalize:
        s1 = normalize_search_term(search_term)
        s2 = normalize_search_term(matched_name)
    else:
        s1 = search_term.lower().strip()
        s2 = matched_name.lower().strip()

    if s1 == s2:
        return "exact"

    score = _jarowinkler.similarity(s1, s2)

    if score >= 0.95:
        return "high"
    elif score >= 0.85:
        return "medium"
    elif score >= 0.75:
        return "low"
    else:
        return "none"
