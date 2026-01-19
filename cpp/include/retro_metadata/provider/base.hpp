#pragma once

/// @file base.hpp
/// @brief Base provider implementation with common functionality

#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/internal/matching.hpp>
#include <retro_metadata/internal/normalization.hpp>
#include <retro_metadata/provider/provider.hpp>

#include <memory>
#include <regex>
#include <string>
#include <vector>

namespace retro_metadata {

/// @brief Base class providing common functionality for providers
///
/// Provides utilities for normalization, caching, and matching that
/// are commonly needed by provider implementations.
class BaseProvider {
public:
    BaseProvider(
        std::string name, ProviderConfig config, std::shared_ptr<Cache> cache = nullptr);
    virtual ~BaseProvider() = default;

    /// @brief Returns the provider name
    [[nodiscard]] const std::string& provider_name() const { return name_; }

    /// @brief Returns the provider configuration
    [[nodiscard]] const ProviderConfig& config() const { return config_; }

    /// @brief Returns the cache backend
    [[nodiscard]] std::shared_ptr<Cache> cache() const { return cache_; }

    /// @brief Returns true if the provider is enabled and configured
    [[nodiscard]] bool is_enabled() const;

    /// @brief Returns a credential value by key
    [[nodiscard]] std::string get_credential(const std::string& key) const;

    /// @brief Normalizes a search term for comparison
    [[nodiscard]] std::string normalize_search_term(const std::string& name) const;

    /// @brief Normalizes a cover image URL
    [[nodiscard]] std::string normalize_cover_url(const std::string& url) const;

    /// @brief Finds the best matching name from candidates
    [[nodiscard]] matching::BestMatchResult find_best_match(
        const std::string& search_term, const std::vector<std::string>& candidates) const;

    /// @brief Finds the best match with custom options
    [[nodiscard]] matching::BestMatchResult find_best_match_with_options(
        const std::string& search_term,
        const std::vector<std::string>& candidates,
        const matching::FindBestMatchOptions& opts) const;

    /// @brief Sets the minimum similarity score for matching
    void set_min_similarity_score(double score);

    /// @brief Extracts a provider ID from a filename using a regex pattern
    [[nodiscard]] std::optional<int> extract_id_from_filename(
        const std::string& filename, const std::regex& pattern) const;

    /// @brief Splits a search term by common delimiters
    [[nodiscard]] std::vector<std::string> split_search_term(const std::string& name) const;

    /// @brief Retrieves a value from cache if available
    [[nodiscard]] std::optional<std::any> get_cached(const std::string& key) const;

    /// @brief Stores a value in cache if available
    void set_cached(const std::string& key, std::any value) const;

protected:
    std::string name_;
    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
    double min_similarity_score_ = matching::kDefaultMinSimilarity;
};

}  // namespace retro_metadata
