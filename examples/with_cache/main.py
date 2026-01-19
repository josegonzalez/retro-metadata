#!/usr/bin/env python3
"""Example: Using Cache with Providers

This example demonstrates how to use an in-memory cache with providers
to reduce API calls and improve performance.

To run:
    export IGDB_CLIENT_ID="your_client_id"
    export IGDB_CLIENT_SECRET="your_client_secret"
    python main.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

from retro_metadata import ProviderConfig
from retro_metadata.cache import MemoryCache
from retro_metadata.providers import IGDBProvider


async def main() -> None:
    # Get credentials from environment variables
    client_id = os.getenv("IGDB_CLIENT_ID", "")
    client_secret = os.getenv("IGDB_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("Please set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables")
        sys.exit(1)

    # Create an in-memory cache
    # Options:
    # - max_size: Maximum number of cached items (default: 10000)
    # - default_ttl: How long items stay cached in seconds (default: 3600)
    mem_cache = MemoryCache(
        max_size=1000,
        default_ttl=1800,  # 30 minutes
    )

    # Create provider configuration
    config = ProviderConfig(
        enabled=True,
        credentials={
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )

    # Create IGDB provider with cache
    provider = IGDBProvider(config, cache=mem_cache)

    try:
        query = "The Legend of Zelda"

        # First search - will hit the API
        print("First search (no cache)...")
        start = time.time()
        results1 = await provider.search(query, limit=5)
        elapsed1 = time.time() - start
        print(f"Found {len(results1)} results in {elapsed1:.3f}s\n")

        # Second search - should be cached
        print("Second search (should be cached)...")
        start = time.time()
        results2 = await provider.search(query, limit=5)
        elapsed2 = time.time() - start
        print(f"Found {len(results2)} results in {elapsed2:.3f}s\n")

        # Print cache stats
        stats = await mem_cache.stats()
        print("Cache Stats:")
        print(f"  Size: {stats.size} / {stats.max_size}")
        print(f"  Hits: {stats.hits}")
        print(f"  Misses: {stats.misses}")

        # Print results
        print(f"\nResults for '{query}':")
        for i, result in enumerate(results1, 1):
            print(f"{i}. {result.name} ({result.provider})")
    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
