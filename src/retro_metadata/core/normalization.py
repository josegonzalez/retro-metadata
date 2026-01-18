"""Text normalization utilities for game name matching.

This module provides functions for normalizing game names and search terms
to improve matching accuracy across different naming conventions.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Final
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Pre-compiled regex patterns for performance
LEADING_ARTICLE_PATTERN: Final = re.compile(r"^(a|an|the)\b", re.IGNORECASE)
COMMA_ARTICLE_PATTERN: Final = re.compile(r",\s(a|an|the)\b(?=\s*[^\w\s]|$)", re.IGNORECASE)
NON_WORD_SPACE_PATTERN: Final = re.compile(r"[^\w\s]")
MULTIPLE_SPACE_PATTERN: Final = re.compile(r"\s+")
SEARCH_TERM_SPLIT_PATTERN: Final = re.compile(r"[\:\-\/&]")
SEARCH_TERM_NORMALIZER: Final = re.compile(r"\s*[:-]\s+")

# Sensitive keys that should be masked in URLs
SENSITIVE_KEYS: Final[set[str]] = {
    "Authorization",
    "Client-ID",
    "Client-Secret",
    "client_id",
    "client_secret",
    "api_key",
    "ssid",
    "sspassword",
    "devid",
    "devpassword",
    "y",
}


@lru_cache(maxsize=1024)
def normalize_search_term(
    name: str, remove_articles: bool = True, remove_punctuation: bool = True
) -> str:
    """Normalize a search term for comparison.

    This function normalizes game names by:
    - Converting to lowercase
    - Replacing underscores with spaces
    - Removing articles (a, an, the) if specified
    - Removing punctuation if specified
    - Normalizing Unicode characters and removing accents

    Args:
        name: The search term to normalize
        remove_articles: Whether to remove articles (default: True)
        remove_punctuation: Whether to remove punctuation (default: True)

    Returns:
        The normalized search term

    Examples:
        >>> normalize_search_term("The Legend of Zelda")
        'legend of zelda'
        >>> normalize_search_term("Super Mario Bros.")
        'super mario bros'
        >>> normalize_search_term("Pokémon Red")
        'pokemon red'
    """
    # Lower and replace underscores with spaces
    name = name.lower().replace("_", " ")

    # Remove articles (combined if possible)
    if remove_articles:
        name = LEADING_ARTICLE_PATTERN.sub("", name)
        name = COMMA_ARTICLE_PATTERN.sub("", name)

    # Remove punctuation and normalize spaces in one step
    if remove_punctuation:
        name = NON_WORD_SPACE_PATTERN.sub(" ", name)
        name = MULTIPLE_SPACE_PATTERN.sub(" ", name)

    # Unicode normalization and accent removal
    if any(ord(c) > 127 for c in name):  # Only if non-ASCII chars present
        normalized = unicodedata.normalize("NFD", name)
        name = "".join(c for c in normalized if not unicodedata.combining(c))

    return name.strip()


def normalize_cover_url(url: str) -> str:
    """Normalize a cover image URL to ensure consistent format.

    Args:
        url: The cover URL to normalize

    Returns:
        The normalized URL with https:// prefix
    """
    if not url:
        return url
    return f"https:{url.replace('https:', '')}"


def strip_sensitive_query_params(
    url: str, sensitive_keys: set[str] | None = None
) -> str:
    """Remove sensitive query parameters from a URL for logging.

    Args:
        url: The URL to sanitize
        sensitive_keys: Set of parameter names to remove (uses defaults if None)

    Returns:
        The URL with sensitive parameters removed
    """
    if sensitive_keys is None:
        sensitive_keys = SENSITIVE_KEYS

    parsed = urlparse(url)
    qsl = parse_qsl(parsed.query, keep_blank_values=True)

    keys_lower = {k.lower() for k in sensitive_keys}
    keep = [(k, v) for k, v in qsl if k.lower() not in keys_lower]

    new_query = urlencode(keep, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def mask_sensitive_values(values: dict[str, str | None]) -> dict[str, str]:
    """Mask sensitive values for safe logging.

    Masks sensitive values (headers or params), leaving only the first 2
    and last 2 characters of tokens visible.

    Args:
        values: Dictionary of header/param names to values

    Returns:
        Dictionary with sensitive values masked
    """
    masked_keys: dict[str, str] = {}
    for key, val in values.items():
        if val is None:
            masked_keys[key] = ""
            continue

        if key == "Authorization" and val.startswith("Bearer "):
            token = val.split(" ", 1)[1]
            if len(token) > 4:
                masked_keys[key] = f"Bearer {token[:2]}***{token[-2:]}"
            else:
                masked_keys[key] = "Bearer ***"
        elif key in SENSITIVE_KEYS:
            if len(val) > 4:
                masked_keys[key] = f"{val[:2]}***{val[-2:]}"
            else:
                masked_keys[key] = "***"
        else:
            masked_keys[key] = val
    return masked_keys


def split_search_term(name: str) -> list[str]:
    """Split a search term by common delimiters.

    Useful for handling game names with subtitles like "Game: Subtitle".

    Args:
        name: The game name to split

    Returns:
        List of parts split by colons, dashes, and slashes
    """
    return SEARCH_TERM_SPLIT_PATTERN.split(name)


def normalize_for_api(search_term: str) -> str:
    """Normalize a search term for API queries.

    Replaces certain punctuation patterns with more API-friendly formats.

    Args:
        search_term: The search term to normalize

    Returns:
        The normalized search term suitable for API queries
    """
    return SEARCH_TERM_NORMALIZER.sub(": ", search_term)
