# retro-metadata Documentation

**retro-metadata** is a Python library for fetching game metadata from multiple providers. It's designed to be the core engine for ROM managers, game launchers, and emulation frontends.

## Quick Start

```python
from retro_metadata import MetadataClient, MetadataConfig, ProviderConfig

# Configure providers
config = MetadataConfig(
    igdb=ProviderConfig(
        enabled=True,
        credentials={
            "client_id": "your_twitch_client_id",
            "client_secret": "your_twitch_client_secret",
        }
    )
)

# Use the client
async with MetadataClient(config) as client:
    # Search for games
    results = await client.search("Super Mario World", platform="snes")

    # Identify a ROM file
    game = await client.identify("Super Mario World (USA).sfc", platform="snes")

    # Get by provider ID
    game = await client.get_by_id("igdb", 1234)
```

## Features

- **Multiple Providers**: IGDB, MobyGames, ScreenScraper, RetroAchievements, SteamGridDB, HLTB
- **Smart Matching**: Jaro-Winkler similarity for fuzzy name matching
- **ROM Identification**: Parse No-Intro filenames and identify games
- **Caching**: Memory, Redis, and SQLite cache backends
- **Async Support**: Built on asyncio for high performance
- **Type Safety**: Full type hints and TypedDict definitions

## Installation

```bash
pip install retro-metadata
```

With optional dependencies:

```bash
# Redis cache support
pip install retro-metadata[redis]

# SQLite cache support
pip install retro-metadata[sqlite]

# All optional dependencies
pip install retro-metadata[all]
```

## UI Applications

- **CLI**: `pip install retro-metadata-cli`
- **TUI**: `pip install retro-metadata-tui`
- **Desktop**: `pip install retro-metadata-qt`
- **Web**: `pip install retro-metadata-web`

## Documentation Contents

### Architecture
- [Overview](architecture/overview.md) - System architecture
- [Library Design](architecture/library.md) - Core library design
- [Providers](architecture/providers.md) - Provider implementation
- [Caching](architecture/caching.md) - Cache backend design

### Guides
- [Installation](guides/installation.md) - Installation instructions
- [Configuration](guides/configuration.md) - Configuration reference
- [CLI Usage](guides/cli-usage.md) - CLI user guide
- [Integration](guides/integration.md) - Integrating with other projects

### API Reference
- [MetadataClient](api/client.md) - Client API
- [Providers](api/providers.md) - Provider APIs
- [Types](api/types.md) - Type definitions
- [Cache](api/cache.md) - Cache backend API

### Development
- [Contributing](development/contributing.md) - Contribution guide
- [Testing](development/testing.md) - Testing guide
- [Adding Providers](development/adding-providers.md) - How to add providers
- [Migration](development/migration.md) - Syncing with RomM upstream

## License

MIT License
