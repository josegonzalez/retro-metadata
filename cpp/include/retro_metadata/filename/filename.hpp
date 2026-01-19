#pragma once

/// @file filename.hpp
/// @brief Filename parsing utilities for ROM files

#include <map>
#include <string>
#include <string_view>
#include <vector>

namespace retro_metadata {
namespace filename {

/// @brief Region tag mappings from common indicators to normalized codes
extern const std::map<std::string, std::string> kRegionTags;

/// @brief Returns the file extension from a filename (without the dot, lowercased)
[[nodiscard]] std::string get_file_extension(std::string_view filename);

/// @brief Extracts all tags from a filename
///
/// Tags are text within parentheses () or brackets [].
///
/// @param filename The filename to extract tags from
/// @return List of extracted tags
[[nodiscard]] std::vector<std::string> extract_tags(std::string_view filename);

/// @brief Extracts the region code from a filename
///
/// @param filename The filename to extract region from
/// @return Normalized region code (us, eu, jp, etc.) or empty string if not found
[[nodiscard]] std::string extract_region(std::string_view filename);

/// @brief Cleans a filename by removing tags and optionally the extension
///
/// @param filename The filename to clean
/// @param remove_extension Whether to remove the file extension
/// @return Cleaned filename
[[nodiscard]] std::string clean_filename(std::string_view filename, bool remove_extension);

/// @brief Components parsed from a No-Intro filename
struct ParsedFilename {
    /// Cleaned game name
    std::string name;
    /// Normalized region code (us, eu, jp, etc.)
    std::string region;
    /// Version tag if found (e.g., "Rev 1", "v1.1")
    std::string version;
    /// List of language tags
    std::vector<std::string> languages;
    /// File extension
    std::string extension;
    /// All extracted tags
    std::vector<std::string> tags;
};

/// @brief Parses a No-Intro naming convention filename
///
/// No-Intro filenames follow the format:
/// Title (Region) (Language) (Version) (Other Tags).ext
///
/// @param filename The filename to parse
/// @return Parsed filename components
[[nodiscard]] ParsedFilename parse_no_intro_filename(std::string_view filename);

/// @brief Checks if a filename appears to be a BIOS file
[[nodiscard]] bool is_bios_file(std::string_view filename);

/// @brief Checks if a filename appears to be a demo, prototype, or beta
[[nodiscard]] bool is_demo_file(std::string_view filename);

/// @brief Checks if a filename indicates an unlicensed game
[[nodiscard]] bool is_unlicensed(std::string_view filename);

}  // namespace filename
}  // namespace retro_metadata
