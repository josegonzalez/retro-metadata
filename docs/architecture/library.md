# Library Design

This document details the internal design of the retro-metadata library, covering the core modules, type system, and key implementation patterns.

## Core Module: `core/`

### MetadataClient (`core/client.py`)

The `MetadataClient` is the primary interface for consuming the library. It implements the **Facade pattern**, providing a simplified API that orchestrates providers, caching, and matching.

#### Key Responsibilities

1. **Provider Lifecycle Management**
   - Lazy initialization on first async operation
   - Graceful shutdown via context manager
   - Dynamic provider instantiation based on configuration

2. **Search Orchestration**
   - Routes queries to enabled providers
   - Merges and deduplicates results
   - Handles provider failures gracefully

3. **Identification Algorithms**
   - Multiple strategies: filename, hash, smart (combined)
   - Provider priority ordering
   - Similarity threshold enforcement

4. **Platform Translation**
   - Maps universal slugs to provider-specific IDs
   - Handles missing platform mappings gracefully

#### Class Structure

```python
class MetadataClient:
    def __init__(self, config: MetadataConfig) -> None:
        self.config = config
        self._providers: dict[str, MetadataProvider] = {}
        self._cache: CacheBackend | None = None
        self._initialized = False

    async def __aenter__(self) -> "MetadataClient":
        await self._initialize()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    # Public API
    async def search(...) -> list[SearchResult]: ...
    async def identify(...) -> GameResult | None: ...
    async def identify_by_hash(...) -> GameResult | None: ...
    async def identify_smart(...) -> GameResult | None: ...
    async def get_by_id(...) -> GameResult | None: ...
    async def heartbeat() -> dict[str, bool]: ...

    # Internal
    async def _initialize() -> None: ...
    def _init_providers() -> None: ...
    def _get_platform_id(provider, platform) -> str | int | None: ...
```

#### Initialization Flow

```
MetadataClient(config)
    │
    ▼ (lazy, on first async operation)
_initialize()
    │
    ├── Create cache backend (memory/redis/sqlite/none)
    │
    └── _init_providers()
            │
            ├── For each provider in config:
            │   ├── Check if enabled
            │   ├── Check if credentials configured
            │   └── Instantiate provider class
            │
            └── Sort by priority
```

### Configuration (`core/config.py`)

Configuration uses **dataclasses** for type safety and immutability.

#### ProviderConfig

```python
@dataclass
class ProviderConfig:
    enabled: bool = False
    credentials: dict[str, str] = field(default_factory=dict)
    priority: int = 100
    timeout: int = 30
    rate_limit: float = 1.0
    options: dict[str, Any] = field(default_factory=dict)

    def get_credential(self, key: str, default: str = "") -> str:
        return self.credentials.get(key, default)

    @property
    def is_configured(self) -> bool:
        # Provider-specific validation
        return self.enabled
```

#### MetadataConfig

```python
@dataclass
class MetadataConfig:
    # Provider configurations (one per provider)
    igdb: ProviderConfig = field(default_factory=ProviderConfig)
    mobygames: ProviderConfig = field(default_factory=ProviderConfig)
    screenscraper: ProviderConfig = field(default_factory=ProviderConfig)
    # ... 9 more providers

    # Cache configuration
    cache: CacheConfig = field(default_factory=CacheConfig)

    # Global settings
    user_agent: str = "retro-metadata/1.0"
    default_timeout: int = 30
    max_concurrent_requests: int = 10
    preferred_locale: str = "en"
    region_priority: list[str] = field(default_factory=lambda: ["us", "wor", "eu", "jp"])

    def get_enabled_providers(self) -> list[str]:
        """Return list of enabled provider names."""

    @classmethod
    def from_dict(cls, data: dict) -> "MetadataConfig":
        """Create config from dictionary (JSON/YAML)."""

    def to_dict(self) -> dict:
        """Serialize config to dictionary."""
```

### String Matching (`core/matching.py`)

The matching module provides fuzzy string matching using the **Jaro-Winkler algorithm**, which is well-suited for game title matching.

```python
from strsimpy.jaro_winkler import JaroWinkler

_jaro_winkler = JaroWinkler()

def find_best_match(
    search_term: str,
    candidates: list[str],
    min_similarity_score: float = 0.75,
    split_candidates: bool = False,
) -> tuple[str | None, float]:
    """Find best matching candidate for search term.

    Args:
        search_term: The term to match
        candidates: List of candidate strings
        min_similarity_score: Minimum score threshold (0-1)
        split_candidates: If True, also try matching against
                         split versions of candidates (e.g., "Title: Subtitle")

    Returns:
        Tuple of (best_match, score) or (None, 0.0)
    """
```

**Why Jaro-Winkler?**
- Gives higher scores to strings matching from the beginning (important for game titles)
- Handles transpositions well
- Fast computation for short strings
- Threshold of 0.75 balances precision and recall

### Text Normalization (`core/normalization.py`)

Normalization prepares strings for comparison by removing noise.

```python
@lru_cache(maxsize=10000)
def normalize_search_term(
    term: str,
    remove_articles: bool = True,
    remove_punctuation: bool = True,
) -> str:
    """Normalize text for comparison.

    Transformations:
    1. Convert to lowercase
    2. Replace underscores with spaces
    3. Remove articles (a, an, the) - optional
    4. Remove punctuation - optional
    5. Unicode normalization (NFD)
    6. Remove diacritical marks (accents)
    7. Collapse whitespace

    Results are cached for performance.
    """
```

### File Hashing (`core/hashing.py`)

Provides efficient file hash calculation for ROM identification.

```python
class FileHashes(NamedTuple):
    md5: str
    sha1: str
    crc32: str
    file_size: int

def calculate_hashes(
    file_path: Path,
    chunk_size: int = 8192,
) -> FileHashes:
    """Calculate MD5, SHA1, and CRC32 hashes.

    Uses streaming to handle large files efficiently.
    """

# Convenience functions for single hash types
def calculate_md5(file_path: Path) -> str: ...
def calculate_sha1(file_path: Path) -> str: ...
def calculate_crc32(file_path: Path) -> str: ...
```

### Exception Hierarchy (`core/exceptions.py`)

```
MetadataError (base)
├── ProviderNotFoundError
├── ProviderAuthenticationError
├── ProviderConnectionError
├── ProviderRateLimitError
│   └── retry_after: int | None
├── GameNotFoundError
├── InvalidConfigurationError
└── CacheError
```

All exceptions include:
- Human-readable message
- Provider name (when applicable)
- Original exception (when wrapping)

## Type System: `types/`

### Common Types (`types/common.py`)

#### GameResult

The primary result type containing full game metadata.

```python
@dataclass
class GameResult:
    # Identity
    name: str
    provider: str
    provider_id: str | int
    provider_ids: dict[str, str | int] = field(default_factory=dict)
    slug: str = ""

    # Content
    summary: str = ""
    artwork: Artwork = field(default_factory=Artwork)
    metadata: GameMetadata = field(default_factory=GameMetadata)

    # Match info
    match_score: float = 0.0
    match_type: str = ""  # "hash+filename", "hash", "filename", etc.

    # Raw data (for debugging/extensions)
    raw_response: dict = field(default_factory=dict)

    # Convenience properties
    @property
    def cover_url(self) -> str | None:
        return self.artwork.cover_url

    @property
    def screenshot_urls(self) -> list[str]:
        return self.artwork.screenshot_urls or []
```

#### SearchResult

Lightweight result for search listings.

```python
@dataclass
class SearchResult:
    name: str
    provider: str
    provider_id: str | int
    slug: str = ""
    cover_url: str | None = None
    platforms: list[str] = field(default_factory=list)
    release_year: int | None = None
    match_score: float = 0.0
```

#### Artwork

Container for artwork URLs.

```python
@dataclass
class Artwork:
    cover_url: str | None = None
    banner_url: str | None = None
    icon_url: str | None = None
    logo_url: str | None = None
    background_url: str | None = None
    screenshot_urls: list[str] | None = None
```

#### GameMetadata

Extended metadata container.

```python
@dataclass
class GameMetadata:
    # Ratings
    total_rating: float | None = None
    aggregated_rating: float | None = None

    # Release info
    first_release_date: int | None = None  # Unix timestamp
    release_year: int | None = None

    # Classification
    genres: list[str] = field(default_factory=list)
    franchises: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    alternative_names: list[str] = field(default_factory=list)

    # Companies
    developer: str | None = None
    publisher: str | None = None
    companies: list[str] = field(default_factory=list)

    # Gameplay
    game_modes: list[str] = field(default_factory=list)
    player_count: str | None = None
    multiplayer_modes: list[MultiplayerMode] = field(default_factory=list)

    # Age ratings
    age_ratings: list[AgeRating] = field(default_factory=list)

    # Related games
    platforms: list[Platform] = field(default_factory=list)
    expansions: list[RelatedGame] = field(default_factory=list)
    dlcs: list[RelatedGame] = field(default_factory=list)
    remasters: list[RelatedGame] = field(default_factory=list)
    remakes: list[RelatedGame] = field(default_factory=list)
    ports: list[RelatedGame] = field(default_factory=list)
    similar_games: list[RelatedGame] = field(default_factory=list)

    # Media
    youtube_video_id: str | None = None

    # Raw provider data
    raw_data: dict = field(default_factory=dict)
```

## Platform System: `platforms/`

### Universal Platform Slugs (`platforms/slugs.py`)

```python
class UniversalPlatformSlug(StrEnum):
    # Nintendo
    NES = "nes"
    SNES = "snes"
    N64 = "n64"
    GAMECUBE = "gamecube"
    WII = "wii"
    WIIU = "wiiu"
    SWITCH = "switch"
    GB = "gb"
    GBC = "gbc"
    GBA = "gba"
    NDS = "nds"
    N3DS = "3ds"

    # Sony
    PS1 = "psx"
    PS2 = "ps2"
    PS3 = "ps3"
    PS4 = "ps4"
    PS5 = "ps5"
    PSP = "psp"
    VITA = "vita"

    # ... 300+ platform definitions
```

### Platform Mappings (`platforms/mappings.py`)

Maps universal slugs to provider-specific IDs:

```python
IGDB_PLATFORM_IDS = {
    UniversalPlatformSlug.NES: 18,
    UniversalPlatformSlug.SNES: 19,
    UniversalPlatformSlug.N64: 4,
    # ...
}

SCREENSCRAPER_PLATFORM_IDS = {
    UniversalPlatformSlug.NES: 3,
    UniversalPlatformSlug.SNES: 4,
    UniversalPlatformSlug.N64: 14,
    # ...
}

def get_igdb_platform_id(slug: str) -> int | None: ...
def get_screenscraper_platform_id(slug: str) -> int | None: ...
def get_mobygames_platform_id(slug: str) -> int | None: ...
# ...
```

## Artwork Subsystem: `artwork/`

### ArtworkConfig (`artwork/config.py`)

```python
ARTWORK_TYPES = frozenset({
    "cover",
    "screenshots",
    "banner",
    "icon",
    "logo",
    "background",
})

@dataclass
class ArtworkConfig:
    cache_dir: Path | None = None
    cache_enabled: bool = True
    cache_ttl: int = 2592000  # 30 days

    max_width: int | None = None
    max_height: int | None = None

    filename_format: str = "extended"  # or "simple"
    artwork_types: list[str] = field(
        default_factory=lambda: ["cover"]
    )

    timeout: int = 30
    max_concurrent: int = 5

    def get_cache_dir(self) -> Path:
        """Get cache directory, creating if needed."""

    def ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
```

### ArtworkDownloader (`artwork/downloader.py`)

```python
class ArtworkDownloader:
    def __init__(
        self,
        client: MetadataClient,
        config: ArtworkConfig | None = None,
    ) -> None:
        self.client = client
        self.config = config or ArtworkConfig()
        self._cache = ArtworkCache(self.config)
        self._http_client: httpx.AsyncClient | None = None
        self._semaphore: asyncio.Semaphore | None = None

    async def download_for_game(
        self,
        game: GameResult,
        output_dir: Path,
        rom_filename: str | None = None,
        artwork_types: list[str] | None = None,
    ) -> dict[str, Path]:
        """Download artwork for a game using its embedded URLs."""

    async def download_with_fallback(
        self,
        filename: str,
        platform: str,
        output_dir: Path,
        identify_providers: list[str] | None = None,
        artwork_providers: list[str] | None = None,
        artwork_types: list[str] | None = None,
        game_name: str | None = None,
    ) -> dict[str, Path]:
        """Download artwork with cross-provider support.

        If game_name is provided, skips identification and uses
        the name directly to search in artwork_providers.
        """

    async def download_batch(
        self,
        directory: Path,
        platform: str,
        output_dir: Path,
        recursive: bool = False,
        extensions: list[str] | None = None,
        progress_callback: Callable | None = None,
    ) -> ArtworkBatchResult:
        """Process entire directory of ROMs."""
```

### ArtworkCache (`artwork/cache.py`)

SQLite-backed persistent cache for downloaded images.

```python
@dataclass
class CachedArtwork:
    url: str
    provider: str
    path: Path
    width: int | None
    height: int | None
    download_date: int  # Unix timestamp
    expires_at: int     # Unix timestamp

class ArtworkCache:
    def __init__(self, config: ArtworkConfig) -> None:
        self.config = config
        self._db_path = config.get_cache_dir() / "index.db"

    async def get(self, url: str) -> CachedArtwork | None:
        """Get cached artwork by URL."""

    async def put(
        self,
        url: str,
        provider: str,
        data: bytes,
        content_type: str | None = None,
    ) -> CachedArtwork:
        """Store artwork in cache."""

    async def get_stats(self) -> dict:
        """Get cache statistics."""

    async def clear_expired(self) -> int:
        """Remove expired entries."""
```

## Design Patterns Used

### 1. Facade Pattern
`MetadataClient` provides a simplified interface to the complex subsystem of providers, caching, and matching.

### 2. Strategy Pattern
Cache backends implement a common interface, allowing runtime selection of caching strategy.

### 3. Template Method Pattern
`MetadataProvider` defines the algorithm structure, with concrete providers implementing specific steps.

### 4. Registry Pattern
Providers are registered by name, enabling dynamic lookup and instantiation.

### 5. Builder Pattern (Configuration)
`MetadataConfig.from_dict()` enables building configuration from various sources.

### 6. Null Object Pattern
`NullCache` provides a no-op cache implementation for testing or disabled caching.

## Performance Considerations

### Caching Strategy
- Provider results cached by query + platform + provider
- Artwork cached by URL with 30-day TTL
- Memory cache uses LRU eviction with configurable max size

### Concurrency
- Semaphore limits concurrent downloads (default: 5)
- Providers can specify per-provider rate limits
- HTTP clients reused for connection pooling

### Lazy Loading
- Providers initialized on first use
- Cache backend created on demand
- Platform mappings loaded once per import

### String Operations
- Normalization results cached via `@lru_cache`
- Jaro-Winkler instance reused (singleton)
- Hash calculations use streaming for large files
