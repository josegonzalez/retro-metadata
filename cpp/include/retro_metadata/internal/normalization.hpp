#pragma once

/// @file normalization.hpp
/// @brief Text normalization utilities for game name matching

#include <map>
#include <string>
#include <string_view>
#include <vector>

namespace retro_metadata {
namespace normalization {

/// @brief Normalizes a search term for comparison
///
/// Performs the following transformations:
/// - Converts to lowercase
/// - Replaces underscores with spaces
/// - Optionally removes articles (a, an, the)
/// - Optionally removes punctuation
/// - Normalizes Unicode characters and removes accents
///
/// @param name The search term to normalize
/// @param remove_articles Whether to remove leading articles
/// @param remove_punctuation Whether to remove punctuation
/// @return The normalized search term
[[nodiscard]] std::string normalize_search_term(
    std::string_view name, bool remove_articles = true, bool remove_punctuation = true);

/// @brief Normalizes a search term with default options (remove articles and punctuation)
[[nodiscard]] std::string normalize_search_term_default(std::string_view name);

/// @brief Normalizes a cover image URL to ensure consistent format
[[nodiscard]] std::string normalize_cover_url(std::string_view cover_url);

/// @brief Splits a search term by common delimiters (colon, dash, slash, ampersand)
[[nodiscard]] std::vector<std::string> split_search_term(std::string_view name);

/// @brief Normalizes a search term for API queries
[[nodiscard]] std::string normalize_for_api(std::string_view search_term);

/// @brief Removes diacritical marks from Unicode characters
[[nodiscard]] std::string remove_accents(std::string_view str);

/// @brief Checks if a string contains non-ASCII characters
[[nodiscard]] bool has_non_ascii(std::string_view str);

/// @brief Strips sensitive query parameters from a URL for logging
///
/// @param raw_url The URL to sanitize
/// @param custom_sensitive_keys Optional custom keys to also strip (in addition to defaults)
/// @return The URL with sensitive parameters removed
[[nodiscard]] std::string strip_sensitive_query_params(
    std::string_view raw_url,
    const std::map<std::string, bool>& custom_sensitive_keys = {});

/// @brief Masks sensitive values for safe logging
///
/// @param values Map of header/parameter names to values
/// @return Map with sensitive values masked (e.g., "ab***cd")
[[nodiscard]] std::map<std::string, std::string> mask_sensitive_values(
    const std::map<std::string, std::string>& values);

/// @brief Default sensitive keys that should be masked in URLs
extern const std::map<std::string, bool> kDefaultSensitiveKeys;

}  // namespace normalization
}  // namespace retro_metadata
