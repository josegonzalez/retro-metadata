"""Utility functions for artwork downloading."""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from urllib.parse import urlparse


def hash_url(url: str) -> str:
    """Generate a short hash from a URL for cache filenames.

    Args:
        url: The URL to hash

    Returns:
        First 16 characters of the SHA256 hash
    """
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def get_extension_from_url(url: str) -> str:
    """Extract file extension from a URL.

    Args:
        url: The URL to extract extension from

    Returns:
        File extension including the dot (e.g., ".png"), or ".jpg" as default
    """
    parsed = urlparse(url)
    path = Path(parsed.path)
    ext = path.suffix.lower()

    # Handle common image extensions
    valid_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
    if ext in valid_extensions:
        return ext

    # Default to .jpg for unknown extensions
    return ".jpg"


def get_extension_from_content_type(content_type: str) -> str:
    """Get file extension from Content-Type header.

    Args:
        content_type: The Content-Type header value

    Returns:
        File extension including the dot
    """
    content_type = content_type.lower().split(";")[0].strip()

    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
    }

    return mapping.get(content_type, ".jpg")


def get_image_dimensions(data: bytes) -> tuple[int, int] | None:
    """Parse image dimensions from PNG or JPEG headers.

    Args:
        data: The image data bytes

    Returns:
        Tuple of (width, height) or None if unable to parse
    """
    if len(data) < 24:
        return None

    # PNG: Check magic bytes and parse IHDR chunk
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        # IHDR chunk starts at byte 8, width at byte 16, height at byte 20
        if len(data) >= 24:
            width = struct.unpack(">I", data[16:20])[0]
            height = struct.unpack(">I", data[20:24])[0]
            return (width, height)

    # JPEG: Parse SOF0 marker for dimensions
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue

            marker = data[i + 1]

            # SOF0, SOF1, SOF2 markers contain dimensions
            if marker in (0xC0, 0xC1, 0xC2):
                height = struct.unpack(">H", data[i + 5 : i + 7])[0]
                width = struct.unpack(">H", data[i + 7 : i + 9])[0]
                return (width, height)

            # Skip to next marker
            if marker in (0xD8, 0xD9, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
            else:
                length = struct.unpack(">H", data[i + 2 : i + 4])[0]
                i += 2 + length

    # GIF: Parse header for dimensions
    if data[:6] in (b"GIF87a", b"GIF89a"):
        width = struct.unpack("<H", data[6:8])[0]
        height = struct.unpack("<H", data[8:10])[0]
        return (width, height)

    # WebP: Parse RIFF header
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        # VP8 or VP8L chunk
        if data[12:16] == b"VP8 " and len(data) >= 30:
            # VP8 bitstream, dimensions at offset 26
            width = struct.unpack("<H", data[26:28])[0] & 0x3FFF
            height = struct.unpack("<H", data[28:30])[0] & 0x3FFF
            return (width, height)
        elif data[12:16] == b"VP8L" and len(data) >= 25:
            # VP8L lossless
            bits = struct.unpack("<I", data[21:25])[0]
            width = (bits & 0x3FFF) + 1
            height = ((bits >> 14) & 0x3FFF) + 1
            return (width, height)

    return None


def transform_url_for_size(
    url: str,
    provider: str,
    max_width: int | None = None,
    max_height: int | None = None,
) -> str:
    """Transform artwork URL to request a specific size from the provider.

    Different providers have different URL patterns for size requests:
    - IGDB: Replace size suffix (t_thumb → t_720p, t_1080p, t_cover_big, etc.)
    - SteamGridDB: URL already contains size, may need adjustment
    - ScreenScraper: Add size parameters

    Args:
        url: The original artwork URL
        provider: The provider name
        max_width: Maximum desired width
        max_height: Maximum desired height

    Returns:
        Transformed URL with size adjustments
    """
    if not max_width and not max_height:
        return url

    if provider == "igdb":
        # IGDB uses size suffixes like t_thumb, t_cover_small, t_cover_big, t_720p, t_1080p
        # Determine the best size suffix based on max dimensions
        if max_width and max_width <= 90:
            size_suffix = "t_thumb"
        elif max_width and max_width <= 264:
            size_suffix = "t_cover_big"
        elif max_width and max_width <= 720:
            size_suffix = "t_720p"
        else:
            size_suffix = "t_1080p"

        # Replace existing size suffix
        import re

        return re.sub(r"t_[a-z0-9_]+", size_suffix, url)

    elif provider == "screenscraper":
        # ScreenScraper uses maxwidth/maxheight parameters
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        if max_width:
            params["maxwidth"] = [str(max_width)]
        if max_height:
            params["maxheight"] = [str(max_height)]

        new_query = urlencode(params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    # Default: return URL unchanged
    return url


def generate_output_filename(
    rom_filename: str,
    artwork_type: str,
    extension: str,
    filename_format: str = "extended",
) -> str:
    """Generate output filename for downloaded artwork.

    Args:
        rom_filename: The original ROM filename (e.g., "Super Mario World (USA).sfc")
        artwork_type: The type of artwork (e.g., "cover", "screenshot")
        extension: The file extension (e.g., ".png")
        filename_format: Either "extended" or "simple"

    Returns:
        Generated filename:
        - extended: "Super Mario World (USA).sfc.cover.png"
        - simple: "Super Mario World (USA).cover.png"
    """
    if not extension.startswith("."):
        extension = f".{extension}"

    rom_path = Path(rom_filename)

    if filename_format == "simple":
        # Remove the ROM extension, add artwork type and extension
        return f"{rom_path.stem}.{artwork_type}{extension}"
    else:
        # Keep the full ROM filename, add artwork type and extension
        return f"{rom_filename}.{artwork_type}{extension}"


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing invalid characters.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename safe for filesystem use
    """
    # Characters not allowed in filenames on various systems
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Remove leading/trailing spaces and dots
    filename = filename.strip(". ")

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed"

    return filename
