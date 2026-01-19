#!/usr/bin/env python3
"""Example: Multi-Provider Search

This example demonstrates how to search across multiple metadata providers
concurrently and aggregate results.

To run:
    export IGDB_CLIENT_ID="your_client_id"
    export IGDB_CLIENT_SECRET="your_client_secret"
    export MOBYGAMES_API_KEY="your_api_key"
    python main.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from retro_metadata import ProviderConfig
from retro_metadata.providers import IGDBProvider, MobyGamesProvider

if TYPE_CHECKING:
    from retro_metadata.providers.base import MetadataProvider
    from retro_metadata.types.common import SearchResult


@dataclass
class ProviderWrapper:
    """Wraps a metadata provider with a name."""

    name: str
    provider: MetadataProvider


@dataclass
class SearchResultGroup:
    """Groups search results by provider."""

    provider_name: str
    results: list[SearchResult]
    error: Exception | None = None


async def search_provider(
    wrapper: ProviderWrapper,
    query: str,
    limit: int = 5,
) -> SearchResultGroup:
    """Search a single provider and return results."""
    try:
        results = await wrapper.provider.search(query, limit=limit)
        return SearchResultGroup(provider_name=wrapper.name, results=results)
    except Exception as e:
        return SearchResultGroup(provider_name=wrapper.name, results=[], error=e)


async def main() -> None:
    # Get credentials from environment variables
    igdb_client_id = os.getenv("IGDB_CLIENT_ID", "")
    igdb_client_secret = os.getenv("IGDB_CLIENT_SECRET", "")
    moby_api_key = os.getenv("MOBYGAMES_API_KEY", "")

    # Create providers list
    providers: list[ProviderWrapper] = []

    # Create IGDB provider if credentials are available
    if igdb_client_id and igdb_client_secret:
        igdb_config = ProviderConfig(
            enabled=True,
            credentials={
                "client_id": igdb_client_id,
                "client_secret": igdb_client_secret,
            },
            timeout=30,
        )
        igdb_provider = IGDBProvider(igdb_config)
        providers.append(ProviderWrapper(name="IGDB", provider=igdb_provider))

    # Create MobyGames provider if credentials are available
    if moby_api_key:
        moby_config = ProviderConfig(
            enabled=True,
            credentials={"api_key": moby_api_key},
            timeout=30,
        )
        moby_provider = MobyGamesProvider(moby_config)
        providers.append(ProviderWrapper(name="MobyGames", provider=moby_provider))

    if not providers:
        print(
            "No providers available. Please set at least one of:\n"
            "  IGDB_CLIENT_ID and IGDB_CLIENT_SECRET\n"
            "  MOBYGAMES_API_KEY"
        )
        sys.exit(1)

    print(f"Using {len(providers)} provider(s)\n")

    # Search query
    query = "Chrono Trigger"

    # Search all providers concurrently
    print(f"Searching for '{query}' across all providers...\n")
    start = time.time()

    # Create tasks for concurrent execution
    tasks = [search_provider(p, query, limit=5) for p in providers]
    result_groups = await asyncio.gather(*tasks)

    elapsed = time.time() - start
    print(f"Search completed in {elapsed:.3f}s\n")

    # Print results by provider
    for group in result_groups:
        print(f"═══ {group.provider_name} Results ═══")
        if group.error:
            print(f"  Error: {group.error}")
        elif not group.results:
            print("  No results found")
        else:
            for i, result in enumerate(group.results, 1):
                print(f"{i}. {result.name}")
                if result.release_year:
                    print(f"   Year: {result.release_year}")
                if result.platforms:
                    print(f"   Platforms: {result.platforms}")
        print()

    # Clean up
    for wrapper in providers:
        await wrapper.provider.close()


if __name__ == "__main__":
    asyncio.run(main())
