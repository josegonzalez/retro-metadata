// Example: Filename Parsing
//
// This example demonstrates how to parse ROM filenames to extract
// game information, regions, tags, and other metadata.
//
// To run:
//   ./filename_parsing

#include <iostream>
#include <retro_metadata/filename/filename.hpp>
#include <string>
#include <vector>

int main() {
    using namespace retro_metadata::filename;

    // Example ROM filenames
    std::vector<std::string> examples = {
        "Super Mario World (USA).sfc",
        "Legend of Zelda, The - A Link to the Past (USA, Europe) (Rev 1).sfc",
        "Sonic the Hedgehog (Japan, Korea).md",
        "Pokemon - Red Version (USA, Europe) (SGB Enhanced).gb",
        "Chrono Trigger (USA) [!].sfc",
        "Final Fantasy VI (Japan) (Beta).sfc",
        "Street Fighter II' Turbo - Hyper Fighting (USA) (Virtual Console).sfc",
    };

    for (const auto& rom_filename : examples) {
        std::cout << "Filename: " << rom_filename << "\n";
        std::cout << "------------------------------------------------\n";

        // Get file extension
        auto ext = get_file_extension(rom_filename);
        std::cout << "  Extension: " << ext << "\n";

        // Extract region
        auto region = extract_region(rom_filename);
        std::cout << "  Region: " << region << "\n";

        // Extract tags (parenthesized content)
        auto tags = extract_tags(rom_filename);
        if (!tags.empty()) {
            std::cout << "  Tags: [";
            for (size_t i = 0; i < tags.size(); ++i) {
                if (i > 0) std::cout << ", ";
                std::cout << "\"" << tags[i] << "\"";
            }
            std::cout << "]\n";
        }

        // Clean the filename (remove extension and tags)
        auto clean_name = clean_filename(rom_filename, true);
        std::cout << "  Clean Name: " << clean_name << "\n";

        // Check if it's a BIOS file
        if (is_bios_file(rom_filename)) {
            std::cout << "  Note: This is a BIOS file\n";
        }

        // Check if it's a demo
        if (is_demo_file(rom_filename)) {
            std::cout << "  Note: This is a demo/beta file\n";
        }

        // Check if it's unlicensed
        if (is_unlicensed(rom_filename)) {
            std::cout << "  Note: This is an unlicensed ROM\n";
        }

        std::cout << "\n";
    }

    // No-Intro filename parsing example
    std::cout << "=================================================\n";
    std::cout << "No-Intro Filename Parsing\n";
    std::cout << "=================================================\n";

    std::vector<std::string> no_intro_examples = {
        "Super Mario World (USA).sfc",
        "Legend of Zelda, The - A Link to the Past (USA, Europe) (Rev 1).sfc",
    };

    for (const auto& rom_filename : no_intro_examples) {
        std::cout << "\nFilename: " << rom_filename << "\n";
        auto parsed = parse_no_intro_filename(rom_filename);
        std::cout << "  Name: " << parsed.clean_name << "\n";
        std::cout << "  Region: " << parsed.region << "\n";
        if (!parsed.version.empty()) {
            std::cout << "  Version: " << parsed.version << "\n";
        }
        if (!parsed.tags.empty()) {
            std::cout << "  Tags: [";
            for (size_t i = 0; i < parsed.tags.size(); ++i) {
                if (i > 0) std::cout << ", ";
                std::cout << "\"" << parsed.tags[i] << "\"";
            }
            std::cout << "]\n";
        }
        if (!parsed.languages.empty()) {
            std::cout << "  Languages: [";
            for (size_t i = 0; i < parsed.languages.size(); ++i) {
                if (i > 0) std::cout << ", ";
                std::cout << "\"" << parsed.languages[i] << "\"";
            }
            std::cout << "]\n";
        }
    }

    return 0;
}
