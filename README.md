# retro-metadata

Multi-language library for fetching game metadata from multiple providers. Available in **Python** and **Go**. Designed for ROM managers, game launchers, and emulation frontends.

## Features

- **Multiple Providers**: IGDB, MobyGames, ScreenScraper, RetroAchievements, SteamGridDB, HowLongToBeat, TheGamesDB, LaunchBox, Flashpoint, and more
- **Smart Matching**: Jaro-Winkler similarity algorithm for fuzzy name matching
- **ROM Identification**: Parse No-Intro filenames and identify games automatically
- **Caching**: In-memory, Redis, and SQLite cache backends
- **Async Support**: Built on asyncio (Python) and goroutines (Go) for high performance
- **Type Safety**: Full type hints (Python) and strong typing (Go)
- **Shared Test Suite**: Both implementations share test data ensuring consistent behavior

## Installation

### Python

#### Using uv (recommended for development)

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

#### Using pip (after package is published)

```bash
pip install retro-metadata
```

With optional dependencies:

```bash
pip install retro-metadata[redis]   # Redis cache
pip install retro-metadata[sqlite]  # SQLite cache
pip install retro-metadata[all]     # All optional deps
```

### Go

```bash
go get github.com/josegonzalez/retro-metadata/pkg/retrometadata
```

## Quick Start

### Python

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

### Go

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/josegonzalez/retro-metadata/pkg/retrometadata"
    "github.com/josegonzalez/retro-metadata/pkg/provider/igdb"
    "github.com/josegonzalez/retro-metadata/pkg/provider/mobygames"
)

func main() {
    ctx := context.Background()

    // Configure providers
    config := &retrometadata.Config{
        Providers: map[string]*retrometadata.ProviderConfig{
            "igdb": {
                Enabled: true,
                Credentials: map[string]string{
                    "client_id":     "your_twitch_client_id",
                    "client_secret": "your_twitch_client_secret",
                },
            },
            "mobygames": {
                Enabled: true,
                Credentials: map[string]string{
                    "api_key": "your_api_key",
                },
            },
        },
    }

    // Create client
    client, err := retrometadata.NewClient(config)
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()

    // Search for games
    results, err := client.Search(ctx, "Super Mario World", retrometadata.SearchOptions{
        Platform: "snes",
    })
    if err != nil {
        log.Fatal(err)
    }

    for _, result := range results {
        fmt.Printf("%s (%s)\n", result.Name, result.Provider)
    }

    // Identify a ROM file
    game, err := client.Identify(ctx, "Super Mario World (USA).sfc", retrometadata.IdentifyOptions{
        Platform: "snes",
    })
    if err != nil {
        log.Fatal(err)
    }

    if game != nil {
        fmt.Printf("Identified: %s\n", game.Name)
        if game.Metadata.TotalRating != nil {
            fmt.Printf("Rating: %.0f/100\n", *game.Metadata.TotalRating)
        }
    }

    // Get by provider ID
    game, err = client.GetByID(ctx, "igdb", 1234)
    if err != nil {
        log.Fatal(err)
    }
}
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
| TheGamesDB | Yes | Box art, metadata |
| LaunchBox | No (local XML) | Local metadata from LaunchBox |
| Flashpoint | No | Flash/web game archive |
| Hasheous | No | Hash-based identification |
| Playmatch | No | Hash-to-IGDB ID matching |

### Getting API Keys

- **IGDB**: Create a Twitch developer app at https://dev.twitch.tv/console
- **MobyGames**: Request at https://www.mobygames.com/info/api/
- **ScreenScraper**: Register at https://screenscraper.fr/
- **RetroAchievements**: Get from your profile at https://retroachievements.org/
- **SteamGridDB**: Get at https://www.steamgriddb.com/profile/preferences/api
- **TheGamesDB**: Request at https://thegamesdb.net/

## Caching

### Python

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

### Go

```go
import (
    "github.com/josegonzalez/retro-metadata/pkg/retrometadata"
    "github.com/josegonzalez/retro-metadata/pkg/cache"
)

// In-memory cache (default)
config := &retrometadata.Config{
    Cache: &retrometadata.CacheConfig{
        Backend: "memory",
        TTL:     86400,
        MaxSize: 1000,
    },
}

// Redis cache
config := &retrometadata.Config{
    Cache: &retrometadata.CacheConfig{
        Backend:          "redis",
        ConnectionString: "redis://localhost",
    },
}

// SQLite cache
config := &retrometadata.Config{
    Cache: &retrometadata.CacheConfig{
        Backend:          "sqlite",
        ConnectionString: "metadata_cache.db",
    },
}
```

## Filename Parsing

Both implementations include utilities for parsing ROM filenames:

### Python

```python
from retro_metadata.utils.filename import (
    parse_no_intro_filename,
    clean_filename,
    extract_region,
    is_bios_file,
)

# Parse a No-Intro filename
info = parse_no_intro_filename("Super Mario World (USA) (Rev 1).sfc")
print(info["name"])      # "Super Mario World"
print(info["region"])    # "us"
print(info["version"])   # "Rev 1"

# Clean a filename
clean = clean_filename("Game (USA) [!].sfc")
print(clean)  # "Game"

# Extract region
region = extract_region("Zelda (Europe).sfc")
print(region)  # "eu"

# Check for BIOS files
is_bios = is_bios_file("[BIOS] PlayStation.bin")
print(is_bios)  # True
```

### Go

```go
import "github.com/josegonzalez/retro-metadata/pkg/filename"

// Parse a No-Intro filename
info := filename.ParseNoIntroFilename("Super Mario World (USA) (Rev 1).sfc")
fmt.Println(info.Name)      // "Super Mario World"
fmt.Println(info.Region)    // "us"
fmt.Println(info.Version)   // "Rev 1"

// Clean a filename
clean := filename.CleanFilename("Game (USA) [!].sfc", true)
fmt.Println(clean)  // "Game"

// Extract region
region := filename.ExtractRegion("Zelda (Europe).sfc")
fmt.Println(region)  // "eu"

// Check for BIOS files
isBios := filename.IsBiosFile("[BIOS] PlayStation.bin")
fmt.Println(isBios)  // true
```

## Platform Support

The library uses universal platform slugs that map to provider-specific IDs:

### Python

```python
from retro_metadata.platforms import UniversalPlatformSlug

# Use slug directly
results = await client.search("Zelda", platform="snes")

# Or use enum
results = await client.search("Zelda", platform=UniversalPlatformSlug.SNES)
```

### Go

```go
import "github.com/josegonzalez/retro-metadata/pkg/platform"

// Use slug directly
results, _ := client.Search(ctx, "Zelda", retrometadata.SearchOptions{
    Platform: "snes",
})

// Or use constant
results, _ := client.Search(ctx, "Zelda", retrometadata.SearchOptions{
    Platform: platform.SNES,
})
```

Supported platforms include: NES, SNES, N64, GameCube, Wii, Switch, Game Boy, GBC, GBA, DS, 3DS, Genesis, Saturn, Dreamcast, PlayStation 1-5, PSP, Vita, Xbox, Arcade, and 400+ more.

## Project Structure

```
retro-metadata/
├── src/retro_metadata/     # Python implementation
├── pkg/                    # Go implementation
│   ├── retrometadata/      # Main client and types
│   ├── provider/           # Provider implementations
│   ├── cache/              # Cache backends
│   ├── platform/           # Platform mappings
│   ├── filename/           # Filename parsing
│   └── internal/           # Internal utilities
├── testdata/               # Shared test data (JSON)
└── tests/                  # Python tests
```

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

## Development

### Running Tests

```bash
# Python tests
uv sync --extra dev
uv run pytest tests/ -v

# Go tests
go test ./... -v

# Both share test data in testdata/ directory
```

### Test Data

Both implementations share test data in the `testdata/` directory to ensure consistent behavior:

```
testdata/
├── filename/           # Filename parsing tests
├── matching/           # String matching tests
├── normalization/      # Text normalization tests
└── cache/              # Cache behavior tests
```

## Documentation

Full documentation available at https://github.com/josegonzalez/retro-metadata/docs

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Origin

This library was extracted from [RomM](https://github.com/rommapp/romm) to provide a standalone, reusable metadata scraping solution.

## License

MIT License
