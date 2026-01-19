/// @file retroachievements.cpp
/// @brief RetroAchievements metadata provider implementation

#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/errors.hpp>
#include <retro_metadata/internal/matching.hpp>
#include <retro_metadata/internal/normalization.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>

#include <cpr/cpr.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <map>
#include <regex>
#include <string>

namespace retro_metadata {

namespace {

/// @brief Base URL for RetroAchievements API
const std::string kRABaseURL = "https://retroachievements.org/API";

/// @brief Media URL for RetroAchievements assets
const std::string kRAMediaURL = "https://media.retroachievements.org";

/// @brief Badge URL for achievement images
const std::string kRABadgeURL = "https://media.retroachievements.org/Badge";

/// @brief Regex pattern for RA ID tags in filenames like (ra-12345)
const std::regex kRATagRegex(R"(\(ra-(\d+)\))", std::regex::icase);

/// @brief Maps RetroAchievements console IDs to platform names
const std::map<int, std::string> kRAPlatformNames = {
    {1, "Mega Drive"},
    {2, "Nintendo 64"},
    {3, "SNES"},
    {4, "Game Boy"},
    {5, "Game Boy Advance"},
    {6, "Game Boy Color"},
    {7, "NES"},
    {8, "TurboGrafx-16"},
    {9, "Mega CD"},
    {10, "32X"},
    {11, "Master System"},
    {12, "PlayStation"},
    {13, "Lynx"},
    {14, "Neo Geo Pocket"},
    {15, "Game Gear"},
    {16, "GameCube"},
    {17, "Jaguar"},
    {18, "Nintendo DS"},
    {19, "Wii"},
    {21, "PlayStation 2"},
    {23, "Odyssey 2"},
    {24, "Pokemon Mini"},
    {25, "Atari 2600"},
    {27, "Arcade"},
    {28, "Virtual Boy"},
    {29, "MSX"},
    {33, "SG-1000"},
    {34, "ZX Spectrum"},
    {36, "Atari ST"},
    {37, "Amstrad CPC"},
    {38, "Apple II"},
    {39, "Saturn"},
    {40, "Dreamcast"},
    {41, "PSP"},
    {43, "3DO"},
    {44, "ColecoVision"},
    {45, "Intellivision"},
    {46, "Vectrex"},
    {47, "PC-8000/8800"},
    {48, "PC-9800"},
    {49, "PC-FX"},
    {50, "Atari 5200"},
    {51, "Atari 7800"},
    {52, "Sharp X68000"},
    {53, "WonderSwan"},
    {56, "Neo Geo CD"},
    {57, "Fairchild Channel F"},
    {63, "Watara Supervision"},
    {69, "Mega Duck"},
    {71, "Arduboy"},
    {72, "WASM-4"},
    {73, "Arcadia 2001"},
    {75, "Interton VC 4000"},
    {76, "SuperGrafx"},
    {77, "Atari Jaguar CD"},
    {78, "Nintendo DSi"},
    {80, "Uzebox"},
};

/// @brief Safely extracts a string from JSON
std::string get_string(const nlohmann::json& j, const std::string& key) {
    if (!j.contains(key) || j[key].is_null()) {
        return "";
    }
    if (j[key].is_string()) {
        return j[key].get<std::string>();
    }
    if (j[key].is_number()) {
        if (j[key].is_number_integer()) {
            return std::to_string(j[key].get<int64_t>());
        }
        return std::to_string(j[key].get<double>());
    }
    return "";
}

/// @brief Safely extracts an integer from JSON
int get_int(const nlohmann::json& j, const std::string& key) {
    if (!j.contains(key) || j[key].is_null()) {
        return 0;
    }
    if (j[key].is_number()) {
        return j[key].get<int>();
    }
    if (j[key].is_string()) {
        try {
            return std::stoi(j[key].get<std::string>());
        } catch (...) {
            return 0;
        }
    }
    return 0;
}

/// @brief Cleans a filename for searching
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

/// @brief Converts a string to lowercase
std::string to_lower(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

}  // namespace

/// @brief Represents a RetroAchievements achievement
struct RAGameAchievement {
    int id = 0;
    std::string title;
    std::string description;
    int points = 0;
    std::string badge_id;
    std::string badge_url;
    std::string badge_url_locked;
    std::string type;
    int num_awarded = 0;
    int num_awarded_hardcore = 0;
    int display_order = 0;
};

/// @brief RetroAchievements metadata provider
///
/// This provider implements the HashProvider interface for hash-based game identification.
/// It provides access to RetroAchievements game metadata including achievements,
/// artwork, and platform information.
class RetroAchievementsProvider : public HashProvider {
public:
    RetroAchievementsProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache)
        : config_(config), cache_(std::move(cache)), user_agent_("retro-metadata/1.0") {}

    std::string name() const override { return "retroachievements"; }

    /// @brief Searches for games by name
    ///
    /// Note: RetroAchievements doesn't have a search endpoint, so this fetches the
    /// game list for the platform and filters locally.
    std::vector<SearchResult> search(const std::string& query, const SearchOptions& opts) override {
        if (!config_.is_configured()) return {};

        // RetroAchievements requires a platform ID to search
        if (!opts.platform_id) {
            return {};
        }

        // Get game list for platform
        std::map<std::string, std::string> params = {
            {"i", std::to_string(*opts.platform_id)},
            {"f", "1"},  // Only games with achievements
            {"h", "0"}   // Don't include hashes
        };

        nlohmann::json result;
        try {
            result = request("/API_GetGameList.php", params);
        } catch (...) {
            return {};
        }

        if (!result.is_array()) {
            return {};
        }

        // Filter by query
        std::string query_lower = to_lower(query);
        int limit = opts.limit > 0 ? opts.limit : 25;

        std::vector<SearchResult> search_results;
        for (const auto& game : result) {
            if (!game.is_object()) continue;

            std::string title = get_string(game, "Title");
            std::string title_lower = to_lower(title);

            if (title_lower.find(query_lower) == std::string::npos) {
                continue;
            }

            SearchResult sr;
            sr.provider = name();
            sr.provider_id = get_int(game, "ID");
            sr.name = title;

            std::string icon = get_string(game, "ImageIcon");
            if (!icon.empty()) {
                sr.cover_url = kRAMediaURL + icon;
            }

            std::string console_name = get_string(game, "ConsoleName");
            if (!console_name.empty()) {
                sr.platforms.push_back(console_name);
            }

            search_results.push_back(std::move(sr));

            if (static_cast<int>(search_results.size()) >= limit) {
                break;
            }
        }

        return search_results;
    }

    /// @brief Gets game details by RetroAchievements ID
    std::unique_ptr<GameResult> get_by_id(int game_id) override {
        if (!config_.is_configured()) return nullptr;

        std::map<std::string, std::string> params = {{"i", std::to_string(game_id)}};

        nlohmann::json result;
        try {
            result = request("/API_GetGameExtended.php", params);
        } catch (...) {
            return nullptr;
        }

        if (!result.is_object() || get_int(result, "ID") == 0) {
            return nullptr;
        }

        return build_game_result(result);
    }

    /// @brief Identifies a game from a ROM filename
    std::unique_ptr<GameResult> identify(
        const std::string& filename, const IdentifyOptions& opts) override {
        if (!config_.is_configured()) return nullptr;

        // Check for RetroAchievements ID tag in filename
        std::smatch match;
        if (std::regex_search(filename, match, kRATagRegex) && match.size() > 1) {
            try {
                int id = std::stoi(match[1].str());
                auto result = get_by_id(id);
                if (result) {
                    result->match_type = "tag";
                    return result;
                }
            } catch (...) {
                // Continue to filename search
            }
        }

        // Need platform ID to search game list
        if (!opts.platform_id) {
            return nullptr;
        }

        // Clean the filename and search
        std::string search_term = clean_filename(filename);
        search_term = normalization::normalize_search_term_default(search_term);

        // Get game list for platform
        std::map<std::string, std::string> params = {
            {"i", std::to_string(*opts.platform_id)},
            {"f", "1"},
            {"h", "0"}
        };

        nlohmann::json result;
        try {
            result = request("/API_GetGameList.php", params);
        } catch (...) {
            return nullptr;
        }

        if (!result.is_array() || result.empty()) {
            return nullptr;
        }

        // Build name mapping
        std::map<std::string, nlohmann::json> games_by_name;
        std::vector<std::string> names;
        for (const auto& game : result) {
            if (!game.is_object()) continue;

            std::string title = get_string(game, "Title");
            if (!title.empty()) {
                games_by_name[title] = game;
                names.push_back(title);
            }
        }

        // Find best match
        matching::FindBestMatchOptions match_opts;
        match_opts.min_similarity_score = 0.6;
        auto best = matching::find_best_match(search_term, names, match_opts);

        if (!best.found()) {
            return nullptr;
        }

        auto it = games_by_name.find(best.match);
        if (it == games_by_name.end()) {
            return nullptr;
        }

        // Get full game details
        auto game_result = get_by_id(get_int(it->second, "ID"));
        if (game_result) {
            game_result->match_score = best.score;
            game_result->match_type = "filename";
        }
        return game_result;
    }

    /// @brief Identifies a game using file hashes (MD5)
    std::unique_ptr<GameResult> identify_by_hash(
        const FileHashes& hashes, const IdentifyOptions& opts) override {
        if (!opts.platform_id) {
            return nullptr;
        }
        return lookup_by_hash(*opts.platform_id, hashes.md5);
    }

    /// @brief Checks if the provider API is accessible
    void heartbeat() override {
        std::map<std::string, std::string> params = {
            {"i", "1"},
            {"f", "1"},
            {"h", "0"}
        };
        request("/API_GetGameList.php", params);
    }

    void close() override {}

    /// @brief Gets all achievements for a game
    std::vector<RAGameAchievement> get_achievements(int game_id) {
        if (!config_.is_configured()) return {};

        std::map<std::string, std::string> params = {{"i", std::to_string(game_id)}};

        nlohmann::json result;
        try {
            result = request("/API_GetGameExtended.php", params);
        } catch (...) {
            return {};
        }

        if (!result.is_object()) {
            return {};
        }

        if (!result.contains("Achievements") || !result["Achievements"].is_object()) {
            return {};
        }

        std::vector<RAGameAchievement> achievements;
        for (const auto& [key, ach_data] : result["Achievements"].items()) {
            if (!ach_data.is_object()) continue;

            RAGameAchievement ach;
            ach.id = get_int(ach_data, "ID");
            ach.title = get_string(ach_data, "Title");
            ach.description = get_string(ach_data, "Description");
            ach.points = get_int(ach_data, "Points");
            ach.badge_id = get_string(ach_data, "BadgeName");
            ach.type = get_string(ach_data, "type");
            ach.num_awarded = get_int(ach_data, "NumAwarded");
            ach.num_awarded_hardcore = get_int(ach_data, "NumAwardedHardcore");
            ach.display_order = get_int(ach_data, "DisplayOrder");

            if (!ach.badge_id.empty()) {
                ach.badge_url = kRABadgeURL + "/" + ach.badge_id + ".png";
                ach.badge_url_locked = kRABadgeURL + "/" + ach.badge_id + "_lock.png";
            }

            achievements.push_back(std::move(ach));
        }

        return achievements;
    }

    /// @brief Looks up a game by ROM MD5 hash
    std::unique_ptr<GameResult> lookup_by_hash(int platform_id, const std::string& md5) {
        if (!config_.is_configured() || md5.empty()) {
            return nullptr;
        }

        // Get game list with hashes
        std::map<std::string, std::string> params = {
            {"i", std::to_string(platform_id)},
            {"f", "1"},  // Only games with achievements
            {"h", "1"}   // Include hashes
        };

        nlohmann::json result;
        try {
            result = request("/API_GetGameList.php", params);
        } catch (...) {
            return nullptr;
        }

        if (!result.is_array()) {
            return nullptr;
        }

        // Find matching hash
        std::string md5_lower = to_lower(md5);
        for (const auto& game : result) {
            if (!game.is_object()) continue;

            if (!game.contains("Hashes") || !game["Hashes"].is_array()) {
                continue;
            }

            for (const auto& hash : game["Hashes"]) {
                if (!hash.is_string()) continue;

                std::string hash_str = to_lower(hash.get<std::string>());
                if (hash_str == md5_lower) {
                    // Get full game details
                    auto game_result = get_by_id(get_int(game, "ID"));
                    if (game_result) {
                        game_result->match_type = "hash";
                        game_result->match_score = 1.0;
                    }
                    return game_result;
                }
            }
        }

        return nullptr;
    }

    /// @brief Returns platform name for a RetroAchievements console ID
    static std::string get_platform_name(int console_id) {
        auto it = kRAPlatformNames.find(console_id);
        if (it != kRAPlatformNames.end()) {
            return it->second;
        }
        return "";
    }

private:
    /// @brief Makes an API request
    nlohmann::json request(
        const std::string& endpoint, const std::map<std::string, std::string>& params) {
        std::string url = kRABaseURL + endpoint;

        cpr::Parameters cpr_params;
        cpr_params.Add({"z", username()});
        cpr_params.Add({"y", api_key()});
        for (const auto& [key, value] : params) {
            cpr_params.Add({key, value});
        }

        cpr::Response r = cpr::Get(
            cpr::Url{url},
            cpr_params,
            cpr::Header{{"User-Agent", user_agent_}},
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

        return nlohmann::json::parse(r.text);
    }

    /// @brief Gets the API key from config
    std::string api_key() const {
        return config_.get_credential("api_key");
    }

    /// @brief Gets the username from config
    std::string username() const {
        std::string user = config_.get_credential("username");
        if (user.empty()) {
            return "retro-metadata";
        }
        return user;
    }

    /// @brief Builds a GameResult from API response
    std::unique_ptr<GameResult> build_game_result(const nlohmann::json& game) {
        auto result = std::make_unique<GameResult>();
        int game_id = get_int(game, "ID");

        result->provider = name();
        result->provider_id = game_id;
        result->provider_ids = {{"retroachievements", game_id}};
        result->name = get_string(game, "Title");
        result->summary = "";  // RA doesn't provide game descriptions

        // Build artwork URLs
        std::string icon = get_string(game, "ImageIcon");
        std::string title_img = get_string(game, "ImageTitle");
        std::string ingame_img = get_string(game, "ImageIngame");
        std::string boxart_img = get_string(game, "ImageBoxArt");

        // Cover priority: boxart > title
        if (!boxart_img.empty()) {
            result->artwork.cover_url = kRAMediaURL + boxart_img;
        } else if (!title_img.empty()) {
            result->artwork.cover_url = kRAMediaURL + title_img;
        }

        // Screenshots
        if (!ingame_img.empty()) {
            result->artwork.screenshot_urls.push_back(kRAMediaURL + ingame_img);
        }
        if (!title_img.empty() && title_img != boxart_img) {
            result->artwork.screenshot_urls.push_back(kRAMediaURL + title_img);
        }

        // Icon
        if (!icon.empty()) {
            result->artwork.icon_url = kRAMediaURL + icon;
        }

        // Extract metadata
        result->metadata = extract_metadata(game);
        result->raw_response = game;

        return result;
    }

    /// @brief Extracts metadata from API response
    GameMetadata extract_metadata(const nlohmann::json& game) {
        GameMetadata metadata;
        metadata.raw_data = game;

        // Genre
        std::string genre = get_string(game, "Genre");
        if (!genre.empty()) {
            metadata.genres = {genre};
        }

        // Companies
        std::string publisher = get_string(game, "Publisher");
        if (!publisher.empty()) {
            metadata.companies.push_back(publisher);
            metadata.publisher = publisher;
        }

        std::string developer = get_string(game, "Developer");
        if (!developer.empty()) {
            // Avoid duplicates
            bool found = false;
            for (const auto& c : metadata.companies) {
                if (c == developer) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                metadata.companies.push_back(developer);
            }
            metadata.developer = developer;
        }

        // Release date
        std::string released = get_string(game, "Released");
        if (!released.empty()) {
            // Handle "YYYY-MM-DD extra info" format
            std::string date_str = released;
            size_t space_pos = released.find(' ');
            if (space_pos != std::string::npos) {
                date_str = released.substr(0, space_pos);
            }

            // Parse date
            std::tm tm = {};
            if (strptime(date_str.c_str(), "%Y-%m-%d", &tm) != nullptr) {
                metadata.first_release_date = mktime(&tm);
                metadata.release_year = 1900 + tm.tm_year;
            }
        }

        // Platform info
        std::string console_name = get_string(game, "ConsoleName");
        if (!console_name.empty()) {
            Platform plat;
            plat.name = console_name;
            plat.provider_ids = {{"retroachievements", get_int(game, "ConsoleID")}};
            metadata.platforms.push_back(std::move(plat));
        }

        return metadata;
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
    std::string user_agent_;
};

namespace {
[[maybe_unused]] ProviderRegistrar retroachievements_registrar(
    "retroachievements",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<RetroAchievementsProvider>(config, std::move(cache));
    });
}

}  // namespace retro_metadata
