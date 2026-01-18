# Syncing with RomM Upstream

This document describes how to keep the retro-metadata library synchronized with changes in RomM's metadata scraping code.

## Overview

The retro-metadata library was extracted from RomM's codebase. While the library is designed to be independent, it should track relevant improvements and fixes from RomM upstream.

## File Mappings

The `migration/file_map.yaml` file defines the relationship between RomM source files and library modules:

```yaml
mappings:
  - source: backend/handler/metadata/base_handler.py
    targets:
      - module: core/matching.py
        functions: [find_best_match, _jaro_winkler_similarity]
```

## Using the Sync Script

### Check for Changes

```bash
# Check for changes (dry run)
python scripts/sync_upstream.py --romm-path /path/to/romm --check-only

# Output:
# Found 3 relevant change(s):
#   - backend/handler/metadata/igdb_handler.py (modified)
#     Affects: providers/igdb.py, platforms/mappings.py
```

### Generate Diff Report

```bash
# Generate markdown report
python scripts/sync_upstream.py --generate-diff -o migration_report.md
```

### Compare Against Specific Commit

```bash
# Check changes since a specific commit
python scripts/sync_upstream.py --since abc123
```

## Manual Sync Process

1. **Run the sync check**:
   ```bash
   python scripts/sync_upstream.py --romm-path ../romm --check-only
   ```

2. **Review the changes**:
   - Read the diff report
   - Identify breaking vs non-breaking changes
   - Note any new features or bug fixes

3. **Apply safe changes**:
   - Copy updated type definitions
   - Update platform mappings
   - Apply bug fixes

4. **Handle breaking changes**:
   - Update library API if needed
   - Add deprecation warnings
   - Update documentation

5. **Test thoroughly**:
   ```bash
   pytest tests/
   ```

6. **Update version compatibility**:
   - Update `migration/file_map.yaml`
   - Document in CHANGELOG

## What to Sync

### Always Sync
- Type definitions (`*_types.py`)
- Platform ID mappings
- Bug fixes in matching logic
- New provider features

### Review Before Syncing
- API changes to handlers
- New dependencies
- Database model changes

### Don't Sync
- RomM-specific code (database operations, web endpoints)
- Configuration that's RomM-specific
- Test fixtures that depend on RomM infrastructure

## Version Compatibility Matrix

| retro-metadata | RomM | Notes |
|----------------|------|-------|
| 0.1.x | 3.x | Initial extraction |

## Handling Breaking Changes

When RomM makes breaking changes:

1. Create a compatibility layer if possible
2. Document migration steps
3. Bump library minor/major version
4. Update all UI packages to match

## Contributing Changes Back

If you fix a bug or add a feature to retro-metadata:

1. Verify it applies to RomM's use case
2. Create a PR to RomM with the same change
3. Reference both PRs in documentation
