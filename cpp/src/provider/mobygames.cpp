/// @file mobygames.cpp
/// @brief MobyGames metadata provider implementation

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

namespace retro_metadata {

namespace {

/// @brief Regex to match MobyGames ID tags in filenames like (moby-12345)
const std::regex kMobyGamesTagRegex(R"(\(moby-(\d+)\))", std::regex::icase);

/// @brief Regex to match Sony serial codes like SLUS-12345, SCUS-97328
const std::regex kSonySerialRegex(R"(([A-Z]{4})[_-](\d{5}))", std::regex::icase);

/// @brief Regex to match PS2 OPL format like SLUS_123.45
const std::regex kPS2OPLRegex(R"(([A-Z]{4})_(\d{3})\.(\d{2}))", std::regex::icase);

/// @brief Regex to match Nintendo Switch 16-character hex IDs
const std::regex kSwitchTitleDBRegex(R"(([0-9A-Fa-f]{16}))");

/// @brief Regex to match Switch product IDs like LA-H-AAAAA
const std::regex kSwitchProductIDRegex(R"([A-Z]{2}-[A-Z]-([A-Z0-9]{5}))", std::regex::icase);

/// @brief Regex to match MAME ROM names
const std::regex kMAMEArcadeRegex(R"(^[a-z0-9_]+$)", std::regex::icase);

/// @brief Base URL for the MobyGames API
constexpr const char* kBaseURL = "https://api.mobygames.com/v1";

/// @brief Safely gets a string from a JSON object
std::string get_string(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key) && j[key].is_string()) {
        return j[key].get<std::string>();
    }
    return "";
}

/// @brief Safely gets a number from a JSON object
double get_number(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key) && j[key].is_number()) {
        return j[key].get<double>();
    }
    return 0.0;
}

/// @brief Cleans a filename by removing extension and tags
std::string clean_filename(const std::string& filename) {
    static const std::regex ext_pattern(R"(\.[^.]+$)");
    static const std::regex tag_pattern(R"(\s*[\(\[][^\)\]]*[\)\]])");
    std::string name = std::regex_replace(filename, ext_pattern, "");
    name = std::regex_replace(name, tag_pattern, "");
    auto start = name.find_first_not_of(" \t\n\r");
    if (start == std::string::npos) return "";
    auto end = name.find_last_not_of(" \t\n\r");
    return name.substr(start, end - start + 1);
}

/// @brief Extracts Sony serial code from filename (PS1/PS2/PSP)
std::string extract_serial_code(const std::string& filename) {
    std::smatch match;

    // Try PS2 OPL format first (SLUS_123.45)
    if (std::regex_search(filename, match, kPS2OPLRegex) && match.size() > 3) {
        std::string prefix = match[1].str();
        std::transform(prefix.begin(), prefix.end(), prefix.begin(), ::toupper);
        return prefix + "-" + match[2].str() + match[3].str();
    }

    // Try standard Sony serial format (SLUS-12345 or SLUS_12345)
    if (std::regex_search(filename, match, kSonySerialRegex) && match.size() > 2) {
        std::string prefix = match[1].str();
        std::transform(prefix.begin(), prefix.end(), prefix.begin(), ::toupper);
        return prefix + "-" + match[2].str();
    }

    return "";
}

/// @brief Extracts Nintendo Switch product ID from filename
std::string extract_switch_product_id(const std::string& filename) {
    std::smatch match;
    if (std::regex_search(filename, match, kSwitchProductIDRegex) && match.size() > 1) {
        std::string product_id = match[1].str();
        std::transform(product_id.begin(), product_id.end(), product_id.begin(), ::toupper);
        return product_id;
    }
    return "";
}

/// @brief Checks if filename is in MAME format
bool is_mame_format(const std::string& filename) {
    static const std::regex ext_pattern(R"(\.[^.]+$)");
    std::string name = std::regex_replace(filename, ext_pattern, "");
    // MAME names are typically short (under 20 chars) and alphanumeric
    if (name.length() > 20) {
        return false;
    }
    return std::regex_match(name, kMAMEArcadeRegex);
}

/// @brief MobyGames platform IDs for special handling
constexpr int kPlatformPS1 = 6;
constexpr int kPlatformPS2 = 7;
constexpr int kPlatformPSP = 46;
constexpr int kPlatformArcade = 143;
constexpr int kPlatformSwitch = 203;

}  // namespace

/// @brief MobyGames metadata provider
class MobyGamesProvider : public Provider {
public:
    MobyGamesProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache)
        : config_(config), cache_(std::move(cache)) {}

    std::string name() const override { return "mobygames"; }

    std::vector<SearchResult> search(const std::string& query, const SearchOptions& opts) override {
        if (!config_.is_configured()) return {};

        cpr::Parameters params{
            {"title", query},
            {"api_key", config_.get_credential("api_key")}
        };

        int limit = opts.limit > 0 ? opts.limit : 10;
        params.Add({"limit", std::to_string(limit)});

        if (opts.platform_id) {
            params.Add({"platform", std::to_string(*opts.platform_id)});
        }

        auto response = make_request("/games", params);
        if (!response.contains("games") || !response["games"].is_array()) {
            return {};
        }

        std::vector<SearchResult> results;
        for (const auto& game : response["games"]) {
            SearchResult sr;
            sr.provider = name();
            sr.provider_id = static_cast<int>(get_number(game, "game_id"));
            sr.name = get_string(game, "title");

            // Extract cover URL from sample_cover
            if (game.contains("sample_cover") && game["sample_cover"].is_object()) {
                sr.cover_url = get_string(game["sample_cover"], "image");
            }

            // Extract platforms
            if (game.contains("platforms") && game["platforms"].is_array()) {
                for (const auto& pl : game["platforms"]) {
                    sr.platforms.push_back(get_string(pl, "platform_name"));
                }
            }

            // Extract release year from first platform
            if (game.contains("platforms") && game["platforms"].is_array() &&
                !game["platforms"].empty()) {
                std::string date_str = get_string(game["platforms"][0], "first_release_date");
                if (date_str.length() >= 4) {
                    try {
                        sr.release_year = std::stoi(date_str.substr(0, 4));
                    } catch (...) {
                        // Ignore parse errors
                    }
                }
            }

            results.push_back(std::move(sr));
        }

        return results;
    }

    std::unique_ptr<GameResult> get_by_id(int game_id) override {
        if (!config_.is_configured()) return nullptr;

        cpr::Parameters params{
            {"api_key", config_.get_credential("api_key")}
        };

        auto response = make_request("/games/" + std::to_string(game_id), params);
        if (get_number(response, "game_id") == 0) {
            return nullptr;
        }

        return build_game_result(response);
    }

    std::unique_ptr<GameResult> identify(
        const std::string& filename, const IdentifyOptions& opts) override {
        if (!config_.is_configured()) return nullptr;

        // Check for MobyGames ID tag in filename
        std::smatch match;
        if (std::regex_search(filename, match, kMobyGamesTagRegex) && match.size() > 1) {
            try {
                int id = std::stoi(match[1].str());
                auto result = get_by_id(id);
                if (result) return result;
            } catch (...) {
                // Ignore parse errors, continue with filename matching
            }
        }

        if (!opts.platform_id) return nullptr;

        int platform_id = *opts.platform_id;
        std::string search_term;

        // Try Sony serial format for PS1/PS2/PSP platforms
        if (platform_id == kPlatformPS1 || platform_id == kPlatformPS2 ||
            platform_id == kPlatformPSP) {
            std::string serial = extract_serial_code(filename);
            if (!serial.empty()) {
                search_term = serial;
            }
        }

        // Try Nintendo Switch product ID format
        if (platform_id == kPlatformSwitch && search_term.empty()) {
            std::string product_id = extract_switch_product_id(filename);
            if (!product_id.empty()) {
                search_term = product_id;
            }
        }

        // Try MAME format for arcade platform
        if (platform_id == kPlatformArcade && search_term.empty()) {
            if (is_mame_format(filename)) {
                static const std::regex ext_pattern(R"(\.[^.]+$)");
                search_term = std::regex_replace(filename, ext_pattern, "");
            }
        }

        // Fall back to cleaned filename
        if (search_term.empty()) {
            search_term = clean_filename(filename);
        }

        // Search for the game
        cpr::Parameters params{
            {"title", search_term},
            {"platform", std::to_string(platform_id)},
            {"api_key", config_.get_credential("api_key")}
        };

        auto response = make_request("/games", params);

        nlohmann::json games;
        if (response.contains("games") && response["games"].is_array()) {
            games = response["games"];
        }

        // If no results, try splitting by special characters
        if (games.empty() || !games.is_array()) {
            auto terms = normalization::split_search_term(search_term);
            if (terms.size() > 1) {
                params = cpr::Parameters{
                    {"title", terms.back()},
                    {"platform", std::to_string(platform_id)},
                    {"api_key", config_.get_credential("api_key")}
                };
                response = make_request("/games", params);
                if (response.contains("games") && response["games"].is_array()) {
                    games = response["games"];
                }
            }
        }

        if (games.empty() || !games.is_array()) {
            return nullptr;
        }

        // Build map of games by name for matching
        std::map<std::string, nlohmann::json> games_by_name;
        std::vector<std::string> names;
        for (const auto& g : games) {
            std::string title = get_string(g, "title");
            if (!title.empty()) {
                games_by_name[title] = g;
                names.push_back(title);
            }
        }

        // Find best match using Jaro-Winkler similarity
        matching::FindBestMatchOptions match_opts;
        match_opts.min_similarity_score = 0.6;  // MobyGames uses lower threshold
        auto best = matching::find_best_match(search_term, names, match_opts);

        if (!best.found()) {
            return nullptr;
        }

        auto result = build_game_result(games_by_name[best.match]);
        result->match_score = best.score;
        return result;
    }

    void heartbeat() override {
        cpr::Parameters params{
            {"limit", "1"},
            {"api_key", config_.get_credential("api_key")}
        };

        // This will throw appropriate errors if the API is not accessible
        make_request("/games", params);
    }

    void close() override {
        // No resources to clean up
    }

private:
    /// @brief Makes an HTTP request to the MobyGames API
    nlohmann::json make_request(const std::string& endpoint, const cpr::Parameters& params) {
        std::string url = std::string(kBaseURL) + endpoint;

        cpr::Response r = cpr::Get(
            cpr::Url{url},
            params,
            cpr::Header{
                {"Accept", "application/json"},
                {"User-Agent", "retro-metadata/1.0"}
            },
            cpr::Timeout{config_.timeout * 1000}
        );

        if (r.status_code == 401) {
            throw AuthError(name());
        }

        if (r.status_code == 429) {
            throw RateLimitError(name());
        }

        if (r.status_code != 200) {
            throw ConnectionError(name(), "HTTP " + std::to_string(r.status_code));
        }

        try {
            return nlohmann::json::parse(r.text);
        } catch (const nlohmann::json::parse_error& e) {
            throw ConnectionError(name(), "Failed to parse JSON response");
        }
    }

    /// @brief Builds a GameResult from a MobyGames API response
    std::unique_ptr<GameResult> build_game_result(const nlohmann::json& game) {
        auto result = std::make_unique<GameResult>();
        int game_id = static_cast<int>(get_number(game, "game_id"));

        result->provider = name();
        result->provider_id = game_id;
        result->provider_ids = {{"mobygames", game_id}};
        result->name = get_string(game, "title");
        result->summary = get_string(game, "description");

        // Extract cover URL from sample_cover
        if (game.contains("sample_cover") && game["sample_cover"].is_object()) {
            result->artwork.cover_url = get_string(game["sample_cover"], "image");
        }

        // Extract screenshots from sample_screenshots
        if (game.contains("sample_screenshots") && game["sample_screenshots"].is_array()) {
            for (const auto& s : game["sample_screenshots"]) {
                std::string img_url = get_string(s, "image");
                if (!img_url.empty()) {
                    result->artwork.screenshot_urls.push_back(img_url);
                }
            }
        }

        // Extract metadata
        result->metadata = extract_metadata(game);
        result->raw_response = game;

        return result;
    }

    /// @brief Extracts metadata from a MobyGames game object
    GameMetadata extract_metadata(const nlohmann::json& game) {
        GameMetadata metadata;
        metadata.raw_data = game;

        // Genres
        if (game.contains("genres") && game["genres"].is_array()) {
            for (const auto& g : game["genres"]) {
                std::string genre_name = get_string(g, "genre_name");
                if (!genre_name.empty()) {
                    metadata.genres.push_back(genre_name);
                }
            }
        }

        // Alternative names
        if (game.contains("alternate_titles") && game["alternate_titles"].is_array()) {
            for (const auto& t : game["alternate_titles"]) {
                std::string title = get_string(t, "title");
                if (!title.empty()) {
                    metadata.alternative_names.push_back(title);
                }
            }
        }

        // Platforms
        if (game.contains("platforms") && game["platforms"].is_array()) {
            for (const auto& pl : game["platforms"]) {
                Platform platform;
                platform.name = get_string(pl, "platform_name");
                int platform_id = static_cast<int>(get_number(pl, "platform_id"));
                platform.provider_ids = {{"mobygames", platform_id}};
                metadata.platforms.push_back(platform);

                // Extract release year from first platform if not set
                if (!metadata.release_year) {
                    std::string date_str = get_string(pl, "first_release_date");
                    if (date_str.length() >= 4) {
                        try {
                            metadata.release_year = std::stoi(date_str.substr(0, 4));
                        } catch (...) {
                            // Ignore parse errors
                        }
                    }
                }
            }
        }

        // Rating (MobyGames scores are out of 10, convert to 100)
        double moby_score = get_number(game, "moby_score");
        if (moby_score > 0) {
            metadata.total_rating = moby_score * 10;
        }

        return metadata;
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
};

namespace {
[[maybe_unused]] ProviderRegistrar mobygames_registrar(
    "mobygames",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<MobyGamesProvider>(config, std::move(cache));
    });
}

}  // namespace retro_metadata
