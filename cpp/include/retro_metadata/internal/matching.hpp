#pragma once

/// @file matching.hpp
/// @brief String matching utilities using Jaro-Winkler similarity

#include <string>
#include <string_view>
#include <vector>

namespace retro_metadata {
namespace matching {

/// @brief Default minimum similarity score for a match
constexpr double kDefaultMinSimilarity = 0.75;

/// @brief Calculates the Jaro-Winkler similarity between two strings
///
/// The comparison is case-insensitive and returns a value between 0 and 1,
/// where 1 indicates an exact match.
///
/// @param s1 First string
/// @param s2 Second string
/// @return Similarity score between 0 and 1
[[nodiscard]] double jaro_winkler_similarity(std::string_view s1, std::string_view s2);

/// @brief Options for FindBestMatch
struct FindBestMatchOptions {
    /// Minimum similarity score to consider a match
    double min_similarity_score = kDefaultMinSimilarity;
    /// Split candidates by delimiters and match against last part
    bool split_candidate_name = false;
    /// Normalize strings before comparison
    bool normalize = true;
    /// Limit matching to the first N candidates (0 = no limit)
    int first_n_only = 0;
};

/// @brief Returns sensible defaults for FindBestMatch
[[nodiscard]] FindBestMatchOptions default_find_best_match_options();

/// @brief Result of FindBestMatch
struct BestMatchResult {
    /// The best matching name, or empty if no match above threshold
    std::string match;
    /// Similarity score (0-1), or 0 if no match
    double score = 0.0;

    /// Check if a match was found
    [[nodiscard]] bool found() const { return !match.empty() && score > 0; }
};

/// @brief Finds the best matching name from a list of candidates
///
/// @param search_term The term to search for
/// @param candidates List of candidate names
/// @param opts Match options
/// @return The best match and its score, or empty if no match meets threshold
[[nodiscard]] BestMatchResult find_best_match(
    std::string_view search_term,
    const std::vector<std::string>& candidates,
    const FindBestMatchOptions& opts = {});

/// @brief Convenience function that uses default options
[[nodiscard]] BestMatchResult find_best_match_simple(
    std::string_view search_term, const std::vector<std::string>& candidates);

/// @brief A match result with name and score
struct MatchResult {
    std::string name;
    double score = 0.0;
};

/// @brief Finds all matching names above the minimum similarity threshold
///
/// Results are sorted by score in descending order.
///
/// @param search_term The term to search for
/// @param candidates List of candidate names
/// @param min_score Minimum similarity score
/// @param max_results Maximum number of results to return (0 = unlimited)
/// @return List of matches sorted by score descending
[[nodiscard]] std::vector<MatchResult> find_all_matches(
    std::string_view search_term,
    const std::vector<std::string>& candidates,
    double min_score = kDefaultMinSimilarity,
    int max_results = 0);

/// @brief Checks if two strings are an exact match after normalization
[[nodiscard]] bool is_exact_match(std::string_view s1, std::string_view s2, bool normalize = true);

/// @brief Match confidence level
enum class MatchConfidence {
    Exact,   ///< Exact match after normalization
    High,    ///< Score >= 0.95
    Medium,  ///< Score >= 0.85
    Low,     ///< Score >= 0.75
    None     ///< Score < 0.75
};

/// @brief Returns a human-readable confidence level for a match
[[nodiscard]] MatchConfidence match_confidence(
    std::string_view search_term, std::string_view matched_name, bool normalize = true);

/// @brief Converts MatchConfidence to string
[[nodiscard]] std::string to_string(MatchConfidence confidence);

}  // namespace matching
}  // namespace retro_metadata
