#!/usr/bin/env python3
"""Example: Identify Game from Filename

This example demonstrates how to identify a game from its ROM filename.

To run:
    export IGDB_CLIENT_ID="your_client_id"
    export IGDB_CLIENT_SECRET="your_client_secret"
    python main.py "Super Mario World (USA).sfc"
"""

from __future__ import annotations

import asyncio
import os
import sys

from retro_metadata import ProviderConfig
from retro_metadata.providers import IGDBProvider
from retro_metadata.utils import clean_filename, extract_region, get_file_extension


async def main() -> None:
    # Get filename from command line
    if len(sys.argv) < 2:
        print("Usage: python main.py <filename>")
        print('Example: python main.py "Super Mario World (USA).sfc"')
        sys.exit(1)
    rom_filename = sys.argv[1]

    # Get credentials from environment variables
    client_id = os.getenv("IGDB_CLIENT_ID", "")
    client_secret = os.getenv("IGDB_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("Please set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables")
        sys.exit(1)

    # Parse the filename first
    print(f"Parsing filename: {rom_filename}\n")

    # Get file extension
    ext = get_file_extension(rom_filename)
    print(f"Extension: {ext}")

    # Extract region
    region = extract_region(rom_filename)
    print(f"Region: {region}")

    # Clean the filename to get the game name
    clean_name = clean_filename(rom_filename, remove_extension=True)
    print(f"Clean name: {clean_name}\n")

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
        # Identify the game
        result = await provider.identify(rom_filename)

        if result is None:
            print("No game found")
            return

        # Print result
        print("Game Identified:")
        print(f"  Name: {result.name}")
        print(f"  Match Score: {result.match_score:.2f}")

        if result.summary:
            summary = result.summary
            if len(summary) > 200:
                summary = summary[:200] + "..."
            print(f"  Summary: {summary}")

        if result.metadata.genres:
            print(f"  Genres: {result.metadata.genres}")

        if result.metadata.companies:
            print(f"  Companies: {result.metadata.companies}")

        if result.metadata.release_year:
            print(f"  Year: {result.metadata.release_year}")

        if result.artwork and result.artwork.cover_url:
            print(f"  Cover: {result.artwork.cover_url}")
    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
