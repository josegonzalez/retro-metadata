# Platform Support Guide

retro-metadata uses universal platform slugs that automatically map to provider-specific IDs.

## Python

```python
from retro_metadata.platforms import UniversalPlatformSlug

# Use slug string directly
results = await client.search("Zelda", platform="snes")

# Or use the enum
results = await client.search("Zelda", platform=UniversalPlatformSlug.SNES)

# List all supported platforms
for slug in UniversalPlatformSlug:
    print(f"{slug.value}: {slug.name}")
```

## Go

```go
import "github.com/josegonzalez/retro-metadata/pkg/platform"

// Use slug string directly
results, _ := client.Search(ctx, "Zelda", retrometadata.SearchOptions{
    Platform: "snes",
})

// Or use the constant
results, _ := client.Search(ctx, "Zelda", retrometadata.SearchOptions{
    Platform: platform.SNES,
})

// Get platform info
info := platform.GetPlatformInfo("snes")
fmt.Println(info.Name)  // "Super Nintendo Entertainment System"

// Get provider-specific ID
igdbID := platform.GetIGDBPlatformID("snes")  // 19
```

## C++

```cpp
#include <retro_metadata/platform/slug.hpp>
#include <retro_metadata/platform/mapping.hpp>

using namespace retro_metadata::platform;

// Use slug constant
SearchOptions opts;
opts.platform_id = get_igdb_platform_id(kSNES);

// Get platform info
auto info = get_platform_info("snes");
if (info) {
    std::cout << info->name << "\n";  // "Super Nintendo Entertainment System"
}

// Get provider-specific IDs
int igdb_id = get_igdb_platform_id("snes");           // 19
int moby_id = get_mobygames_platform_id("snes");      // 15
int ss_id = get_screenscraper_platform_id("snes");    // 4

// Reverse lookup from provider ID
auto slug = slug_from_igdb_id(19);  // Returns "snes"

// List all platforms
auto all_slugs = get_all_platform_slugs();
for (const auto& slug : all_slugs) {
    std::cout << slug << "\n";
}
```

## Supported Platforms

### Nintendo

| Slug | Name | IGDB ID |
|------|------|---------|
| `nes` | Nintendo Entertainment System | 18 |
| `snes` | Super Nintendo | 19 |
| `n64` | Nintendo 64 | 4 |
| `gamecube` | GameCube | 21 |
| `wii` | Wii | 5 |
| `wiiu` | Wii U | 41 |
| `switch` | Nintendo Switch | 130 |
| `gb` | Game Boy | 33 |
| `gbc` | Game Boy Color | 22 |
| `gba` | Game Boy Advance | 24 |
| `nds` | Nintendo DS | 20 |
| `3ds` | Nintendo 3DS | 37 |
| `virtualboy` | Virtual Boy | 87 |

### Sony

| Slug | Name | IGDB ID |
|------|------|---------|
| `ps1` | PlayStation | 7 |
| `ps2` | PlayStation 2 | 8 |
| `ps3` | PlayStation 3 | 9 |
| `ps4` | PlayStation 4 | 48 |
| `ps5` | PlayStation 5 | 167 |
| `psp` | PlayStation Portable | 38 |
| `vita` | PlayStation Vita | 46 |

### Sega

| Slug | Name | IGDB ID |
|------|------|---------|
| `genesis` | Sega Genesis/Mega Drive | 29 |
| `sms` | Sega Master System | 64 |
| `gamegear` | Game Gear | 35 |
| `saturn` | Sega Saturn | 32 |
| `dreamcast` | Dreamcast | 23 |
| `segacd` | Sega CD | 78 |
| `sega32x` | Sega 32X | 30 |

### Microsoft

| Slug | Name | IGDB ID |
|------|------|---------|
| `xbox` | Xbox | 11 |
| `xbox360` | Xbox 360 | 12 |
| `xboxone` | Xbox One | 49 |
| `xboxseries` | Xbox Series X|S | 169 |

### Other

| Slug | Name | IGDB ID |
|------|------|---------|
| `arcade` | Arcade | 52 |
| `pc` | PC (Windows) | 6 |
| `mac` | Mac | 14 |
| `linux` | Linux | 3 |
| `dos` | DOS | 13 |
| `atari2600` | Atari 2600 | 59 |
| `atari7800` | Atari 7800 | 60 |
| `neogeo` | Neo Geo | 80 |
| `turbografx16` | TurboGrafx-16 | 86 |
| `3do` | 3DO | 50 |
| `jaguar` | Atari Jaguar | 62 |

## Provider ID Mappings

Each provider uses different platform IDs. The library handles this automatically:

```cpp
// These all refer to the same platform (SNES)
get_igdb_platform_id("snes");           // 19
get_mobygames_platform_id("snes");      // 15
get_screenscraper_platform_id("snes");  // 4
get_retroachievements_platform_id("snes"); // 3
get_thegamesdb_platform_id("snes");     // 6
```

## Adding Custom Platforms

For platforms not in the default list, you can use provider IDs directly:

```cpp
SearchOptions opts;
opts.platform_id = 999;  // Custom provider-specific ID
auto results = provider->search("Game Name", opts);
```
