/// @file steamgriddb.cpp
/// @brief SteamGridDB provider implementation for artwork fetching

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
#include <string>
#include <vector>

namespace retro_metadata {

namespace {

/// Base URL for the SteamGridDB API
const std::string kBaseURL = "https://www.steamgriddb.com/api/v2";

/// Regex to detect SteamGridDB ID tags in filenames like (sgdb-12345)
const std::regex kSgdbTagRegex(R"(\(sgdb-(\d+)\))", std::regex::icase);

/// @brief SteamGridDB grid dimension options
enum class SGDBDimension {
    // Vertical grids
    SteamVertical,   // 600x900
    GOGGalaxy,       // 342x482
    Square,          // 512x512
    SquareIcon,      // 256x256
    // Horizontal grids
    SteamHorizontal, // 460x215
    Legacy,          // 920x430
    Old,             // 460x215
    // Heroes
    HeroBlurred,     // 1920x620
    HeroMaterial,    // 3840x1240
    // Logos
    LogoCustom       // custom
};

/// @brief SteamGridDB artwork style options
enum class SGDBStyle {
    // Grid styles
    Alternate,
    Blurred,
    WhiteLogo,
    Material,
    NoLogo,
    // Logo styles
    LogoOfficial,
    LogoWhite,
    LogoBlack,
    LogoCustom
};

/// @brief SteamGridDB MIME type options
enum class SGDBMime {
    PNG,
    JPEG,
    WEBP,
    ICO
};

std::string get_string(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key) && j[key].is_string()) {
        return j[key].get<std::string>();
    }
    return "";
}

double get_number(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key) && j[key].is_number()) {
        return j[key].get<double>();
    }
    return 0.0;
}

bool get_bool(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key) && j[key].is_boolean()) {
        return j[key].get<bool>();
    }
    return false;
}

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

std::string url_encode(const std::string& str) {
    std::string encoded;
    for (char c : str) {
        if (std::isalnum(static_cast<unsigned char>(c)) || c == '-' || c == '_' || c == '.' || c == '~') {
            encoded += c;
        } else if (c == ' ') {
            encoded += "%20";
        } else {
            char buf[4];
            snprintf(buf, sizeof(buf), "%%%02X", static_cast<unsigned char>(c));
            encoded += buf;
        }
    }
    return encoded;
}

}  // namespace

/// @brief SteamGridDB metadata provider for artwork
class SteamGridDBProvider : public Provider {
public:
    SteamGridDBProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache)
        : config_(config), cache_(std::move(cache)), nsfw_(false), humor_(true), epilepsy_(true) {
        // Check options for content filters
        if (auto it = config_.options.find("nsfw"); it != config_.options.end()) {
            try {
                nsfw_ = std::any_cast<bool>(it->second);
            } catch (...) {}
        }
        if (auto it = config_.options.find("humor"); it != config_.options.end()) {
            try {
                humor_ = std::any_cast<bool>(it->second);
            } catch (...) {}
        }
        if (auto it = config_.options.find("epilepsy"); it != config_.options.end()) {
            try {
                epilepsy_ = std::any_cast<bool>(it->second);
            } catch (...) {}
        }
    }

    std::string name() const override { return "steamgriddb"; }

    std::vector<SearchResult> search(const std::string& query, const SearchOptions& opts) override {
        if (!config_.is_configured()) return {};

        auto response = request("/search/autocomplete/" + url_encode(query));
        if (response.empty() || !get_bool(response, "success")) {
            return {};
        }

        if (!response.contains("data") || !response["data"].is_array()) {
            return {};
        }

        int limit = opts.limit > 0 ? opts.limit : 10;
        std::vector<SearchResult> results;

        for (const auto& item : response["data"]) {
            if (static_cast<int>(results.size()) >= limit) break;

            int game_id = static_cast<int>(get_number(item, "id"));
            if (game_id == 0) continue;

            SearchResult sr;
            sr.provider = name();
            sr.provider_id = game_id;
            sr.name = get_string(item, "name");

            // Try to get cover image from grids
            auto grids = fetch_grids(game_id);
            if (!grids.empty() && grids[0].contains("url")) {
                sr.cover_url = get_string(grids[0], "url");
            }

            double release_date = get_number(item, "release_date");
            if (release_date > 0) {
                sr.release_year = static_cast<int>(release_date);
            }

            results.push_back(std::move(sr));
        }

        return results;
    }

    std::unique_ptr<GameResult> get_by_id(int game_id) override {
        if (!config_.is_configured()) return nullptr;

        auto response = request("/games/id/" + std::to_string(game_id));
        if (response.empty() || !get_bool(response, "success")) {
            return nullptr;
        }

        if (!response.contains("data") || !response["data"].is_object()) {
            return nullptr;
        }

        const auto& game = response["data"];
        auto artwork = fetch_all_artwork(game_id);

        auto result = std::make_unique<GameResult>();
        result->provider = name();
        result->provider_id = game_id;
        result->provider_ids = {{"steamgriddb", game_id}};
        result->name = get_string(game, "name");
        result->artwork = artwork;

        double release_date = get_number(game, "release_date");
        if (release_date > 0) {
            result->metadata.release_year = static_cast<int>(release_date);
        }

        result->raw_response = game;
        return result;
    }

    std::unique_ptr<GameResult> identify(const std::string& filename, const IdentifyOptions& /*opts*/) override {
        if (!config_.is_configured()) return nullptr;

        // Check for SteamGridDB ID tag in filename
        std::smatch match;
        if (std::regex_search(filename, match, kSgdbTagRegex) && match.size() > 1) {
            try {
                int id = std::stoi(match[1].str());
                auto result = get_by_id(id);
                if (result) {
                    result->match_type = "tag";
                    result->match_score = 1.0;
                    return result;
                }
            } catch (...) {}
        }

        // Clean the filename
        std::string search_term = clean_filename(filename);
        search_term = normalization::normalize_search_term_default(search_term);

        // Search for the game
        auto response = request("/search/autocomplete/" + url_encode(search_term));
        if (response.empty() || !get_bool(response, "success")) {
            return nullptr;
        }

        if (!response.contains("data") || !response["data"].is_array() || response["data"].empty()) {
            return nullptr;
        }

        // Build name to game map
        std::map<std::string, nlohmann::json> games_by_name;
        std::vector<std::string> names;
        for (const auto& item : response["data"]) {
            std::string game_name = get_string(item, "name");
            if (!game_name.empty()) {
                games_by_name[game_name] = item;
                names.push_back(game_name);
            }
        }

        // Find best match
        auto best = matching::find_best_match_simple(search_term, names);
        if (!best.found()) {
            return nullptr;
        }

        const auto& game = games_by_name[best.match];
        int game_id = static_cast<int>(get_number(game, "id"));
        auto artwork = fetch_all_artwork(game_id);

        auto result = std::make_unique<GameResult>();
        result->provider = name();
        result->provider_id = game_id;
        result->provider_ids = {{"steamgriddb", game_id}};
        result->name = get_string(game, "name");
        result->artwork = artwork;
        result->match_score = best.score;
        result->match_type = "filename";

        double release_date = get_number(game, "release_date");
        if (release_date > 0) {
            result->metadata.release_year = static_cast<int>(release_date);
        }

        result->raw_response = game;
        return result;
    }

    void heartbeat() override {
        if (!config_.is_configured()) {
            throw AuthError(name(), "provider not configured");
        }

        // Try a simple search to check connectivity
        auto response = request("/search/autocomplete/test");
        // If we get here without throwing, the provider is available
    }

    void close() override {}

private:
    /// @brief Makes an authenticated request to the SteamGridDB API
    nlohmann::json request(const std::string& endpoint, const cpr::Parameters& params = {}) {
        std::string api_key = config_.get_credential("api_key");

        std::string url = kBaseURL + endpoint;
        cpr::Response r = cpr::Get(
            cpr::Url{url},
            cpr::Header{
                {"Accept", "application/json"},
                {"Authorization", "Bearer " + api_key}
            },
            params,
            cpr::Timeout{config_.timeout * 1000}
        );

        if (r.status_code == 401) {
            throw AuthError(name(), "invalid API key");
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
            throw ConnectionError(name(), "failed to parse JSON response");
        }
    }

    /// @brief Builds filter parameters for artwork requests
    cpr::Parameters build_filter_params() {
        cpr::Parameters params;

        // Content filters
        if (nsfw_) {
            params.Add({"nsfw", "any"});
        } else {
            params.Add({"nsfw", "false"});
        }

        if (humor_) {
            params.Add({"humor", "any"});
        } else {
            params.Add({"humor", "false"});
        }

        if (epilepsy_) {
            params.Add({"epilepsy", "any"});
        } else {
            params.Add({"epilepsy", "false"});
        }

        return params;
    }

    /// @brief Fetches grids (covers) for a game
    std::vector<nlohmann::json> fetch_grids(int game_id) {
        try {
            auto response = request("/grids/game/" + std::to_string(game_id), build_filter_params());
            if (!get_bool(response, "success")) {
                return {};
            }

            if (!response.contains("data") || !response["data"].is_array()) {
                return {};
            }

            std::vector<nlohmann::json> grids;
            for (const auto& item : response["data"]) {
                if (item.is_object()) {
                    grids.push_back(item);
                }
            }
            return grids;
        } catch (...) {
            return {};
        }
    }

    /// @brief Fetches heroes (banners/backgrounds) for a game
    std::vector<nlohmann::json> fetch_heroes(int game_id) {
        try {
            auto response = request("/heroes/game/" + std::to_string(game_id), build_filter_params());
            if (!get_bool(response, "success")) {
                return {};
            }

            if (!response.contains("data") || !response["data"].is_array()) {
                return {};
            }

            std::vector<nlohmann::json> heroes;
            for (const auto& item : response["data"]) {
                if (item.is_object()) {
                    heroes.push_back(item);
                }
            }
            return heroes;
        } catch (...) {
            return {};
        }
    }

    /// @brief Fetches logos for a game
    std::vector<nlohmann::json> fetch_logos(int game_id) {
        try {
            auto response = request("/logos/game/" + std::to_string(game_id), build_filter_params());
            if (!get_bool(response, "success")) {
                return {};
            }

            if (!response.contains("data") || !response["data"].is_array()) {
                return {};
            }

            std::vector<nlohmann::json> logos;
            for (const auto& item : response["data"]) {
                if (item.is_object()) {
                    logos.push_back(item);
                }
            }
            return logos;
        } catch (...) {
            return {};
        }
    }

    /// @brief Fetches icons for a game
    std::vector<nlohmann::json> fetch_icons(int game_id) {
        try {
            auto response = request("/icons/game/" + std::to_string(game_id), build_filter_params());
            if (!get_bool(response, "success")) {
                return {};
            }

            if (!response.contains("data") || !response["data"].is_array()) {
                return {};
            }

            std::vector<nlohmann::json> icons;
            for (const auto& item : response["data"]) {
                if (item.is_object()) {
                    icons.push_back(item);
                }
            }
            return icons;
        } catch (...) {
            return {};
        }
    }

    /// @brief Fetches all artwork types for a game
    Artwork fetch_all_artwork(int game_id) {
        Artwork artwork;

        // Fetch grids (covers)
        auto grids = fetch_grids(game_id);
        if (!grids.empty()) {
            artwork.cover_url = get_string(grids[0], "url");
        }

        // Fetch heroes (banners/backgrounds)
        auto heroes = fetch_heroes(game_id);
        if (!heroes.empty()) {
            artwork.background_url = get_string(heroes[0], "url");
            if (heroes.size() > 1) {
                artwork.banner_url = get_string(heroes[1], "url");
            }
        }

        // Fetch logos
        auto logos = fetch_logos(game_id);
        if (!logos.empty()) {
            artwork.logo_url = get_string(logos[0], "url");
        }

        // Fetch icons
        auto icons = fetch_icons(game_id);
        if (!icons.empty()) {
            artwork.icon_url = get_string(icons[0], "url");
        }

        return artwork;
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
    bool nsfw_;
    bool humor_;
    bool epilepsy_;
};

namespace {
[[maybe_unused]] ProviderRegistrar steamgriddb_registrar(
    "steamgriddb",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<SteamGridDBProvider>(config, std::move(cache));
    });
}

}  // namespace retro_metadata
