#!/usr/bin/env python3
"""Example: Filename Parsing

This example demonstrates how to parse ROM filenames to extract
game information, regions, tags, and other metadata.

To run:
    python main.py
"""

from __future__ import annotations

from retro_metadata.utils import clean_filename, extract_region, extract_tags, get_file_extension
from retro_metadata.utils.filename import (
    is_bios_file,
    is_demo_file,
    is_unlicensed,
    parse_no_intro_filename,
)


def main() -> None:
    # Example ROM filenames
    examples = [
        "Super Mario World (USA).sfc",
        "Legend of Zelda, The - A Link to the Past (USA, Europe) (Rev 1).sfc",
        "Sonic the Hedgehog (Japan, Korea).md",
        "Pokemon - Red Version (USA, Europe) (SGB Enhanced).gb",
        "Chrono Trigger (USA) [!].sfc",
        "Final Fantasy VI (Japan) (Beta).sfc",
        "Street Fighter II' Turbo - Hyper Fighting (USA) (Virtual Console).sfc",
    ]

    for rom_filename in examples:
        print(f"Filename: {rom_filename}")
        print("────────────────────────────────────────────────")

        # Get file extension
        ext = get_file_extension(rom_filename)
        print(f"  Extension: {ext}")

        # Extract region
        region = extract_region(rom_filename)
        print(f"  Region: {region}")

        # Extract tags (parenthesized content)
        tags = extract_tags(rom_filename)
        if tags:
            print(f"  Tags: {tags}")

        # Clean the filename (remove extension and tags)
        clean_name = clean_filename(rom_filename, remove_extension=True)
        print(f"  Clean Name: {clean_name}")

        # Check if it's a BIOS file
        if is_bios_file(rom_filename):
            print("  Note: This is a BIOS file")

        # Check if it's a demo
        if is_demo_file(rom_filename):
            print("  Note: This is a demo/beta file")

        # Check if it's unlicensed
        if is_unlicensed(rom_filename):
            print("  Note: This is an unlicensed ROM")

        print()

    # No-Intro filename parsing example
    print("═══════════════════════════════════════════════")
    print("No-Intro Filename Parsing")
    print("═══════════════════════════════════════════════")

    no_intro_examples = [
        "Super Mario World (USA).sfc",
        "Legend of Zelda, The - A Link to the Past (USA, Europe) (Rev 1).sfc",
    ]

    for rom_filename in no_intro_examples:
        print(f"\nFilename: {rom_filename}")
        parsed = parse_no_intro_filename(rom_filename)
        print(f"  Name: {parsed['name']}")
        print(f"  Region: {parsed['region']}")
        if parsed.get("version"):
            print(f"  Version: {parsed['version']}")
        if parsed.get("tags"):
            print(f"  Tags: {parsed['tags']}")
        if parsed.get("languages"):
            print(f"  Languages: {parsed['languages']}")


if __name__ == "__main__":
    main()
