// TheGamesDB metadata provider implementation
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
#include <set>

namespace retro_metadata {

namespace {

// Regex to detect TheGamesDB ID tags in filenames like (tgdb-12345)
const std::regex kTgdbTagRegex(R"(\(tgdb-(\d+)\))", std::regex::icase);

// Base URL for TheGamesDB API
const std::string kBaseURL = "https://api.thegamesdb.net/v1";

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

// Extract boxart data from the include section of the response
nlohmann::json get_boxart_data(const nlohmann::json& result) {
    if (result.contains("include") && result["include"].is_object()) {
        const auto& include = result["include"];
        if (include.contains("boxart") && include["boxart"].is_object()) {
            return include["boxart"];
        }
    }
    return nlohmann::json();
}

// Get base URLs for boxart (thumb and original)
std::map<std::string, std::string> get_boxart_base_url(const nlohmann::json& boxart_data) {
    std::map<std::string, std::string> base_urls;
    if (!boxart_data.is_null() && boxart_data.contains("base_url") && boxart_data["base_url"].is_object()) {
        for (const auto& [key, value] : boxart_data["base_url"].items()) {
            if (value.is_string()) {
                base_urls[key] = value.get<std::string>();
            }
        }
    }
    return base_urls;
}

// Get cover URL (front boxart) for a game
std::string get_cover_url(const nlohmann::json& boxart_data, int game_id,
                          const std::map<std::string, std::string>& base_urls) {
    if (boxart_data.is_null() || base_urls.empty()) return "";

    if (!boxart_data.contains("data") || !boxart_data["data"].is_object()) return "";

    std::string game_id_str = std::to_string(game_id);
    const auto& data = boxart_data["data"];

    if (!data.contains(game_id_str) || !data[game_id_str].is_array()) return "";

    for (const auto& art : data[game_id_str]) {
        if (!art.is_object()) continue;
        if (get_string(art, "side") == "front") {
            auto thumb_it = base_urls.find("thumb");
            if (thumb_it != base_urls.end()) {
                return thumb_it->second + get_string(art, "filename");
            }
        }
    }
    return "";
}

// Get back cover URLs (used as screenshots)
std::vector<std::string> get_back_cover_urls(const nlohmann::json& boxart_data, int game_id,
                                              const std::map<std::string, std::string>& base_urls) {
    std::vector<std::string> urls;
    if (boxart_data.is_null() || base_urls.empty()) return urls;

    if (!boxart_data.contains("data") || !boxart_data["data"].is_object()) return urls;

    std::string game_id_str = std::to_string(game_id);
    const auto& data = boxart_data["data"];

    if (!data.contains(game_id_str) || !data[game_id_str].is_array()) return urls;

    for (const auto& art : data[game_id_str]) {
        if (!art.is_object()) continue;
        if (get_string(art, "side") == "back") {
            auto original_it = base_urls.find("original");
            if (original_it != base_urls.end()) {
                urls.push_back(original_it->second + get_string(art, "filename"));
            }
        }
    }
    return urls;
}

// Get string values from array or map (TGDB returns both formats)
std::vector<std::string> get_string_slice_or_map(const nlohmann::json& j, const std::string& key) {
    std::vector<std::string> result;
    if (!j.contains(key)) return result;

    const auto& value = j[key];
    if (value.is_array()) {
        for (const auto& item : value) {
            if (item.is_string()) {
                result.push_back(item.get<std::string>());
            }
        }
    } else if (value.is_object()) {
        for (const auto& [k, v] : value.items()) {
            if (v.is_string()) {
                result.push_back(v.get<std::string>());
            }
        }
    }
    return result;
}

}  // namespace

/// @brief TheGamesDB metadata provider
class TheGamesDBProvider : public Provider {
public:
    TheGamesDBProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache)
        : config_(config), cache_(std::move(cache)) {}

    std::string name() const override { return "thegamesdb"; }

    std::vector<SearchResult> search(const std::string& query, const SearchOptions& opts) override {
        if (!config_.is_configured()) return {};

        cpr::Parameters params;
        params.Add({"name", query});
        params.Add({"apikey", api_key()});
        params.Add({"fields", "players,publishers,genres,overview,rating"});
        params.Add({"include", "boxart"});

        if (opts.platform_id) {
            params.Add({"filter[platform]", std::to_string(*opts.platform_id)});
        }

        auto response = request("/Games/ByGameName", params);
        if (response.is_null()) return {};

        if (!response.contains("data") || !response["data"].is_object()) return {};
        const auto& data = response["data"];

        if (!data.contains("games") || !data["games"].is_array()) return {};
        const auto& games = data["games"];

        auto boxart_data = get_boxart_data(response);
        auto base_urls = get_boxart_base_url(boxart_data);

        int limit = opts.limit > 0 ? opts.limit : 20;

        std::vector<SearchResult> results;
        int count = 0;
        for (const auto& game : games) {
            if (count >= limit) break;
            if (!game.is_object()) continue;

            int game_id = static_cast<int>(get_number(game, "id"));
            if (game_id == 0) continue;

            SearchResult sr;
            sr.provider = name();
            sr.provider_id = game_id;
            sr.name = get_string(game, "game_title");
            sr.cover_url = get_cover_url(boxart_data, game_id, base_urls);

            // Platform as string
            int platform_id = static_cast<int>(get_number(game, "platform"));
            if (platform_id > 0) {
                sr.platforms.push_back(std::to_string(platform_id));
            }

            // Release year from release_date
            std::string date_str = get_string(game, "release_date");
            if (date_str.length() >= 4) {
                try {
                    sr.release_year = std::stoi(date_str.substr(0, 4));
                } catch (...) {}
            }

            results.push_back(std::move(sr));
            ++count;
        }

        return results;
    }

    std::unique_ptr<GameResult> get_by_id(int game_id) override {
        if (!config_.is_configured()) return nullptr;

        cpr::Parameters params;
        params.Add({"id", std::to_string(game_id)});
        params.Add({"apikey", api_key()});
        params.Add({"fields", "players,publishers,genres,overview,rating,platform"});
        params.Add({"include", "boxart"});

        auto response = request("/Games/ByGameID", params);
        if (response.is_null()) return nullptr;

        if (!response.contains("data") || !response["data"].is_object()) return nullptr;
        const auto& data = response["data"];

        if (!data.contains("games")) return nullptr;

        auto boxart_data = get_boxart_data(response);
        nlohmann::json game;

        // TGDB can return games as array or map
        if (data["games"].is_array()) {
            if (data["games"].empty()) return nullptr;
            game = data["games"][0];
        } else if (data["games"].is_object()) {
            std::string game_id_str = std::to_string(game_id);
            if (data["games"].contains(game_id_str)) {
                game = data["games"][game_id_str];
            } else {
                return nullptr;
            }
        } else {
            return nullptr;
        }

        return build_game_result(game, boxart_data);
    }

    std::unique_ptr<GameResult> identify(const std::string& filename, const IdentifyOptions& opts) override {
        if (!config_.is_configured()) return nullptr;

        // Check for TheGamesDB ID tag in filename
        std::smatch match;
        if (std::regex_search(filename, match, kTgdbTagRegex) && match.size() > 1) {
            try {
                int id = std::stoi(match[1].str());
                auto result = get_by_id(id);
                if (result) return result;
            } catch (...) {}
        }

        if (!opts.platform_id) return nullptr;

        // Clean the filename for searching
        std::string search_term = clean_filename(filename);

        cpr::Parameters params;
        params.Add({"name", search_term});
        params.Add({"apikey", api_key()});
        params.Add({"filter[platform]", std::to_string(*opts.platform_id)});
        params.Add({"fields", "players,publishers,genres,overview,rating"});
        params.Add({"include", "boxart"});

        auto response = request("/Games/ByGameName", params);
        if (response.is_null()) return nullptr;

        if (!response.contains("data") || !response["data"].is_object()) return nullptr;
        const auto& data = response["data"];

        if (!data.contains("games") || !data["games"].is_array() || data["games"].empty()) {
            return nullptr;
        }

        auto boxart_data = get_boxart_data(response);

        // Build name to game map
        std::map<std::string, nlohmann::json> games_by_name;
        std::vector<std::string> names;
        for (const auto& game : data["games"]) {
            if (!game.is_object()) continue;
            std::string game_name = get_string(game, "game_title");
            if (!game_name.empty()) {
                games_by_name[game_name] = game;
                names.push_back(game_name);
            }
        }

        // Find best match
        auto best = matching::find_best_match_simple(search_term, names);
        if (!best.found()) return nullptr;

        auto result = build_game_result(games_by_name[best.match], boxart_data);
        result->match_score = best.score;
        return result;
    }

    void heartbeat() override {
        if (!config_.is_configured()) {
            throw AuthError(name(), "provider not configured");
        }

        // Try a simple search to check connectivity
        cpr::Parameters params;
        params.Add({"name", "test"});
        params.Add({"apikey", api_key()});

        auto response = request("/Games/ByGameName", params);
        // If we get here without exception, the API is accessible
    }

    void close() override {}

private:
    std::string api_key() const {
        return config_.get_credential("api_key");
    }

    nlohmann::json request(const std::string& endpoint, const cpr::Parameters& params) {
        cpr::Response r = cpr::Get(
            cpr::Url{kBaseURL + endpoint},
            params,
            cpr::Header{{"User-Agent", "retro-metadata/1.0"}}
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
        } catch (...) {
            throw ConnectionError(name(), "failed to parse JSON response");
        }
    }

    std::unique_ptr<GameResult> build_game_result(const nlohmann::json& game, const nlohmann::json& boxart_data) {
        auto result = std::make_unique<GameResult>();
        int game_id = static_cast<int>(get_number(game, "id"));

        auto base_urls = get_boxart_base_url(boxart_data);

        result->provider = name();
        result->provider_id = game_id;
        result->provider_ids = {{"thegamesdb", game_id}};
        result->name = get_string(game, "game_title");
        result->summary = get_string(game, "overview");

        // Artwork
        result->artwork.cover_url = get_cover_url(boxart_data, game_id, base_urls);
        result->artwork.screenshot_urls = get_back_cover_urls(boxart_data, game_id, base_urls);

        // Metadata
        extract_metadata(game, result->metadata);

        result->raw_response = game;
        return result;
    }

    void extract_metadata(const nlohmann::json& game, GameMetadata& metadata) {
        // Release year from release_date
        std::string date_str = get_string(game, "release_date");
        if (date_str.length() >= 4) {
            try {
                metadata.release_year = std::stoi(date_str.substr(0, 4));
            } catch (...) {}
        }

        // Genres (can be array or map)
        metadata.genres = get_string_slice_or_map(game, "genres");

        // Player count
        int players = static_cast<int>(get_number(game, "players"));
        if (players <= 0) players = 1;
        metadata.player_count = std::to_string(players);

        // Rating - TGDB uses "Rating: X.XX/10" format or just a number
        std::string rating = get_string(game, "rating");
        if (!rating.empty()) {
            double rating_value = 0.0;
            if (rating.find('/') != std::string::npos) {
                // Format: "Rating: X.XX/10"
                size_t slash_pos = rating.find('/');
                std::string num_part = rating.substr(0, slash_pos);
                // Remove "Rating: " prefix if present
                size_t colon_pos = num_part.find(':');
                if (colon_pos != std::string::npos) {
                    num_part = num_part.substr(colon_pos + 1);
                }
                // Trim whitespace
                auto start = num_part.find_first_not_of(" \t");
                if (start != std::string::npos) {
                    auto end = num_part.find_last_not_of(" \t");
                    num_part = num_part.substr(start, end - start + 1);
                }
                try {
                    rating_value = std::stod(num_part);
                } catch (...) {}
            } else {
                try {
                    rating_value = std::stod(rating);
                } catch (...) {}
            }
            if (rating_value > 0) {
                // Convert from 0-10 scale to 0-100 scale
                metadata.total_rating = rating_value * 10.0;
            }
        }

        // Publishers and developers
        std::vector<std::string> publishers = get_string_slice_or_map(game, "publishers");
        std::vector<std::string> developers = get_string_slice_or_map(game, "developers");

        if (!developers.empty()) {
            metadata.developer = developers[0];
        }
        if (!publishers.empty()) {
            metadata.publisher = publishers[0];
        }

        // Combine companies, removing duplicates
        std::set<std::string> seen;
        for (const auto& pub : publishers) {
            if (seen.insert(pub).second) {
                metadata.companies.push_back(pub);
            }
        }
        for (const auto& dev : developers) {
            if (seen.insert(dev).second) {
                metadata.companies.push_back(dev);
            }
        }

        metadata.raw_data = game;
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
};

namespace {
[[maybe_unused]] ProviderRegistrar thegamesdb_registrar(
    "thegamesdb",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<TheGamesDBProvider>(config, std::move(cache));
    });
}

}  // namespace retro_metadata
