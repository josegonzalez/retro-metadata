/// @file flashpoint.cpp
/// @brief Flashpoint Archive metadata provider implementation

#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/errors.hpp>
#include <retro_metadata/internal/matching.hpp>
#include <retro_metadata/internal/normalization.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>

#include <cpr/cpr.h>
#include <nlohmann/json.hpp>

#include <regex>
#include <sstream>

namespace retro_metadata {

namespace {

/// Base URL for the Flashpoint database API
const std::string kBaseURL = "https://db-api.unstable.life";

/// Base URL for Flashpoint images
const std::string kImageBaseURL = "https://infinity.unstable.life/images";

/// Regex to detect Flashpoint ID tags in filenames (UUID format)
const std::regex kFlashpointTagRegex(
    R"(\(fp-([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\))",
    std::regex::icase);

/// UUID regex for filename extraction
const std::regex kUuidRegex(
    R"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",
    std::regex::icase);

/// Get a string value from a JSON object, returning empty string if not found
std::string get_string(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key) && j[key].is_string()) {
        return j[key].get<std::string>();
    }
    return "";
}

/// Build image URL for Flashpoint
/// @param game_id The UUID of the game
/// @param image_type The type of image ("Logos" for cover, "Screenshots" for screenshots)
std::string build_image_url(const std::string& game_id, const std::string& image_type) {
    if (game_id.length() < 4) {
        return "";
    }
    // Format: https://infinity.unstable.life/images/{type}/{id[0:2]}/{id[2:4]}/{id}?type=jpg
    return kImageBaseURL + "/" + image_type + "/" + game_id.substr(0, 2) + "/" +
           game_id.substr(2, 2) + "/" + game_id + "?type=jpg";
}

/// Clean a filename for searching
std::string clean_filename(const std::string& filename) {
    static const std::regex ext_pattern(R"(\.[^.]+$)");
    static const std::regex tag_pattern(R"(\s*[\(\[][^\)\]]*[\)\]])");

    std::string name = std::regex_replace(filename, ext_pattern, "");
    name = std::regex_replace(name, tag_pattern, "");
    // Remove UUID patterns
    name = std::regex_replace(name, kUuidRegex, "");

    auto start = name.find_first_not_of(" \t\n\r");
    if (start == std::string::npos) return "";
    auto end = name.find_last_not_of(" \t\n\r");
    return name.substr(start, end - start + 1);
}

/// Parse year from a date string (expects format starting with YYYY)
int parse_year(const std::string& date_str) {
    if (date_str.length() < 4) {
        return 0;
    }
    try {
        return std::stoi(date_str.substr(0, 4));
    } catch (...) {
        return 0;
    }
}

/// Parse date string to Unix timestamp
int64_t parse_date_to_timestamp(const std::string& date_str) {
    if (date_str.empty()) {
        return 0;
    }
    // Parse YYYY-MM-DD format
    std::tm tm = {};
    std::istringstream ss(date_str);
    ss >> std::get_time(&tm, "%Y-%m-%d");
    if (ss.fail()) {
        return 0;
    }
    return std::mktime(&tm);
}

}  // namespace

/// @brief Flashpoint Archive metadata provider
///
/// Flashpoint is a preservation project for Flash games and other web-based games.
/// It provides metadata for thousands of web games that are no longer available.
/// Note: Flashpoint uses UUID strings for game IDs, not integers.
class FlashpointProvider : public Provider {
public:
    FlashpointProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache)
        : config_(config), cache_(std::move(cache)) {}

    std::string name() const override { return "flashpoint"; }

    std::vector<SearchResult> search(const std::string& query, const SearchOptions& opts) override {
        if (!config_.enabled) {
            return {};
        }

        auto response = request("/search", {{"smartSearch", query}, {"filter", "false"}});
        if (!response.is_array()) {
            return {};
        }

        int limit = opts.limit > 0 ? opts.limit : 30;
        std::vector<SearchResult> results;

        for (const auto& game : response) {
            if (static_cast<int>(results.size()) >= limit) {
                break;
            }

            std::string game_id = get_string(game, "id");
            if (game_id.empty()) {
                continue;
            }

            SearchResult sr;
            sr.provider = name();
            sr.provider_id = 0;  // Flashpoint uses UUID strings, not integers
            sr.name = get_string(game, "title");
            sr.slug = game_id;
            sr.cover_url = build_image_url(game_id, "Logos");

            std::string platform = get_string(game, "platform");
            if (!platform.empty()) {
                sr.platforms.push_back(platform);
            }

            std::string date_str = get_string(game, "releaseDate");
            if (!date_str.empty()) {
                int year = parse_year(date_str);
                if (year > 0) {
                    sr.release_year = year;
                }
            }

            results.push_back(std::move(sr));
        }

        return results;
    }

    std::unique_ptr<GameResult> get_by_id(int /*game_id*/) override {
        // Flashpoint uses UUID strings, not integer IDs
        // This method is not supported
        return nullptr;
    }

    /// @brief Gets game details by Flashpoint UUID
    ///
    /// @param game_uuid The UUID of the game
    /// @return Game result or nullptr if not found
    std::unique_ptr<GameResult> get_by_uuid(const std::string& game_uuid) {
        if (!config_.enabled) {
            return nullptr;
        }

        auto response = request("/search", {{"id", game_uuid}, {"filter", "false"}});
        if (!response.is_array() || response.empty()) {
            return nullptr;
        }

        const auto& game = response[0];
        if (get_string(game, "id").empty()) {
            return nullptr;
        }

        return build_game_result(game);
    }

    std::unique_ptr<GameResult> identify(
        const std::string& filename, const IdentifyOptions& /*opts*/) override {
        if (!config_.enabled) {
            return nullptr;
        }

        // Check for Flashpoint ID tag in filename (fp-UUID)
        std::smatch tag_match;
        if (std::regex_search(filename, tag_match, kFlashpointTagRegex) && tag_match.size() > 1) {
            auto result = get_by_uuid(tag_match[1].str());
            if (result) {
                result->match_type = "tag";
                return result;
            }
        }

        // Check for UUID in filename
        std::smatch uuid_match;
        if (std::regex_search(filename, uuid_match, kUuidRegex)) {
            auto result = get_by_uuid(uuid_match[0].str());
            if (result) {
                result->match_type = "uuid";
                return result;
            }
        }

        // Clean the filename and search
        std::string search_term = clean_filename(filename);
        if (search_term.empty()) {
            return nullptr;
        }

        auto response = request("/search", {{"smartSearch", search_term}, {"filter", "false"}});
        if (!response.is_array() || response.empty()) {
            return nullptr;
        }

        // Build name to game map
        std::map<std::string, nlohmann::json> games_by_name;
        std::vector<std::string> names;
        for (const auto& game : response) {
            std::string game_name = get_string(game, "title");
            if (!game_name.empty()) {
                games_by_name[game_name] = game;
                names.push_back(game_name);
            }
        }

        if (names.empty()) {
            return nullptr;
        }

        // Find best match using Jaro-Winkler similarity
        auto best = matching::find_best_match_simple(search_term, names);
        if (!best.found()) {
            return nullptr;
        }

        auto result = build_game_result(games_by_name[best.match]);
        result->match_score = best.score;
        result->match_type = "filename";
        return result;
    }

    void heartbeat() override {
        if (!config_.enabled) {
            throw ConnectionError(name(), "provider is disabled");
        }

        // Make a simple search request to check connectivity
        auto response = request("/search", {{"smartSearch", "test"}, {"filter", "false"}});
        if (!response.is_array()) {
            throw ConnectionError(name(), "unexpected response format");
        }
    }

    void close() override {}

private:
    /// Make an HTTP request to the Flashpoint API
    nlohmann::json request(
        const std::string& endpoint,
        const std::vector<std::pair<std::string, std::string>>& params) {
        cpr::Parameters cpr_params;
        for (const auto& [key, value] : params) {
            cpr_params.Add({key, value});
        }

        cpr::Response r = cpr::Get(
            cpr::Url{kBaseURL + endpoint},
            cpr_params,
            cpr::Header{{"User-Agent", "retro-metadata/1.0"}},
            cpr::Timeout{config_.timeout * 1000});

        if (r.status_code == 429) {
            throw RateLimitError(name());
        }

        if (r.status_code != 200) {
            throw ConnectionError(name(), "HTTP " + std::to_string(r.status_code));
        }

        try {
            return nlohmann::json::parse(r.text);
        } catch (const nlohmann::json::parse_error& e) {
            throw ConnectionError(name(), "JSON parse error: " + std::string(e.what()));
        }
    }

    /// Build a GameResult from a JSON game object
    std::unique_ptr<GameResult> build_game_result(const nlohmann::json& game) {
        auto result = std::make_unique<GameResult>();
        std::string game_id = get_string(game, "id");

        result->provider = name();
        result->provider_id = std::nullopt;  // Flashpoint uses UUIDs
        result->slug = game_id;
        result->name = get_string(game, "title");
        result->summary = get_string(game, "originalDescription");

        // Artwork
        result->artwork.cover_url = build_image_url(game_id, "Logos");
        std::string screenshot_url = build_image_url(game_id, "Screenshots");
        if (!screenshot_url.empty()) {
            result->artwork.screenshot_urls.push_back(screenshot_url);
        }

        // Extract metadata
        extract_metadata(game, result->metadata);

        result->raw_response = game;
        return result;
    }

    /// Extract metadata from a JSON game object
    void extract_metadata(const nlohmann::json& game, GameMetadata& metadata) {
        // Release date
        std::string date_str = get_string(game, "releaseDate");
        if (!date_str.empty()) {
            int64_t timestamp = parse_date_to_timestamp(date_str);
            if (timestamp > 0) {
                metadata.first_release_date = timestamp;
            }
            int year = parse_year(date_str);
            if (year > 0) {
                metadata.release_year = year;
            }
        }

        // Developer and publisher
        metadata.developer = get_string(game, "developer");
        metadata.publisher = get_string(game, "publisher");

        // Companies (combine developer and publisher)
        if (!metadata.developer.empty()) {
            metadata.companies.push_back(metadata.developer);
        }
        if (!metadata.publisher.empty() && metadata.publisher != metadata.developer) {
            metadata.companies.push_back(metadata.publisher);
        }

        // Genres from tags
        if (game.contains("tags")) {
            if (game["tags"].is_array()) {
                for (const auto& tag : game["tags"]) {
                    if (tag.is_string()) {
                        metadata.genres.push_back(tag.get<std::string>());
                    }
                }
            } else if (game["tags"].is_string()) {
                // Tags might be a comma-separated string
                std::string tags_str = game["tags"].get<std::string>();
                std::istringstream iss(tags_str);
                std::string tag;
                while (std::getline(iss, tag, ',')) {
                    // Trim whitespace
                    auto start = tag.find_first_not_of(" \t");
                    if (start != std::string::npos) {
                        auto end = tag.find_last_not_of(" \t");
                        metadata.genres.push_back(tag.substr(start, end - start + 1));
                    }
                }
            }
        }

        // Franchises from series
        if (game.contains("series")) {
            if (game["series"].is_string()) {
                std::string series = game["series"].get<std::string>();
                if (!series.empty()) {
                    metadata.franchises.push_back(series);
                }
            } else if (game["series"].is_array()) {
                for (const auto& s : game["series"]) {
                    if (s.is_string()) {
                        metadata.franchises.push_back(s.get<std::string>());
                    }
                }
            }
        }

        // Game modes from playMode
        std::string play_mode = get_string(game, "playMode");
        if (!play_mode.empty()) {
            metadata.game_modes.push_back(play_mode);
        }

        // Platform
        std::string platform = get_string(game, "platform");
        if (!platform.empty()) {
            Platform plat;
            plat.name = platform;
            plat.slug = platform;
            metadata.platforms.push_back(plat);
        }

        // Store additional raw data
        metadata.raw_data = nlohmann::json{
            {"source", get_string(game, "source")},
            {"status", get_string(game, "status")},
            {"version", get_string(game, "version")},
            {"language", get_string(game, "language")},
            {"library", get_string(game, "library")},
            {"platform", platform},
            {"notes", get_string(game, "notes")}};
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
};

namespace {
[[maybe_unused]] ProviderRegistrar flashpoint_registrar(
    "flashpoint",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<FlashpointProvider>(config, std::move(cache));
    });
}

}  // namespace retro_metadata
