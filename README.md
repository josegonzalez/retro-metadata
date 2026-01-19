# retro-metadata

Multi-language library for fetching game metadata from multiple providers. Available in **Python**, **Go**, and **C++**. Designed for ROM managers, game launchers, and emulation frontends.

## Features

- **Multiple Providers**: IGDB, MobyGames, ScreenScraper, RetroAchievements, SteamGridDB, HowLongToBeat, TheGamesDB, LaunchBox, Flashpoint, and more
- **Smart Matching**: Jaro-Winkler similarity algorithm for fuzzy name matching
- **ROM Identification**: Parse No-Intro filenames and identify games automatically
- **Caching**: In-memory, Redis, and SQLite cache backends
- **Shared Test Suite**: All implementations share test data ensuring consistent behavior

## Installation

### Python

```bash
pip install retro-metadata
```

### Go

```bash
go get github.com/josegonzalez/retro-metadata/pkg/retrometadata
```

### C++

```bash
cd cpp && cmake -B build && cmake --build build
```

## Quick Start

### Python

```python
async with MetadataClient(config) as client:
    results = await client.search("Super Mario World", platform="snes")
```

### Go

```go
results, err := client.Search(ctx, "Super Mario World", retrometadata.SearchOptions{Platform: "snes"})
```

### C++

```cpp
auto results = provider->search("Super Mario World", opts);
```

See the [Quick Start Guide](docs/guides/quickstart.md) for complete examples.

## Documentation

Full documentation is available in the [docs/](docs/) directory:

- [Quick Start](docs/guides/quickstart.md) - Getting started with all languages
- [Caching](docs/guides/caching.md) - Configure cache backends
- [Filename Parsing](docs/guides/filename-parsing.md) - Parse ROM filenames
- [Platforms](docs/guides/platforms.md) - Platform slug mappings
- [Providers](docs/architecture/providers.md) - Provider details and API keys

## Providers

| Provider | API Key | Features |
|----------|---------|----------|
| IGDB | Twitch OAuth | Full metadata, artwork, ratings |
| MobyGames | Yes | Comprehensive game database |
| ScreenScraper | User/Pass | Screenshots, box art, videos |
| RetroAchievements | Yes | Achievement data, ROM hashes |
| SteamGridDB | Yes | High-quality artwork |
| HowLongToBeat | No | Completion time estimates |
| TheGamesDB | Yes | Box art, metadata |
| LaunchBox | No | Local XML metadata |
| Flashpoint | No | Flash/web game archive |
| Hasheous | No | Hash-based identification |
| Playmatch | No | Hash-to-IGDB matching |
| Gamelist | No | EmulationStation XML |

## Project Structure

```
retro-metadata/
├── src/retro_metadata/     # Python implementation
├── pkg/                    # Go implementation
├── cpp/                    # C++ implementation
├── testdata/               # Shared test data
└── docs/                   # Documentation
```

## Development

```bash
# Python
uv run pytest tests/ -v

# Go
go test ./... -v

# C++
cmake -B build -S cpp -DRETRO_METADATA_BUILD_TESTS=ON
cmake --build build && ctest --test-dir build
```

## Origin

This library was extracted from [RomM](https://github.com/rommapp/romm) to provide a standalone, reusable metadata scraping solution.

## License

MIT License
