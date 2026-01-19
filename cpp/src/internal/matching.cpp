#include <retro_metadata/internal/matching.hpp>
#include <retro_metadata/internal/normalization.hpp>

#include <rapidfuzz/fuzz.hpp>

#include <algorithm>
#include <cctype>

namespace retro_metadata {
namespace matching {

namespace {

std::string to_lower(std::string_view str) {
    std::string result(str);
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

std::string trim(std::string_view str) {
    const auto start = str.find_first_not_of(" \t\n\r");
    if (start == std::string_view::npos) return "";
    const auto end = str.find_last_not_of(" \t\n\r");
    return std::string(str.substr(start, end - start + 1));
}

}  // namespace

double jaro_winkler_similarity(std::string_view s1, std::string_view s2) {
    std::string lower1 = to_lower(s1);
    std::string lower2 = to_lower(s2);
    // rapidfuzz returns 0-100, normalize to 0-1
    return rapidfuzz::fuzz::ratio(lower1, lower2) / 100.0;
}

FindBestMatchOptions default_find_best_match_options() {
    return FindBestMatchOptions{
        .min_similarity_score = kDefaultMinSimilarity,
        .split_candidate_name = false,
        .normalize = true,
        .first_n_only = 0};
}

BestMatchResult find_best_match(
    std::string_view search_term,
    const std::vector<std::string>& candidates,
    const FindBestMatchOptions& opts) {
    if (candidates.empty()) {
        return BestMatchResult{};
    }

    // Normalize the search term once
    std::string search_normalized;
    if (opts.normalize) {
        search_normalized = normalization::normalize_search_term_default(std::string(search_term));
    } else {
        search_normalized = trim(to_lower(search_term));
    }

    // Determine which candidates to check
    size_t limit = candidates.size();
    if (opts.first_n_only > 0 && static_cast<size_t>(opts.first_n_only) < limit) {
        limit = static_cast<size_t>(opts.first_n_only);
    }

    std::string best_match;
    double best_score = 0.0;

    for (size_t i = 0; i < limit; ++i) {
        const std::string& candidate = candidates[i];

        // Normalize the candidate name
        std::string candidate_normalized;
        if (opts.normalize) {
            candidate_normalized = normalization::normalize_search_term_default(candidate);
        } else {
            candidate_normalized = trim(to_lower(candidate));
        }

        // If split mode is enabled, try the last part
        if (opts.split_candidate_name) {
            auto parts = normalization::split_search_term(candidate);
            if (parts.size() > 1) {
                const std::string& last_part = parts.back();
                if (opts.normalize) {
                    candidate_normalized = normalization::normalize_search_term_default(last_part);
                } else {
                    candidate_normalized = trim(to_lower(last_part));
                }
            }
        }

        // Calculate similarity
        double score = jaro_winkler_similarity(search_normalized, candidate_normalized);

        if (score > best_score) {
            best_score = score;
            best_match = candidate;

            // Early exit for perfect match
            if (score == 1.0) {
                break;
            }
        }
    }

    if (best_score >= opts.min_similarity_score) {
        return BestMatchResult{.match = best_match, .score = best_score};
    }

    return BestMatchResult{};
}

BestMatchResult find_best_match_simple(
    std::string_view search_term, const std::vector<std::string>& candidates) {
    return find_best_match(search_term, candidates, default_find_best_match_options());
}

std::vector<MatchResult> find_all_matches(
    std::string_view search_term,
    const std::vector<std::string>& candidates,
    double min_score,
    int max_results) {
    if (candidates.empty()) {
        return {};
    }

    // Normalize the search term once
    std::string search_normalized = normalization::normalize_search_term_default(std::string(search_term));

    std::vector<MatchResult> matches;

    for (const auto& candidate : candidates) {
        std::string candidate_normalized = normalization::normalize_search_term_default(candidate);
        double score = jaro_winkler_similarity(search_normalized, candidate_normalized);

        if (score >= min_score) {
            matches.push_back(MatchResult{.name = candidate, .score = score});
        }
    }

    // Sort by score descending
    std::sort(matches.begin(), matches.end(),
              [](const MatchResult& a, const MatchResult& b) { return a.score > b.score; });

    if (max_results > 0 && static_cast<size_t>(max_results) < matches.size()) {
        matches.resize(static_cast<size_t>(max_results));
    }

    return matches;
}

bool is_exact_match(std::string_view s1, std::string_view s2, bool normalize) {
    if (normalize) {
        return normalization::normalize_search_term_default(std::string(s1)) ==
               normalization::normalize_search_term_default(std::string(s2));
    }
    return trim(to_lower(s1)) == trim(to_lower(s2));
}

MatchConfidence match_confidence(
    std::string_view search_term, std::string_view matched_name, bool normalize) {
    std::string s1, s2;
    if (normalize) {
        s1 = normalization::normalize_search_term_default(std::string(search_term));
        s2 = normalization::normalize_search_term_default(std::string(matched_name));
    } else {
        s1 = trim(to_lower(search_term));
        s2 = trim(to_lower(matched_name));
    }

    if (s1 == s2) {
        return MatchConfidence::Exact;
    }

    double score = jaro_winkler_similarity(s1, s2);

    if (score >= 0.95) return MatchConfidence::High;
    if (score >= 0.85) return MatchConfidence::Medium;
    if (score >= 0.75) return MatchConfidence::Low;
    return MatchConfidence::None;
}

std::string to_string(MatchConfidence confidence) {
    switch (confidence) {
    case MatchConfidence::Exact:
        return "exact";
    case MatchConfidence::High:
        return "high";
    case MatchConfidence::Medium:
        return "medium";
    case MatchConfidence::Low:
        return "low";
    case MatchConfidence::None:
        return "none";
    }
    return "unknown";
}

}  // namespace matching
}  // namespace retro_metadata
