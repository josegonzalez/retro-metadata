# Quick Start Guide

This guide shows how to get started with retro-metadata in Python, Go, and C++.

## Python

### Installation

```bash
# Using uv (recommended)
uv venv && source .venv/bin/activate
uv pip install -e .

# Using pip
pip install retro-metadata

# With optional dependencies
pip install retro-metadata[redis]   # Redis cache
pip install retro-metadata[sqlite]  # SQLite cache
pip install retro-metadata[all]     # All optional deps
```

### Basic Usage

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

## Go

### Installation

```bash
go get github.com/josegonzalez/retro-metadata/pkg/retrometadata
```

### Basic Usage

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/josegonzalez/retro-metadata/pkg/retrometadata"
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

## C++

### Installation

```bash
# Clone and build
git clone https://github.com/josegonzalez/retro-metadata.git
cd retro-metadata/cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel

# Optional: Install system-wide
sudo cmake --install build
```

### CMake Integration

```cmake
# Option 1: FetchContent (recommended)
include(FetchContent)
FetchContent_Declare(
    retro_metadata
    GIT_REPOSITORY https://github.com/josegonzalez/retro-metadata.git
    GIT_TAG main
    SOURCE_SUBDIR cpp
)
FetchContent_MakeAvailable(retro_metadata)
target_link_libraries(your_target PRIVATE retro_metadata)

# Option 2: find_package (if installed)
find_package(retro_metadata REQUIRED)
target_link_libraries(your_target PRIVATE retro_metadata::retro_metadata)
```

### Basic Usage

```cpp
#include <iostream>
#include <retro_metadata/config.hpp>
#include <retro_metadata/cache/memory.hpp>
#include <retro_metadata/provider/registry.hpp>

int main() {
    using namespace retro_metadata;

    // Configure provider
    ProviderConfig config;
    config.enabled = true;
    config.credentials["client_id"] = "your_twitch_client_id";
    config.credentials["client_secret"] = "your_twitch_client_secret";
    config.timeout = std::chrono::seconds(30);

    // Optional: Create a cache
    auto cache = std::make_shared<cache::MemoryCache>(1000, std::chrono::minutes(30));

    // Create provider using registry
    auto provider = Registry::instance().create("igdb", config, cache);
    if (!provider) {
        std::cerr << "Failed to create provider\n";
        return 1;
    }

    // Search for games
    SearchOptions opts;
    opts.limit = 5;

    try {
        auto results = provider->search("Super Mario World", opts);
        for (const auto& result : results) {
            std::cout << result.name << " (" << result.provider << ")\n";
        }

        // Identify a ROM file
        IdentifyOptions id_opts;
        auto game = provider->identify("Super Mario World (USA).sfc", id_opts);
        if (game) {
            std::cout << "Identified: " << game->name << "\n";
            if (game->metadata.total_rating) {
                std::cout << "Rating: " << *game->metadata.total_rating << "/100\n";
            }
        }

        // Get by provider ID
        auto game_by_id = provider->get_by_id(1234);
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
```

### Dependencies

- CMake 3.20+
- C++20 compiler (GCC 12+, Clang 15+, MSVC 2022+)
- libcurl (for HTTP requests)
- ICU (optional, for Unicode normalization)

## Next Steps

- [Caching](caching.md) - Configure cache backends
- [Filename Parsing](filename-parsing.md) - Parse ROM filenames
- [Platforms](platforms.md) - Platform slug mappings
- [Providers](../architecture/providers.md) - Available providers and API keys
