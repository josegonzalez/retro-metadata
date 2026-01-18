"""Filename parsing utilities for ROM files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

# Common region tags
REGION_TAGS: Final[dict[str, str]] = {
    "usa": "us",
    "u": "us",
    "us": "us",
    "america": "us",
    "world": "wor",
    "w": "wor",
    "wor": "wor",
    "europe": "eu",
    "e": "eu",
    "eu": "eu",
    "eur": "eu",
    "japan": "jp",
    "j": "jp",
    "jp": "jp",
    "jpn": "jp",
    "jap": "jp",
    "korea": "kr",
    "k": "kr",
    "kr": "kr",
    "kor": "kr",
    "china": "cn",
    "ch": "cn",
    "cn": "cn",
    "chn": "cn",
    "taiwan": "tw",
    "tw": "tw",
    "asia": "as",
    "as": "as",
    "australia": "au",
    "au": "au",
    "brazil": "br",
    "br": "br",
    "france": "fr",
    "fr": "fr",
    "germany": "de",
    "de": "de",
    "ger": "de",
    "italy": "it",
    "it": "it",
    "spain": "es",
    "es": "es",
    "spa": "es",
    "netherlands": "nl",
    "nl": "nl",
    "sweden": "se",
    "se": "se",
    "russia": "ru",
    "ru": "ru",
}

# Pattern to match tags in parentheses or brackets
TAG_PATTERN: Final = re.compile(r"[\(\[]([^\)\]]+)[\)\]]")

# Pattern to match file extensions
EXTENSION_PATTERN: Final = re.compile(r"\.([a-zA-Z0-9]+)$")


def get_file_extension(filename: str) -> str:
    """Get the file extension from a filename.

    Args:
        filename: The filename to parse

    Returns:
        File extension without the dot, or empty string if none
    """
    match = EXTENSION_PATTERN.search(filename)
    return match.group(1).lower() if match else ""


def extract_tags(filename: str) -> list[str]:
    """Extract all tags from a filename.

    Tags are text within parentheses or brackets.

    Args:
        filename: The filename to parse

    Returns:
        List of tag contents (without brackets)

    Example:
        >>> extract_tags("Super Mario World (USA) [!].sfc")
        ['USA', '!']
    """
    return TAG_PATTERN.findall(filename)


def extract_region(filename: str) -> str | None:
    """Extract the region code from a filename.

    Args:
        filename: The filename to parse

    Returns:
        Normalized region code (us, eu, jp, etc.) or None if not found

    Example:
        >>> extract_region("Super Mario World (USA).sfc")
        'us'
        >>> extract_region("Zelda (Europe).sfc")
        'eu'
    """
    tags = extract_tags(filename)

    for tag in tags:
        tag_lower = tag.lower().strip()

        # Handle comma-separated regions (e.g., "USA, Europe")
        for part in tag_lower.split(","):
            part = part.strip()
            if part in REGION_TAGS:
                return REGION_TAGS[part]

    return None


def clean_filename(filename: str, remove_extension: bool = True) -> str:
    """Clean a filename by removing tags and optionally the extension.

    Args:
        filename: The filename to clean
        remove_extension: Whether to remove the file extension

    Returns:
        Cleaned filename

    Example:
        >>> clean_filename("Super Mario World (USA) [!].sfc")
        'Super Mario World'
    """
    # Get just the filename if a path was provided
    name = Path(filename).name

    # Save extension if keeping it (extract before tag removal)
    ext = ""
    if not remove_extension:
        ext_match = EXTENSION_PATTERN.search(name)
        if ext_match:
            ext = ext_match.group(0)
            name = EXTENSION_PATTERN.sub("", name)
    else:
        name = EXTENSION_PATTERN.sub("", name)

    # Remove all tags in parentheses and brackets
    name = TAG_PATTERN.sub("", name)

    # Clean up extra whitespace
    name = " ".join(name.split())

    # Reattach extension if keeping it
    if ext:
        name = name + ext

    return name.strip()


def parse_no_intro_filename(filename: str) -> dict[str, str | list[str] | None]:
    """Parse a No-Intro naming convention filename.

    No-Intro filenames follow a specific format:
    Title (Region) (Language) (Version) (Other Tags)

    Args:
        filename: The filename to parse

    Returns:
        Dictionary with parsed components

    Example:
        >>> parse_no_intro_filename("Super Mario World (USA) (Rev 1).sfc")
        {'name': 'Super Mario World', 'region': 'us', 'tags': ['Rev 1'], ...}
    """
    name = clean_filename(filename)
    tags = extract_tags(filename)
    region = extract_region(filename)
    extension = get_file_extension(filename)

    # Try to identify version
    version = None
    for tag in tags:
        if tag.lower().startswith(("rev ", "v", "version")):
            version = tag
            break

    # Try to identify language
    languages = []
    language_codes = {"en", "ja", "de", "fr", "es", "it", "nl", "pt", "sv", "ko", "zh"}
    for tag in tags:
        tag_lower = tag.lower()
        if tag_lower in language_codes or "+" in tag_lower:
            languages.append(tag)

    return {
        "name": name,
        "region": region,
        "version": version,
        "languages": languages if languages else None,
        "extension": extension,
        "tags": tags,
    }


def is_bios_file(filename: str) -> bool:
    """Check if a filename appears to be a BIOS file.

    Args:
        filename: The filename to check

    Returns:
        True if the file appears to be a BIOS file
    """
    name_lower = filename.lower()
    bios_indicators = ["bios", "[bios]", "(bios)"]
    return any(indicator in name_lower for indicator in bios_indicators)


def is_demo_file(filename: str) -> bool:
    """Check if a filename appears to be a demo.

    Args:
        filename: The filename to check

    Returns:
        True if the file appears to be a demo
    """
    tags = [t.lower() for t in extract_tags(filename)]
    demo_tags = {"demo", "sample", "trial", "preview", "proto", "prototype", "beta", "alpha"}
    return bool(demo_tags & set(tags))


def is_unlicensed(filename: str) -> bool:
    """Check if a filename indicates an unlicensed game.

    Args:
        filename: The filename to check

    Returns:
        True if the file appears to be unlicensed
    """
    tags = [t.lower() for t in extract_tags(filename)]
    unlicensed_tags = {"unl", "unlicensed", "pirate", "hack"}
    return bool(unlicensed_tags & set(tags))
