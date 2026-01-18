# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Consumer Applications                              │
├─────────────┬─────────────┬─────────────┬─────────────┬────────────────────┤
│ retro-      │ retro-      │ retro-      │ retro-      │ RomM               │
│ metadata-   │ metadata-   │ metadata-   │ metadata-   │ (via adapter)      │
│ cli         │ qt          │ tui         │ web         │                    │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴─────────┬──────────┘
       │             │             │             │                │
       └─────────────┴─────────────┼─────────────┴────────────────┘
                                   │
                         ┌─────────▼─────────┐
                         │   retro-metadata  │
                         │   (core library)  │
                         └─────────┬─────────┘
                                   │
       ┌───────────────────────────┼───────────────────────────┐
       │                           │                           │
  ┌────▼────┐    ┌────────────────▼────────────────┐    ┌────▼────┐
  │Providers│    │         Core Modules            │    │ Artwork │
  │  (12+)  │    │ ┌──────┐ ┌──────┐ ┌──────────┐ │    │Subsystem│
  └────┬────┘    │ │Cache │ │Types │ │Platforms │ │    └────┬────┘
       │         │ └──────┘ └──────┘ └──────────┘ │         │
       │         └────────────────────────────────┘         │
       │                           │                        │
       └───────────────────────────┼────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      External APIs          │
                    │  IGDB, ScreenScraper, etc.  │
                    └─────────────────────────────┘
```

## Package Structure

```
retro_metadata/
├── __init__.py              # Public API exports
├── core/                    # Core functionality
│   ├── client.py           # MetadataClient - main entry point
│   ├── config.py           # Configuration dataclasses
│   ├── exceptions.py       # Exception hierarchy
│   ├── matching.py         # String similarity algorithms
│   ├── normalization.py    # Text normalization
│   └── hashing.py          # File hash calculations
├── providers/               # Metadata provider implementations
│   ├── base.py             # MetadataProvider abstract base class
│   ├── igdb.py             # IGDB provider
│   ├── mobygames.py        # MobyGames provider
│   ├── screenscraper.py    # ScreenScraper provider
│   ├── retroachievements.py # RetroAchievements provider
│   ├── steamgriddb.py      # SteamGridDB provider
│   ├── hltb.py             # HowLongToBeat provider
│   ├── thegamesdb.py       # TheGamesDB provider
│   ├── hasheous.py         # Hasheous hash lookup
│   ├── flashpoint.py       # Flashpoint database
│   ├── playmatch.py        # Playmatch hash lookup
│   ├── launchbox.py        # LaunchBox local XML
│   └── gamelist.py         # EmulationStation gamelist.xml
├── types/                   # Type definitions
│   ├── common.py           # Shared types (GameResult, SearchResult, etc.)
│   └── [provider].py       # Provider-specific types
├── artwork/                 # Artwork management subsystem
│   ├── config.py           # ArtworkConfig
│   ├── downloader.py       # ArtworkDownloader
│   ├── cache.py            # Artwork file caching
│   ├── utils.py            # Image utilities
│   └── exceptions.py       # Artwork-specific exceptions
├── cache/                   # Metadata cache backends
│   ├── base.py             # CacheBackend abstract base class
│   ├── memory.py           # In-memory LRU cache
│   ├── redis.py            # Redis backend
│   └── sqlite.py           # SQLite backend
└── platforms/               # Platform definitions
    ├── slugs.py            # UniversalPlatformSlug enum
    └── mappings.py         # Provider platform ID mappings
```

## Core Components

### MetadataClient

The `MetadataClient` is the main entry point and facade for the library. It provides:

- **Unified Search**: Search across all enabled providers
- **ROM Identification**: Multiple identification strategies
- **Provider Management**: Lazy initialization and lifecycle
- **Platform Mapping**: Universal slugs to provider-specific IDs

```python
async with MetadataClient(config) as client:
    # Search across providers
    results = await client.search("Zelda", platform="snes")

    # Identify by filename
    game = await client.identify("game.sfc", platform="snes")

    # Hash-based identification
    game = await client.identify_by_hash(platform="snes", md5="...")

    # Smart identification (combines hash + filename)
    game = await client.identify_smart(filename="game.sfc", platform="snes", md5="...")
```

### Provider System

Each metadata source is implemented as a provider extending `MetadataProvider`:

| Provider | Source | Auth | Hash Support |
|----------|--------|------|--------------|
| IGDB | Twitch/IGDB API | OAuth | No |
| MobyGames | MobyGames API | API Key | No |
| ScreenScraper | ScreenScraper API | User/Pass | Yes |
| RetroAchievements | RA API | API Key | Yes |
| SteamGridDB | SteamGridDB API | API Key | No |
| HLTB | HowLongToBeat | None | No |
| TheGamesDB | TGDB API | None | No |
| Hasheous | Hasheous API | None | Yes |
| Playmatch | Playmatch API | None | Yes |
| Flashpoint | Flashpoint DB | None | No |
| LaunchBox | Local XML | None | No |
| Gamelist | Local XML | None | No |

### Cache Layer

The cache layer sits between the client and providers:

```
Client → Cache Check → Provider → External API
                ↓
            Cache Store
```

Available backends:
- **MemoryCache**: In-memory LRU cache with TTL and background cleanup
- **RedisCache**: Distributed Redis cache for multi-instance deployments
- **SQLiteCache**: Persistent SQLite cache for single-instance use
- **NullCache**: No caching (passthrough for testing)

### Type System

All data is strongly typed using:

- **Dataclasses** for configuration and internal objects
- **TypedDict** for provider API responses
- **NamedTuple** for immutable data like hash results
- **Pydantic models** (optional) for validation

Key types:
- `GameResult` - Full game metadata with artwork
- `SearchResult` - Lightweight search result
- `Artwork` - Artwork URL container
- `GameMetadata` - Extended metadata (genres, ratings, etc.)

## Data Flow

### Search Flow

```
1. Client.search("Mario", platform="snes")
2. Map platform slug to provider-specific IDs
3. For each enabled provider (respecting priority):
   a. Check cache for query
   b. If cache miss, call provider.search()
   c. Provider makes HTTP request to external API
   d. Response parsed into SearchResult objects
   e. Store results in cache
4. Merge results from all providers
5. Return list of SearchResult
```

### Identification Flow

```
1. Client.identify("Super Mario World (USA).sfc", platform="snes")
2. Clean filename: remove region tags, version, extension
   → "Super Mario World"
3. For each provider (in priority order):
   a. provider.identify(clean_name, platform_id)
   b. Provider searches by cleaned name
   c. Calculate Jaro-Winkler similarity for each result
   d. If best match > threshold (0.75), return it
4. Return best GameResult or None
```

### Hash-Based Identification Flow

```
1. Client.identify_by_hash(platform, md5, sha1, crc, filename)
2. Try hash-capable providers in order:
   a. ScreenScraper (MD5, SHA1, CRC, file_size)
   b. RetroAchievements (MD5)
   c. Playmatch (MD5, SHA1) → fetches IGDB details
   d. Hasheous (MD5, SHA1, CRC)
3. Return first successful match or None
```

### Smart Identification Flow

```
1. Client.identify_smart(filename, platform, md5, sha1, crc)
2. If hashes provided:
   a. Try identify_by_hash()
   b. If found, calculate name similarity with filename
   c. If similarity >= 0.6: return with match_type="hash+filename"
   d. Else: return with match_type="hash"
3. Fall back to identify() by filename
   a. If require_unique=True: only accept if unambiguous
4. Return GameResult with match_type set
```

## Platform Mapping

Universal platform slugs map to provider-specific IDs:

```python
UniversalPlatformSlug.SNES → {
    "igdb": 19,
    "mobygames": 15,
    "screenscraper": 4,
    "retroachievements": 3,
    ...
}
```

This allows applications to use consistent platform identifiers (`snes`, `n64`, `ps2`) regardless of which provider is being queried.

## Artwork Subsystem

The artwork module provides:

- **ArtworkDownloader**: Downloads artwork with caching
- **Cross-provider matching**: Identify with one provider, get artwork from another
- **Batch processing**: Process entire ROM directories
- **Image transformation**: Resize and optimize images

```python
async with ArtworkDownloader(client, config) as downloader:
    # Download artwork for identified game
    paths = await downloader.download_for_game(game, output_dir)

    # Cross-provider: identify with IGDB, get art from SteamGridDB
    paths = await downloader.download_with_fallback(
        filename="game.sfc",
        platform="snes",
        identify_providers=["igdb"],
        artwork_providers=["steamgriddb"],
    )
```

## Design Principles

### 1. Async-First
All I/O operations use async/await for non-blocking execution. This allows efficient concurrent requests to multiple providers.

### 2. Provider Abstraction
Providers implement a common interface, making it easy to add new sources without changing client code.

### 3. Graceful Degradation
If a provider fails, others continue. The client handles partial failures and returns best available results.

### 4. Caching by Default
Results are cached to reduce API calls. Cache backends are pluggable for different deployment scenarios.

### 5. Type Safety
Full type hints throughout the codebase enable IDE support and catch errors early.

## Extension Points

### Adding Providers

1. Create provider class extending `MetadataProvider`
2. Implement required methods: `search()`, `identify()`, `get_by_id()`
3. Add platform ID mappings in `platforms/mappings.py`
4. Register in `MetadataClient._init_providers()`

See [Adding Providers](../development/adding-providers.md) for details.

### Adding Cache Backends

1. Create class extending `CacheBackend`
2. Implement: `get()`, `set()`, `delete()`, `exists()`, `clear()`
3. Add initialization in `MetadataClient._initialize()`

See [Caching](caching.md) for details.

## Related Documentation

- [Library Design](library.md) - Detailed module documentation
- [Providers](providers.md) - Provider implementation details
- [Caching](caching.md) - Cache backend architecture
