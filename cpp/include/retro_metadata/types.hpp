#pragma once

/// @file types.hpp
/// @brief Core data types for the retro-metadata library

#include <chrono>
#include <map>
#include <optional>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

namespace retro_metadata {

/// @brief Represents a gaming platform
struct Platform {
    /// Universal platform identifier (e.g., "snes", "ps2")
    std::string slug;
    /// Human-readable platform name
    std::string name;
    /// Maps provider names to their platform IDs
    std::map<std::string, int> provider_ids;
};

/// @brief Serialization for Platform
void to_json(nlohmann::json& j, const Platform& p);
void from_json(const nlohmann::json& j, Platform& p);

/// @brief Represents an age rating for a game
struct AgeRating {
    /// Rating value (e.g., "E", "T", "M", "PEGI 12")
    std::string rating;
    /// Rating system (e.g., "ESRB", "PEGI", "CERO")
    std::string category;
    /// URL to the rating icon/image
    std::string cover_url;
};

/// @brief Serialization for AgeRating
void to_json(nlohmann::json& j, const AgeRating& a);
void from_json(const nlohmann::json& j, AgeRating& a);

/// @brief Represents multiplayer capabilities for a game on a specific platform
struct MultiplayerMode {
    std::optional<Platform> platform;
    bool campaign_coop = false;
    bool drop_in = false;
    bool lan_coop = false;
    bool offline_coop = false;
    int offline_coop_max = 0;
    int offline_max = 0;
    bool online_coop = false;
    int online_coop_max = 0;
    int online_max = 0;
    bool split_screen = false;
    bool split_screen_online = false;
};

/// @brief Serialization for MultiplayerMode
void to_json(nlohmann::json& j, const MultiplayerMode& m);
void from_json(const nlohmann::json& j, MultiplayerMode& m);

/// @brief Represents a related game (DLC, expansion, remake, etc.)
struct RelatedGame {
    /// Provider-specific ID
    int id = 0;
    /// Game name
    std::string name;
    /// URL-friendly slug
    std::string slug;
    /// Type of relation (expansion, dlc, remaster, remake, port, similar)
    std::string relation_type;
    /// URL to cover art
    std::string cover_url;
    /// Provider name this came from
    std::string provider;
};

/// @brief Serialization for RelatedGame
void to_json(nlohmann::json& j, const RelatedGame& r);
void from_json(const nlohmann::json& j, RelatedGame& r);

/// @brief Contains game artwork URLs
struct Artwork {
    /// URL to the main cover art
    std::string cover_url;
    /// List of screenshot URLs
    std::vector<std::string> screenshot_urls;
    /// URL to a banner image
    std::string banner_url;
    /// URL to an icon image
    std::string icon_url;
    /// URL to the game logo
    std::string logo_url;
    /// URL to a background image
    std::string background_url;
};

/// @brief Serialization for Artwork
void to_json(nlohmann::json& j, const Artwork& a);
void from_json(const nlohmann::json& j, Artwork& a);

/// @brief Contains extended metadata for a game
struct GameMetadata {
    /// Aggregated user rating (0-100)
    std::optional<double> total_rating;
    /// Critic aggregated rating (0-100)
    std::optional<double> aggregated_rating;
    /// Unix timestamp of first release
    std::optional<int64_t> first_release_date;
    /// YouTube video ID for trailer
    std::string youtube_video_id;
    /// List of genre names
    std::vector<std::string> genres;
    /// List of franchise names
    std::vector<std::string> franchises;
    /// List of alternative titles
    std::vector<std::string> alternative_names;
    /// List of game collections/series
    std::vector<std::string> collections;
    /// List of companies involved
    std::vector<std::string> companies;
    /// List of game modes
    std::vector<std::string> game_modes;
    /// List of age ratings
    std::vector<AgeRating> age_ratings;
    /// List of platforms
    std::vector<Platform> platforms;
    /// Multiplayer capabilities per platform
    std::vector<MultiplayerMode> multiplayer_modes;
    /// Human-readable player count string
    std::string player_count;
    /// Related expansion games
    std::vector<RelatedGame> expansions;
    /// Related DLC content
    std::vector<RelatedGame> dlcs;
    /// Related remastered versions
    std::vector<RelatedGame> remasters;
    /// Related remakes
    std::vector<RelatedGame> remakes;
    /// Related expanded editions
    std::vector<RelatedGame> expanded_games;
    /// Related ports to other platforms
    std::vector<RelatedGame> ports;
    /// Similar games
    std::vector<RelatedGame> similar_games;
    /// Primary developer name
    std::string developer;
    /// Primary publisher name
    std::string publisher;
    /// Release year
    std::optional<int> release_year;
    /// Original provider-specific data
    nlohmann::json raw_data;
};

/// @brief Serialization for GameMetadata
void to_json(nlohmann::json& j, const GameMetadata& m);
void from_json(const nlohmann::json& j, GameMetadata& m);

/// @brief Represents a game result from metadata lookup
///
/// This is the main type returned by providers for game lookups.
struct GameResult {
    /// Game name
    std::string name;
    /// Game description/summary
    std::string summary;
    /// Provider name this result came from
    std::string provider;
    /// Provider-specific game ID
    std::optional<int> provider_id;
    /// Maps provider names to IDs
    std::map<std::string, int> provider_ids;
    /// URL-friendly slug
    std::string slug;
    /// Game artwork URLs
    Artwork artwork;
    /// Extended metadata
    GameMetadata metadata;
    /// Similarity score if result was from a search (0-1)
    double match_score = 0.0;
    /// Type of match (hash+filename, hash, filename, etc.)
    std::string match_type;
    /// Raw provider response for debugging
    nlohmann::json raw_response;

    /// Convenience method to get cover URL
    [[nodiscard]] const std::string& cover_url() const { return artwork.cover_url; }

    /// Convenience method to get screenshot URLs
    [[nodiscard]] const std::vector<std::string>& screenshot_urls() const {
        return artwork.screenshot_urls;
    }
};

/// @brief Serialization for GameResult
void to_json(nlohmann::json& j, const GameResult& g);
void from_json(const nlohmann::json& j, GameResult& g);

/// @brief Represents a search result with minimal information
///
/// Used for displaying search results before fetching full details.
struct SearchResult {
    /// Game name
    std::string name;
    /// Provider name
    std::string provider;
    /// Provider-specific ID
    int provider_id = 0;
    /// URL-friendly slug
    std::string slug;
    /// URL to cover art thumbnail
    std::string cover_url;
    /// Platforms the game is available on
    std::vector<std::string> platforms;
    /// Release year if known
    std::optional<int> release_year;
    /// Similarity score (0-1)
    double match_score = 0.0;
};

/// @brief Serialization for SearchResult
void to_json(nlohmann::json& j, const SearchResult& s);
void from_json(const nlohmann::json& j, SearchResult& s);

/// @brief Contains options for search operations
struct SearchOptions {
    /// Provider-specific platform ID to filter by
    std::optional<int> platform_id;
    /// Maximum number of results to return
    int limit = 10;
    /// Minimum similarity score for fuzzy matching
    double min_score = 0.75;
};

/// @brief Returns sensible default search options
[[nodiscard]] SearchOptions default_search_options();

/// @brief Contains various hash values for a ROM file
struct FileHashes {
    std::string md5;
    std::string sha1;
    std::string crc32;
    std::string sha256;

    /// Check if any hash is set
    [[nodiscard]] bool has_any() const {
        return !md5.empty() || !sha1.empty() || !crc32.empty() || !sha256.empty();
    }
};

/// @brief Serialization for FileHashes
void to_json(nlohmann::json& j, const FileHashes& h);
void from_json(const nlohmann::json& j, FileHashes& h);

/// @brief Contains options for identify operations
struct IdentifyOptions {
    /// Provider-specific platform ID
    std::optional<int> platform_id;
    /// File hashes for hash-based identification
    std::optional<FileHashes> hashes;
};

/// @brief Represents the health status of a provider
struct ProviderStatus {
    /// Provider name
    std::string name;
    /// Whether the provider API is accessible
    bool available = false;
    /// Time of the last health check
    std::chrono::system_clock::time_point last_check;
    /// Error message if unavailable
    std::string error;
};

/// @brief Serialization for ProviderStatus
void to_json(nlohmann::json& j, const ProviderStatus& s);
void from_json(const nlohmann::json& j, ProviderStatus& s);

}  // namespace retro_metadata
