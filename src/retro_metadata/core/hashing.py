"""File hashing utilities for ROM identification."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)


class FileHashes(NamedTuple):
    """Container for file hash values."""

    md5: str
    sha1: str
    crc32: str
    file_size: int


def calculate_hashes(file_path: str | Path, chunk_size: int = 8192) -> FileHashes:
    """Calculate MD5, SHA1, and CRC32 hashes for a file.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        FileHashes containing md5, sha1, crc32, and file_size

    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If the file can't be read
    """
    import zlib

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    md5_hash = hashlib.md5()
    sha1_hash = hashlib.sha1()
    crc32_value = 0
    file_size = 0

    logger.debug("Calculating hashes for: %s", path.name)

    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5_hash.update(chunk)
            sha1_hash.update(chunk)
            crc32_value = zlib.crc32(chunk, crc32_value)
            file_size += len(chunk)

    result = FileHashes(
        md5=md5_hash.hexdigest().lower(),
        sha1=sha1_hash.hexdigest().lower(),
        crc32=format(crc32_value & 0xFFFFFFFF, "08x").lower(),
        file_size=file_size,
    )

    logger.debug(
        "Hashes calculated: MD5=%s, SHA1=%s, CRC32=%s, size=%d",
        result.md5,
        result.sha1,
        result.crc32,
        result.file_size,
    )

    return result


def calculate_md5(file_path: str | Path, chunk_size: int = 8192) -> str:
    """Calculate MD5 hash for a file.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        MD5 hash as lowercase hex string
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    md5_hash = hashlib.md5()

    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5_hash.update(chunk)

    return md5_hash.hexdigest().lower()


def calculate_sha1(file_path: str | Path, chunk_size: int = 8192) -> str:
    """Calculate SHA1 hash for a file.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        SHA1 hash as lowercase hex string
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha1_hash = hashlib.sha1()

    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha1_hash.update(chunk)

    return sha1_hash.hexdigest().lower()


def calculate_crc32(file_path: str | Path, chunk_size: int = 8192) -> str:
    """Calculate CRC32 hash for a file.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time

    Returns:
        CRC32 hash as lowercase hex string
    """
    import zlib

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    crc32_value = 0

    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            crc32_value = zlib.crc32(chunk, crc32_value)

    return format(crc32_value & 0xFFFFFFFF, "08x").lower()
