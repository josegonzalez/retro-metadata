# retro-metadata

Python library for fetching game metadata from multiple providers. Designed for ROM managers, game launchers, and emulation frontends.

## Features

- **Multiple Providers**: IGDB, MobyGames, ScreenScraper, RetroAchievements, SteamGridDB, HowLongToBeat
- **Smart Matching**: Jaro-Winkler similarity algorithm for fuzzy name matching
- **ROM Identification**: Parse No-Intro filenames and identify games automatically
- **Caching**: In-memory, Redis, and SQLite cache backends
- **Async Support**: Built on asyncio for high performance
- **Type Safety**: Full type hints throughout the codebase

## Installation

### Using uv (recommended for development)

```bash
# Clone the repository
git clone https://github.com/josegonzalez/retro-metadata.git
cd retro-metadata

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# With optional dependencies
uv pip install -e ".[redis]"
uv pip install -e ".[sqlite]"
uv pip install -e ".[all]"

# Or use uv run to execute without activating
uv run python -c "from retro_metadata import MetadataClient; print('OK')"
```

### Using pip (after package is published)

```bash
pip install retro-metadata
```

With optional dependencies:

```bash
pip install retro-metadata[redis]   # Redis cache
pip install retro-metadata[sqlite]  # SQLite cache
pip install retro-metadata[all]     # All optional deps
```

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
    ),
    mobygames=ProviderConfig(
        enabled=True,
        credentials={"api_key": "your_api_key"}
    )
)

# Use the client
async with MetadataClient(config) as client:
    # Search for games
    results = await client.search("Super Mario World", platform="snes")
    for result in results:
        print(f"{result.name} ({result.provider})")

    # Identify a ROM file
    game = await client.identify("Super Mario World (USA).sfc", platform="snes")
    if game:
        print(f"Identified: {game.name}")
        print(f"Rating: {game.metadata.total_rating}/100")

    # Get by provider ID
    game = await client.get_by_id("igdb", 1234)
```

## Providers

| Provider | API Key Required | Features |
|----------|------------------|----------|
| IGDB | Yes (Twitch OAuth) | Full metadata, artwork, ratings |
| MobyGames | Yes | Full metadata, comprehensive database |
| ScreenScraper | Yes (User/Pass) | Screenshots, box art, videos |
| RetroAchievements | Yes | Achievement data, hashes |
| SteamGridDB | Yes | High-quality artwork |
| HowLongToBeat | No | Completion time estimates |

### Getting API Keys

- **IGDB**: Create a Twitch developer app at https://dev.twitch.tv/console
- **MobyGames**: Request at https://www.mobygames.com/info/api/
- **ScreenScraper**: Register at https://screenscraper.fr/
- **RetroAchievements**: Get from your profile at https://retroachievements.org/
- **SteamGridDB**: Get at https://www.steamgriddb.com/profile/preferences/api

## UI Packages

- **CLI**: `pip install retro-metadata-cli`
- **TUI**: `pip install retro-metadata-tui`
- **Desktop (Qt)**: `pip install retro-metadata-qt`
- **Web**: `pip install retro-metadata-web`

### Running UI Packages Before Publishing

While the core package is not yet published, clone all repositories and install with local dependencies:

```bash
# Clone all repositories into the same parent directory
git clone https://github.com/josegonzalez/retro-metadata.git
git clone https://github.com/josegonzalez/retro-metadata-cli.git
git clone https://github.com/josegonzalez/retro-metadata-tui.git
git clone https://github.com/josegonzalez/retro-metadata-qt.git
git clone https://github.com/josegonzalez/retro-metadata-web.git

# Create a shared virtual environment
uv venv
source .venv/bin/activate

# Install all packages
uv pip install -e ./retro-metadata
uv pip install -e ./retro-metadata-cli
uv pip install -e ./retro-metadata-tui
uv pip install -e ./retro-metadata-qt
uv pip install -e ./retro-metadata-web

# Now all commands are available
retro-metadata --help          # CLI
retro-metadata-tui             # Terminal UI
retro-metadata-qt              # Desktop app
retro-metadata-web             # Web server
```

## Caching

```python
from retro_metadata import MetadataConfig, CacheConfig

# In-memory cache (default)
config = MetadataConfig(
    cache=CacheConfig(backend="memory", ttl=86400, max_size=1000)
)

# Redis cache
config = MetadataConfig(
    cache=CacheConfig(backend="redis", connection_string="redis://localhost")
)

# SQLite cache
config = MetadataConfig(
    cache=CacheConfig(backend="sqlite", connection_string="metadata_cache.db")
)
```

## Platform Support

The library uses universal platform slugs that map to provider-specific IDs:

```python
from retro_metadata.platforms import UniversalPlatformSlug

# Use slug directly
results = await client.search("Zelda", platform="snes")

# Or use enum
results = await client.search("Zelda", platform=UniversalPlatformSlug.SNES)
```

Supported platforms include: NES, SNES, N64, GameCube, Wii, Switch, Game Boy, GBC, GBA, DS, 3DS, Genesis, Saturn, Dreamcast, PlayStation 1-5, PSP, Vita, Xbox, Arcade, and many more.

## Documentation

Full documentation available at https://github.com/josegonzalez/retro-metadata/docs

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Origin

This library was extracted from [RomM](https://github.com/rommapp/romm) to provide a standalone, reusable metadata scraping solution.

## License

MIT License
