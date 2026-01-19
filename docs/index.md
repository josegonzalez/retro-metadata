# retro-metadata Documentation

Multi-language library for fetching game metadata from multiple providers. Available in **Python**, **Go**, and **C++**.

## Features

- **Multiple Providers**: IGDB, MobyGames, ScreenScraper, RetroAchievements, SteamGridDB, HowLongToBeat, and more
- **Smart Matching**: Jaro-Winkler similarity for fuzzy name matching
- **ROM Identification**: Parse No-Intro filenames and identify games
- **Caching**: Memory, Redis, and SQLite cache backends
- **Async Support**: asyncio (Python), goroutines (Go), futures (C++)
- **Type Safety**: Full type hints and strong typing across all implementations

## Quick Example

**Python:**
```python
async with MetadataClient(config) as client:
    results = await client.search("Super Mario World", platform="snes")
```

**Go:**
```go
results, err := client.Search(ctx, "Super Mario World", retrometadata.SearchOptions{Platform: "snes"})
```

**C++:**
```cpp
auto results = provider->search("Super Mario World", opts);
```

See the [Quick Start Guide](guides/quickstart.md) for complete examples in all languages.

## Documentation Contents

### Guides
- [Quick Start](guides/quickstart.md) - Getting started with Python, Go, and C++
- [Caching](guides/caching.md) - Configure cache backends
- [Filename Parsing](guides/filename-parsing.md) - Parse ROM filenames
- [Platforms](guides/platforms.md) - Platform slug mappings

### Architecture
- [Overview](architecture/overview.md) - System architecture
- [Library Design](architecture/library.md) - Core library design
- [Providers](architecture/providers.md) - Provider implementation
- [Caching](architecture/caching.md) - Cache backend design

### Development
- [Migration](development/migration.md) - Syncing with RomM upstream

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
| Gamelist | No (local XML) | EmulationStation gamelist.xml |

### Getting API Keys

- **IGDB**: Create a Twitch developer app at https://dev.twitch.tv/console
- **MobyGames**: Request at https://www.mobygames.com/info/api/
- **ScreenScraper**: Register at https://screenscraper.fr/
- **RetroAchievements**: Get from your profile at https://retroachievements.org/
- **SteamGridDB**: Get at https://www.steamgriddb.com/profile/preferences/api
- **TheGamesDB**: Request at https://thegamesdb.net/

## UI Applications

- **CLI**: `pip install retro-metadata-cli`
- **TUI**: `pip install retro-metadata-tui`
- **Desktop**: `pip install retro-metadata-qt`
- **Web**: `pip install retro-metadata-web`

## License

MIT License
