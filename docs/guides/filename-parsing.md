# Filename Parsing Guide

retro-metadata includes utilities for parsing ROM filenames, particularly No-Intro naming conventions.

## Python

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

# Clean a filename (remove tags and extension)
clean = clean_filename("Game (USA) [!].sfc")
print(clean)  # "Game"

# Extract region from filename
region = extract_region("Zelda (Europe).sfc")
print(region)  # "eu"

# Check for BIOS files
is_bios = is_bios_file("[BIOS] PlayStation.bin")
print(is_bios)  # True

# Check for demo/sample files
is_demo = is_demo_file("Game (Demo).sfc")
print(is_demo)  # True

# Check for unlicensed ROMs
is_unlicensed = is_unlicensed_file("Game (Unl).sfc")
print(is_unlicensed)  # True
```

## Go

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

// Check for demo files
isDemo := filename.IsDemoFile("Game (Demo).sfc")
fmt.Println(isDemo)  // true

// Check for unlicensed ROMs
isUnlicensed := filename.IsUnlicensedFile("Game (Unl).sfc")
fmt.Println(isUnlicensed)  // true
```

## C++

```cpp
#include <retro_metadata/filename/filename.hpp>

using namespace retro_metadata::filename;

// Parse a No-Intro filename
auto info = parse_no_intro_filename("Super Mario World (USA) (Rev 1).sfc");
std::cout << info.clean_name << "\n";  // "Super Mario World"
std::cout << info.region << "\n";      // "USA"
std::cout << info.extension << "\n";   // "sfc"

// Access parsed tags
for (const auto& tag : info.tags) {
    std::cout << "Tag: " << tag << "\n";
}

// Clean a filename
auto clean = clean_filename("Game (USA) [!].sfc", true);
std::cout << clean << "\n";  // "Game"

// Extract region
auto region = extract_region("Zelda (Europe).sfc");
std::cout << region << "\n";  // "Europe"

// Check for special file types
bool is_bios = is_bios_file("[BIOS] PlayStation.bin");
bool is_demo = is_demo_file("Game (Demo).sfc");
bool is_unlicensed = is_unlicensed_file("Game (Unl).sfc");

// Get file extension
auto ext = get_file_extension("game.sfc");
std::cout << ext << "\n";  // "sfc"

// Extract all tags from filename
auto tags = extract_tags("Game (USA) (Rev 1) [!].sfc");
for (const auto& tag : tags) {
    std::cout << tag << "\n";  // "USA", "Rev 1", "!"
}
```

## ParsedFilename Structure

The parsed filename contains:

| Field | Description | Example |
|-------|-------------|---------|
| `name` / `clean_name` | Game name without tags | "Super Mario World" |
| `region` | Detected region code | "USA", "Europe", "Japan" |
| `version` | Version/revision info | "Rev 1", "v1.1" |
| `tags` | All parenthetical tags | ["USA", "Rev 1"] |
| `flags` | Square bracket flags | ["!"] |
| `extension` | File extension | "sfc" |

## Region Codes

The library recognizes these region tags and normalizes them:

| Tag | Normalized Code |
|-----|-----------------|
| USA, US, America | us |
| Europe, EU, EUR | eu |
| Japan, JP, JPN | jp |
| World | world |
| Korea, KR | kr |
| China, CN | cn |
| Germany, DE | de |
| France, FR | fr |
| Spain, ES | es |
| Italy, IT | it |

## Special File Detection

| Function | Detects |
|----------|---------|
| `is_bios_file` | BIOS files: `[BIOS]` prefix |
| `is_demo_file` | Demo/sample: `(Demo)`, `(Sample)`, `(Proto)` |
| `is_unlicensed_file` | Unlicensed: `(Unl)`, `(Pirate)` |
| `is_beta_file` | Beta versions: `(Beta)`, `(Beta 1)` |
| `is_hack_file` | ROM hacks: `(Hack)`, `[h]` |
