#pragma once

/// @file provider.hpp
/// @brief Provider interface for metadata providers

#include <retro_metadata/types.hpp>

#include <memory>
#include <string>
#include <vector>

namespace retro_metadata {

/// @brief Abstract interface that all metadata providers must implement
class Provider {
public:
    virtual ~Provider() = default;

    /// @brief Returns the provider name (e.g., "igdb", "mobygames")
    [[nodiscard]] virtual std::string name() const = 0;

    /// @brief Searches for games by name
    ///
    /// @param query The search query
    /// @param opts Search options
    /// @return List of search results
    [[nodiscard]] virtual std::vector<SearchResult> search(
        const std::string& query, const SearchOptions& opts = {}) = 0;

    /// @brief Gets game details by provider-specific ID
    ///
    /// @param game_id Provider-specific game ID
    /// @return Game result or nullptr if not found
    [[nodiscard]] virtual std::unique_ptr<GameResult> get_by_id(int game_id) = 0;

    /// @brief Identifies a game from a ROM filename
    ///
    /// @param filename The ROM filename
    /// @param opts Identify options
    /// @return Game result or nullptr if not found
    [[nodiscard]] virtual std::unique_ptr<GameResult> identify(
        const std::string& filename, const IdentifyOptions& opts = {}) = 0;

    /// @brief Checks if the provider API is accessible
    ///
    /// @throws ConnectionError, AuthError if the provider is not accessible
    virtual void heartbeat() = 0;

    /// @brief Cleans up provider resources
    virtual void close() = 0;
};

/// @brief Optional interface for providers that support hash-based identification
class HashProvider : public Provider {
public:
    /// @brief Identifies a game using file hashes
    ///
    /// @param hashes File hashes (MD5, SHA1, CRC32, etc.)
    /// @param opts Identify options
    /// @return Game result or nullptr if not found
    [[nodiscard]] virtual std::unique_ptr<GameResult> identify_by_hash(
        const FileHashes& hashes, const IdentifyOptions& opts = {}) = 0;
};

/// @brief Factory function type for creating providers
using ProviderFactory = std::function<std::unique_ptr<Provider>(
    const ProviderConfig& config, std::shared_ptr<class Cache> cache)>;

}  // namespace retro_metadata
