/// @file playmatch.cpp
/// @brief Playmatch hash-matching provider implementation
///
/// Playmatch is a hash-matching service that returns external provider IDs (like IGDB).
/// It is primarily a hash-lookup utility, not a full metadata provider.

#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/errors.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>

#include <cpr/cpr.h>
#include <nlohmann/json.hpp>

#include <optional>
#include <string>
#include <vector>

namespace retro_metadata {

namespace {

/// @brief Helper to extract a string from JSON
std::string get_string(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key) && j[key].is_string()) {
        return j[key].get<std::string>();
    }
    return "";
}

}  // namespace

/// @brief Represents the type of match returned by Playmatch
enum class GameMatchType {
    SHA256,
    SHA1,
    MD5,
    FileNameAndSize,
    NoMatch
};

/// @brief Convert string to GameMatchType
GameMatchType parse_match_type(const std::string& str) {
    if (str == "SHA256") return GameMatchType::SHA256;
    if (str == "SHA1") return GameMatchType::SHA1;
    if (str == "MD5") return GameMatchType::MD5;
    if (str == "FileNameAndSize") return GameMatchType::FileNameAndSize;
    return GameMatchType::NoMatch;
}

/// @brief Convert GameMatchType to string
std::string match_type_to_string(GameMatchType type) {
    switch (type) {
        case GameMatchType::SHA256: return "SHA256";
        case GameMatchType::SHA1: return "SHA1";
        case GameMatchType::MD5: return "MD5";
        case GameMatchType::FileNameAndSize: return "FileNameAndSize";
        case GameMatchType::NoMatch: return "NoMatch";
    }
    return "NoMatch";
}

/// @brief External metadata entry from Playmatch
struct ExternalMetadata {
    std::string provider_name;
    std::string provider_id;
    nlohmann::json raw_data;
};

/// @brief Result of a hash lookup operation
struct LookupResult {
    /// IGDB ID if available
    std::optional<int> igdb_id;
    /// Type of match that was found
    GameMatchType match_type = GameMatchType::NoMatch;
    /// List of external metadata entries
    std::vector<ExternalMetadata> external_metadata;
};

/// @brief Playmatch hash-matching provider
///
/// This provider looks up ROMs by hash to get external provider IDs (like IGDB).
/// It does not provide full game metadata - use the returned IDs to query
/// other providers for complete information.
class PlaymatchProvider : public Provider {
public:
    PlaymatchProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache)
        : config_(config), cache_(std::move(cache)), base_url_("https://playmatch.retrorealm.dev/api") {}

    std::string name() const override { return "playmatch"; }

    /// @brief Search is not supported by Playmatch (hash-based only)
    /// @return Empty vector
    std::vector<SearchResult> search(const std::string& /*query*/,
                                      const SearchOptions& /*opts*/) override {
        return {};
    }

    /// @brief GetByID is not supported by Playmatch
    /// @return nullptr
    std::unique_ptr<GameResult> get_by_id(int /*game_id*/) override {
        return nullptr;
    }

    /// @brief Identify is not the primary method for Playmatch
    ///
    /// Use lookup_by_hash() instead for hash-based identification.
    /// @return nullptr
    std::unique_ptr<GameResult> identify(const std::string& /*filename*/,
                                          const IdentifyOptions& /*opts*/) override {
        return nullptr;
    }

    /// @brief Looks up a ROM by hash to get external provider IDs
    ///
    /// @param filename The ROM filename
    /// @param file_size File size in bytes
    /// @param md5 MD5 hash (optional but recommended)
    /// @param sha1 SHA1 hash (optional but recommended)
    /// @return LookupResult or nullptr if not found
    [[nodiscard]] std::unique_ptr<LookupResult> lookup_by_hash(
        const std::string& filename,
        int64_t file_size,
        const std::string& md5 = "",
        const std::string& sha1 = "") {

        if (!config_.enabled) {
            return nullptr;
        }

        // Build query parameters
        cpr::Parameters params;
        params.Add({"fileName", filename});
        params.Add({"fileSize", std::to_string(file_size)});

        if (!md5.empty()) {
            params.Add({"md5", md5});
        }
        if (!sha1.empty()) {
            params.Add({"sha1", sha1});
        }

        // Make request
        auto response = request("/identify/ids", params);
        if (!response) {
            return nullptr;
        }

        // Parse match type
        std::string match_type_str = get_string(*response, "gameMatchType");
        GameMatchType match_type = parse_match_type(match_type_str);

        if (match_type == GameMatchType::NoMatch || match_type_str.empty()) {
            return nullptr;
        }

        // Check for external metadata
        if (!response->contains("externalMetadata") ||
            !(*response)["externalMetadata"].is_array() ||
            (*response)["externalMetadata"].empty()) {
            return nullptr;
        }

        auto result = std::make_unique<LookupResult>();
        result->match_type = match_type;

        // Extract external metadata
        for (const auto& meta : (*response)["externalMetadata"]) {
            if (!meta.is_object()) continue;

            ExternalMetadata em;
            em.provider_name = get_string(meta, "providerName");
            em.provider_id = get_string(meta, "providerId");
            em.raw_data = meta;

            // Extract IGDB ID if this is an IGDB entry
            if (em.provider_name == "IGDB" && !em.provider_id.empty()) {
                try {
                    result->igdb_id = std::stoi(em.provider_id);
                } catch (...) {
                    // Invalid ID format, ignore
                }
            }

            result->external_metadata.push_back(std::move(em));
        }

        return result;
    }

    /// @brief Convenience method to get just the IGDB ID for a ROM
    ///
    /// @param filename The ROM filename
    /// @param file_size File size in bytes
    /// @param md5 MD5 hash (optional)
    /// @param sha1 SHA1 hash (optional)
    /// @return IGDB ID or nullopt if not found
    [[nodiscard]] std::optional<int> get_igdb_id(
        const std::string& filename,
        int64_t file_size,
        const std::string& md5 = "",
        const std::string& sha1 = "") {

        auto result = lookup_by_hash(filename, file_size, md5, sha1);
        if (!result) {
            return std::nullopt;
        }
        return result->igdb_id;
    }

    /// @brief Checks if the Playmatch API is available
    void heartbeat() override {
        if (!config_.enabled) {
            throw ConnectionError(name(), "provider is disabled");
        }

        cpr::Response r = cpr::Get(
            cpr::Url{base_url_ + "/health"},
            cpr::Header{{"User-Agent", "retro-metadata/1.0"}},
            cpr::Timeout{config_.timeout * 1000}
        );

        if (r.status_code != 200) {
            throw ConnectionError(name(), "health check failed: HTTP " + std::to_string(r.status_code));
        }
    }

    void close() override {}

private:
    /// @brief Make a GET request to the Playmatch API
    ///
    /// @param endpoint API endpoint (e.g., "/identify/ids")
    /// @param params Query parameters
    /// @return JSON response or nullptr on error
    [[nodiscard]] std::optional<nlohmann::json> request(
        const std::string& endpoint,
        const cpr::Parameters& params) {

        cpr::Response r = cpr::Get(
            cpr::Url{base_url_ + endpoint},
            params,
            cpr::Header{{"User-Agent", "retro-metadata/1.0"}},
            cpr::Timeout{config_.timeout * 1000}
        );

        if (r.status_code != 200) {
            return std::nullopt;
        }

        try {
            return nlohmann::json::parse(r.text);
        } catch (...) {
            return std::nullopt;
        }
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
    std::string base_url_;
};

namespace {
[[maybe_unused]] ProviderRegistrar playmatch_registrar(
    "playmatch",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<PlaymatchProvider>(config, std::move(cache));
    });
}

}  // namespace retro_metadata
