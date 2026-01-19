# Caching Guide

retro-metadata supports multiple cache backends to reduce API calls and improve performance.

## Python

### In-Memory Cache (Default)

```python
from retro_metadata import MetadataConfig, CacheConfig

config = MetadataConfig(
    cache=CacheConfig(backend="memory", ttl=86400, max_size=1000)
)
```

### Redis Cache

```bash
pip install retro-metadata[redis]
```

```python
from retro_metadata import MetadataConfig, CacheConfig

config = MetadataConfig(
    cache=CacheConfig(backend="redis", connection_string="redis://localhost")
)
```

### SQLite Cache

```bash
pip install retro-metadata[sqlite]
```

```python
from retro_metadata import MetadataConfig, CacheConfig

config = MetadataConfig(
    cache=CacheConfig(backend="sqlite", connection_string="metadata_cache.db")
)
```

## Go

### In-Memory Cache (Default)

```go
import (
    "github.com/josegonzalez/retro-metadata/pkg/retrometadata"
)

config := &retrometadata.Config{
    Cache: &retrometadata.CacheConfig{
        Backend: "memory",
        TTL:     86400,
        MaxSize: 1000,
    },
}
```

### Redis Cache

```go
config := &retrometadata.Config{
    Cache: &retrometadata.CacheConfig{
        Backend:          "redis",
        ConnectionString: "redis://localhost",
    },
}
```

### SQLite Cache

```go
config := &retrometadata.Config{
    Cache: &retrometadata.CacheConfig{
        Backend:          "sqlite",
        ConnectionString: "metadata_cache.db",
    },
}
```

## C++

### In-Memory Cache with LRU

```cpp
#include <retro_metadata/cache/memory.hpp>

// Create cache with max 1000 entries and 30-minute TTL
auto cache = std::make_shared<cache::MemoryCache>(
    1000,                           // max_size
    std::chrono::minutes(30)        // ttl
);

// Use with provider
auto provider = Registry::instance().create("igdb", config, cache);

// Check cache statistics
auto stats = cache->stats();
std::cout << "Hits: " << stats.hits << ", Misses: " << stats.misses << "\n";
std::cout << "Hit rate: " << (stats.hit_rate() * 100) << "%\n";
```

### Cache Interface

The C++ cache implements the following interface:

```cpp
class Cache {
public:
    virtual ~Cache() = default;

    // Get a value from cache
    virtual std::optional<std::string> get(const std::string& key) = 0;

    // Set a value in cache
    virtual void set(const std::string& key, const std::string& value) = 0;

    // Remove a value from cache
    virtual void remove(const std::string& key) = 0;

    // Check if key exists
    virtual bool exists(const std::string& key) = 0;

    // Clear all entries
    virtual void clear() = 0;

    // Get statistics
    virtual CacheStats stats() const = 0;

    // Close the cache
    virtual void close() = 0;
};
```

## Cache Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `backend` | Cache backend type (memory, redis, sqlite) | memory |
| `ttl` | Time-to-live in seconds | 86400 (24 hours) |
| `max_size` | Maximum number of entries (memory only) | 1000 |
| `connection_string` | Connection URL (redis/sqlite) | - |

## Best Practices

1. **Use appropriate TTL**: Game metadata rarely changes, so longer TTLs (24-72 hours) are usually safe.

2. **Size the cache appropriately**: For large ROM collections, increase `max_size` to avoid cache thrashing.

3. **Consider persistence**: For applications that restart frequently, use Redis or SQLite to preserve cache across restarts.

4. **Monitor hit rates**: Low hit rates may indicate the cache is too small or TTL is too short.
