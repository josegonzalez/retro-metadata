"""File hashing utilities for ROM identification."""

from __future__ import annotations

import hashlib
import zlib
from pathlib import Path


def compute_crc32(file_path: str | Path, chunk_size: int = 65536) -> str:
    """Compute CRC32 checksum of a file.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        CRC32 checksum as uppercase hex string

    Example:
        >>> compute_crc32("game.sfc")
        'A1B2C3D4'
    """
    crc = 0
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            crc = zlib.crc32(chunk, crc)
    return format(crc & 0xFFFFFFFF, "08X")


def compute_md5(file_path: str | Path, chunk_size: int = 65536) -> str:
    """Compute MD5 hash of a file.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        MD5 hash as lowercase hex string

    Example:
        >>> compute_md5("game.sfc")
        'a1b2c3d4e5f6...'
    """
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_sha1(file_path: str | Path, chunk_size: int = 65536) -> str:
    """Compute SHA1 hash of a file.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        SHA1 hash as lowercase hex string

    Example:
        >>> compute_sha1("game.sfc")
        'a1b2c3d4e5f6...'
    """
    hasher = hashlib.sha1()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_all_hashes(file_path: str | Path, chunk_size: int = 65536) -> dict[str, str]:
    """Compute all common hashes of a file in a single pass.

    More efficient than calling individual functions when you need
    multiple hash types.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        Dictionary with 'crc32', 'md5', and 'sha1' keys

    Example:
        >>> compute_all_hashes("game.sfc")
        {'crc32': 'A1B2C3D4', 'md5': 'a1b2...', 'sha1': 'a1b2...'}
    """
    crc = 0
    md5_hasher = hashlib.md5()
    sha1_hasher = hashlib.sha1()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            crc = zlib.crc32(chunk, crc)
            md5_hasher.update(chunk)
            sha1_hasher.update(chunk)

    return {
        "crc32": format(crc & 0xFFFFFFFF, "08X"),
        "md5": md5_hasher.hexdigest(),
        "sha1": sha1_hasher.hexdigest(),
    }


def compute_crc32_from_buffer(data: bytes) -> str:
    """Compute CRC32 checksum of a bytes buffer.

    Args:
        data: Bytes data to hash

    Returns:
        CRC32 checksum as uppercase hex string
    """
    crc = zlib.crc32(data) & 0xFFFFFFFF
    return format(crc, "08X")


def compute_md5_from_buffer(data: bytes) -> str:
    """Compute MD5 hash of a bytes buffer.

    Args:
        data: Bytes data to hash

    Returns:
        MD5 hash as lowercase hex string
    """
    return hashlib.md5(data).hexdigest()


def compute_sha1_from_buffer(data: bytes) -> str:
    """Compute SHA1 hash of a bytes buffer.

    Args:
        data: Bytes data to hash

    Returns:
        SHA1 hash as lowercase hex string
    """
    return hashlib.sha1(data).hexdigest()


async def compute_crc32_async(file_path: str | Path, chunk_size: int = 65536) -> str:
    """Async version of compute_crc32.

    Uses asyncio to avoid blocking on file I/O.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        CRC32 checksum as uppercase hex string
    """
    import asyncio

    return await asyncio.to_thread(compute_crc32, file_path, chunk_size)


async def compute_md5_async(file_path: str | Path, chunk_size: int = 65536) -> str:
    """Async version of compute_md5.

    Uses asyncio to avoid blocking on file I/O.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        MD5 hash as lowercase hex string
    """
    import asyncio

    return await asyncio.to_thread(compute_md5, file_path, chunk_size)


async def compute_sha1_async(file_path: str | Path, chunk_size: int = 65536) -> str:
    """Async version of compute_sha1.

    Uses asyncio to avoid blocking on file I/O.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        SHA1 hash as lowercase hex string
    """
    import asyncio

    return await asyncio.to_thread(compute_sha1, file_path, chunk_size)


async def compute_all_hashes_async(
    file_path: str | Path, chunk_size: int = 65536
) -> dict[str, str]:
    """Async version of compute_all_hashes.

    Uses asyncio to avoid blocking on file I/O.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        Dictionary with 'crc32', 'md5', and 'sha1' keys
    """
    import asyncio

    return await asyncio.to_thread(compute_all_hashes, file_path, chunk_size)
