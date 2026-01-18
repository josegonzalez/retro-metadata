# Provider Architecture

This document details the provider system architecture, including the base class contract, implemented providers, and guidelines for adding new providers.

## Provider Base Class

All providers extend `MetadataProvider`, an abstract base class that defines the contract for metadata sources.

### Abstract Base Class (`providers/base.py`)

```python
from abc import ABC, abstractmethod

class MetadataProvider(ABC):
    """Abstract base class for metadata providers."""

    name: str  # Provider identifier (e.g., "igdb", "screenscraper")

    def __init__(
        self,
        config: ProviderConfig,
        cache: CacheBackend | None = None,
    ) -> None:
        self.config = config
        self.cache = cache
        self._min_similarity_score = 0.75

    # === Abstract Methods (must implement) ===

    @abstractmethod
    async def search(
        self,
        query: str,
        platform_id: str | int | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search for games by query string."""

    @abstractmethod
    async def get_by_id(
        self,
        game_id: str | int,
    ) -> GameResult | None:
        """Get full game details by provider-specific ID."""

    @abstractmethod
    async def identify(
        self,
        filename: str,
        platform_id: str | int | None = None,
    ) -> GameResult | None:
        """Identify a game from ROM filename."""

    # === Optional Methods (can override) ===

    async def heartbeat(self) -> bool:
        """Check if provider API is accessible.

        Default implementation returns True.
        Override for providers with heartbeat endpoints.
        """
        return True

    async def close(self) -> None:
        """Clean up resources (HTTP clients, etc.)."""
        pass

    # === Utility Methods (available to all providers) ===

    def normalize_search_term(self, term: str) -> str:
        """Normalize text using core.normalization."""

    def find_best_match(
        self,
        search_term: str,
        candidates: list[SearchResult],
    ) -> SearchResult | None:
        """Find best match using Jaro-Winkler similarity."""

    def normalize_cover_url(self, url: str | None) -> str | None:
        """Ensure URL has https:// prefix."""

    def extract_id_from_filename(
        self,
        filename: str,
        pattern: str,
    ) -> str | None:
        """Extract provider ID from filename using regex."""

    def split_search_term(self, term: str) -> list[str]:
        """Split term by common delimiters (colon, dash, slash)."""

    # === Cache Integration ===

    async def _get_cached(self, key: str) -> Any | None:
        """Get from cache with provider-namespaced key."""
        if self.cache:
            return await self.cache.get(f"{self.name}:{key}")
        return None

    async def _set_cached(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Store in cache with provider-namespaced key."""
        if self.cache:
            await self.cache.set(
                f"{self.name}:{key}",
                value,
                ttl=ttl or self.config.timeout,
            )
```

## Provider Registry

Providers are registered for dynamic lookup:

```python
class ProviderRegistry:
    _providers: dict[str, type[MetadataProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[MetadataProvider]) -> None:
        cls._providers[name] = provider_class

    @classmethod
    def get(cls, name: str) -> type[MetadataProvider] | None:
        return cls._providers.get(name)

    @classmethod
    def list_providers(cls) -> list[str]:
        return list(cls._providers.keys())
```

## Implemented Providers

### Online Providers (API-based)

#### 1. IGDB Provider (`providers/igdb.py`)

**API**: Twitch/IGDB API v4
**Authentication**: OAuth2 (client_id, client_secret)

```python
class IGDBProvider(MetadataProvider):
    name = "igdb"

    CREDENTIALS = ["client_id", "client_secret"]
    ID_TAG_FORMAT = "(igdb-{id})"

    async def _get_access_token(self) -> str:
        """OAuth token refresh with caching."""

    async def _api_request(
        self,
        endpoint: str,
        body: str,
    ) -> list[dict]:
        """Make IGDB API request with auth."""
```

**Features**:
- Comprehensive game data (metadata, artwork, related games)
- Support for complex queries (APICALYPSE syntax)
- Related games: expansions, DLCs, remakes, remasters
- Multiplayer mode details
- Age ratings

**Platform Mapping**: Uses IGDB platform IDs (integers)

---

#### 2. MobyGames Provider (`providers/mobygames.py`)

**API**: MobyGames REST API
**Authentication**: API Key

```python
class MobyGamesProvider(MetadataProvider):
    name = "mobygames"

    CREDENTIALS = ["api_key"]
    ID_TAG_FORMAT = "(moby-{id})"
```

**Features**:
- Classic games database
- Platform-specific game info
- Alternative names

**Rate Limiting**: Strict rate limits; respect `Retry-After` headers

---

#### 3. ScreenScraper Provider (`providers/screenscraper.py`)

**API**: ScreenScraper v2 API
**Authentication**: Username/Password + Developer credentials

```python
class ScreenScraperProvider(MetadataProvider):
    name = "screenscraper"

    CREDENTIALS = ["username", "password"]
    ID_TAG_FORMAT = "(ssfr-{id})"

    # Built-in developer credentials
    DEV_ID = "..."
    DEV_PASSWORD = "..."

    async def lookup_by_hash(
        self,
        platform_id: int,
        md5: str | None = None,
        sha1: str | None = None,
        crc: str | None = None,
        file_size: int | None = None,
    ) -> GameResult | None:
        """Hash-based ROM identification."""

    def add_auth_to_url(self, url: str) -> str:
        """Add authentication to media URLs."""
```

**Features**:
- **Hash-based identification** (MD5, SHA1, CRC32)
- Region-specific metadata
- Multiple screenshot types
- Localized content (region_priority support)

**Special Handling**:
- Media URLs require authentication
- Region/language priority lists
- File size validation for hash lookups

---

#### 4. RetroAchievements Provider (`providers/retroachievements.py`)

**API**: RetroAchievements Web API
**Authentication**: API Key + Username

```python
class RetroAchievementsProvider(MetadataProvider):
    name = "retroachievements"

    CREDENTIALS = ["api_key", "username"]
    ID_TAG_FORMAT = "(ra-{id})"

    async def lookup_by_hash(
        self,
        md5: str,
    ) -> GameResult | None:
        """MD5-based ROM identification."""
```

**Features**:
- **Hash-based identification** (MD5)
- Achievement data integration
- Verified ROM database

---

#### 5. SteamGridDB Provider (`providers/steamgriddb.py`)

**API**: SteamGridDB API
**Authentication**: API Key

```python
class SteamGridDBProvider(MetadataProvider):
    name = "steamgriddb"

    CREDENTIALS = ["api_key"]

    # Artwork types supported
    GRID_TYPES = ["grid", "hero", "logo", "icon"]
```

**Features**:
- Artwork-focused provider
- Multiple artwork dimensions
- Community-contributed artwork
- Style filtering (alternate, blurred, material, etc.)

**Use Case**: Best for artwork, not game metadata

---

#### 6. HowLongToBeat Provider (`providers/hltb.py`)

**API**: HowLongToBeat (unofficial scraping)
**Authentication**: None

```python
class HLTBProvider(MetadataProvider):
    name = "hltb"

    # No credentials required
```

**Features**:
- Game duration estimates
- Main story, completionist, and all styles times

**Limitations**: No hash support, limited metadata

---

#### 7. TheGamesDB Provider (`providers/thegamesdb.py`)

**API**: TheGamesDB API
**Authentication**: None (API key optional)

**Features**:
- Classic games database
- Box art and screenshots

---

#### 8. Hasheous Provider (`providers/hasheous.py`)

**API**: Hasheous API
**Authentication**: None

```python
class HasheousProvider(MetadataProvider):
    name = "hasheous"

    async def lookup_by_hash(
        self,
        md5: str | None = None,
        sha1: str | None = None,
        crc: str | None = None,
    ) -> GameResult | None:
        """Hash-only ROM identification."""
```

**Features**:
- **Hash-based identification** (MD5, SHA1, CRC32)
- Community-maintained hash database

**Use Case**: Hash verification, ROM identification

---

#### 9. Flashpoint Provider (`providers/flashpoint.py`)

**API**: Flashpoint Archive
**Authentication**: None

**Features**:
- Web game preservation database
- Flash/HTML5 game metadata

---

#### 10. Playmatch Provider (`providers/playmatch.py`)

**API**: Playmatch API
**Authentication**: None

```python
class PlaymatchProvider(MetadataProvider):
    name = "playmatch"

    async def lookup_by_hash(
        self,
        filename: str,
        file_size: int,
        md5: str | None = None,
        sha1: str | None = None,
    ) -> GameResult | None:
        """Returns IGDB ID for matched ROM."""
```

**Features**:
- **Hash-based identification**
- Returns IGDB IDs (can fetch full details from IGDB)
- Filename + size matching

**Special**: Acts as a bridge to IGDB via hash lookup

---

### Local Providers (File-based)

#### 11. LaunchBox Provider (`providers/launchbox.py`)

**Source**: Local LaunchBox XML metadata
**Authentication**: None

```python
class LaunchBoxProvider(MetadataProvider):
    name = "launchbox"

    def __init__(self, config: ProviderConfig, ...):
        self.metadata_path = Path(config.options.get("metadata_path", ""))
        self._games_index: dict[str, dict] = {}
        self._platforms: dict[str, str] = {}

    async def _load_metadata(self) -> None:
        """Parse LaunchBox XML into memory indices."""

    ID_TAG_FORMAT = "(launchbox-{id})"
```

**Features**:
- Loads locally stored LaunchBox XML
- In-memory indices for fast lookup
- No API calls required

**Configuration**:
```python
launchbox=ProviderConfig(
    enabled=True,
    options={"metadata_path": "/path/to/LaunchBox/Metadata"}
)
```

---

#### 12. Gamelist Provider (`providers/gamelist.py`)

**Source**: EmulationStation gamelist.xml files
**Authentication**: None

```python
class GamelistProvider(MetadataProvider):
    name = "gamelist"

    async def identify(
        self,
        filename: str,
        platform_id: str | None = None,
        gamelist_path: Path | None = None,
    ) -> GameResult | None:
        """Match ROM to gamelist.xml entry."""
```

**Features**:
- Parses EmulationStation gamelist.xml format
- ROM path-based matching
- Local artwork references

## Hash-Capable Providers

Providers with hash-based identification:

| Provider | MD5 | SHA1 | CRC32 | File Size |
|----------|-----|------|-------|-----------|
| ScreenScraper | ✓ | ✓ | ✓ | ✓ |
| RetroAchievements | ✓ | - | - | - |
| Hasheous | ✓ | ✓ | ✓ | - |
| Playmatch | ✓ | ✓ | - | ✓ |

### Hash Lookup Priority

The client tries hash-capable providers in this order:

1. **ScreenScraper** - Most comprehensive ROM database
2. **RetroAchievements** - Verified ROMs with achievements
3. **Playmatch** - Links to IGDB metadata
4. **Hasheous** - Community hash database

## Provider ID Tags

Some providers support embedding IDs in filenames for direct lookup:

```
Super Mario World (igdb-1234).sfc
The Legend of Zelda (ssfr-5678).z64
Metroid (ra-9012).nes
```

Patterns:
- IGDB: `(igdb-{id})`
- ScreenScraper: `(ssfr-{id})`
- RetroAchievements: `(ra-{id})`
- MobyGames: `(moby-{id})`
- LaunchBox: `(launchbox-{id})`

The `extract_id_from_filename()` method handles parsing.

## Error Handling

### Provider Exceptions

```python
# Authentication failure
raise ProviderAuthenticationError(
    provider="igdb",
    message="Invalid client credentials"
)

# Network/connection issues
raise ProviderConnectionError(
    provider="screenscraper",
    message="Connection timeout"
)

# Rate limiting
raise ProviderRateLimitError(
    provider="mobygames",
    message="Rate limit exceeded",
    retry_after=60  # seconds
)
```

### Graceful Degradation

The client handles provider failures gracefully:

```python
async def search(self, query: str, ...) -> list[SearchResult]:
    results = []
    for provider in self._providers.values():
        try:
            provider_results = await provider.search(query, ...)
            results.extend(provider_results)
        except ProviderError as e:
            logger.warning("Provider %s failed: %s", provider.name, e)
            continue  # Try next provider
    return results
```

## Adding New Providers

### Step 1: Create Provider Class

```python
# providers/newprovider.py
from retro_metadata.providers.base import MetadataProvider
from retro_metadata.types.common import GameResult, SearchResult

class NewProvider(MetadataProvider):
    name = "newprovider"

    CREDENTIALS = ["api_key"]  # Required credentials
    BASE_URL = "https://api.newprovider.com/v1"

    def __init__(self, config: ProviderConfig, cache=None):
        super().__init__(config, cache)
        self._http_client = None

    async def search(
        self,
        query: str,
        platform_id: str | int | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        # Implement search logic
        pass

    async def get_by_id(self, game_id: str | int) -> GameResult | None:
        # Implement get_by_id logic
        pass

    async def identify(
        self,
        filename: str,
        platform_id: str | int | None = None,
    ) -> GameResult | None:
        # Use search + best match
        clean_name = self._clean_filename(filename)
        results = await self.search(clean_name, platform_id, limit=5)
        return self.find_best_match(clean_name, results)

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
```

### Step 2: Add Platform Mappings

```python
# platforms/mappings.py
NEWPROVIDER_PLATFORM_IDS = {
    UniversalPlatformSlug.NES: "nintendo-nes",
    UniversalPlatformSlug.SNES: "nintendo-snes",
    # ...
}

def get_newprovider_platform_id(slug: str) -> str | None:
    return NEWPROVIDER_PLATFORM_IDS.get(slug)
```

### Step 3: Register in Client

```python
# core/client.py
def _init_providers(self) -> None:
    # ... existing providers ...

    if self.config.newprovider.enabled:
        from retro_metadata.providers.newprovider import NewProvider
        self._providers["newprovider"] = NewProvider(
            self.config.newprovider,
            self._cache,
        )
```

### Step 4: Add Configuration

```python
# core/config.py
@dataclass
class MetadataConfig:
    # ... existing providers ...
    newprovider: ProviderConfig = field(default_factory=ProviderConfig)
```

### Step 5: Export (Optional)

```python
# __init__.py
from retro_metadata.providers.newprovider import NewProvider
```

## Best Practices

### 1. Use Caching
```python
async def search(self, query: str, ...) -> list[SearchResult]:
    cache_key = f"search:{query}:{platform_id}"
    cached = await self._get_cached(cache_key)
    if cached:
        return cached

    results = await self._api_search(query, platform_id)
    await self._set_cached(cache_key, results)
    return results
```

### 2. Handle Rate Limits
```python
async def _api_request(self, ...):
    try:
        response = await self._http_client.get(url)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise ProviderRateLimitError(
                provider=self.name,
                retry_after=retry_after,
            )
        return response.json()
    except httpx.RequestError as e:
        raise ProviderConnectionError(provider=self.name, message=str(e))
```

### 3. Normalize Data
```python
def _to_game_result(self, data: dict) -> GameResult:
    return GameResult(
        name=data.get("title", ""),
        provider=self.name,
        provider_id=str(data["id"]),
        artwork=Artwork(
            cover_url=self.normalize_cover_url(data.get("cover")),
        ),
        # ... normalize all fields
    )
```

### 4. Log Appropriately
```python
logger = logging.getLogger(__name__)

async def identify(self, filename: str, ...) -> GameResult | None:
    logger.debug("Identifying '%s' via %s", filename, self.name)
    # ...
    if result:
        logger.debug("Found match: %s (score: %.2f)", result.name, result.match_score)
    else:
        logger.debug("No match found for '%s'", filename)
    return result
```
