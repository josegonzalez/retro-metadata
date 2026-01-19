#!/usr/bin/env python3
"""Example: Basic Search

This example demonstrates how to search for a game using the IGDB provider.

To run:
    export IGDB_CLIENT_ID="your_client_id"
    export IGDB_CLIENT_SECRET="your_client_secret"
    python main.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from retro_metadata import ProviderConfig
from retro_metadata.providers import IGDBProvider


async def main() -> None:
    # Get credentials from environment variables
    client_id = os.getenv("IGDB_CLIENT_ID", "")
    client_secret = os.getenv("IGDB_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("Please set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables")
        sys.exit(1)

    # Create provider configuration
    config = ProviderConfig(
        enabled=True,
        credentials={
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )

    # Create IGDB provider
    provider = IGDBProvider(config)

    try:
        # Search for games
        results = await provider.search("Super Mario World", limit=5)

        # Print results
        print(f"Found {len(results)} results for 'Super Mario World':\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.name}")
            print(f"   Provider: {result.provider}")
            print(f"   ID: {result.provider_id}")
            if result.release_year:
                print(f"   Year: {result.release_year}")
            if result.cover_url:
                print(f"   Cover: {result.cover_url}")
            print()
    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
