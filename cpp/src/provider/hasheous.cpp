/// @file hasheous.cpp
/// @brief Hasheous provider implementation - hash-based ROM identification service

#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/errors.hpp>
#include <retro_metadata/internal/matching.hpp>
#include <retro_metadata/internal/normalization.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>

#include <cpr/cpr.h>
#include <nlohmann/json.hpp>

#include <map>
#include <regex>
#include <string>

namespace retro_metadata {

namespace {

/// Regex to match Hasheous ID tags in filenames like (hasheous-xxxxx)
const std::regex kHasheousTagRegex(R"(\(hasheous-([a-f0-9-]+)\))", std::regex::icase);

/// API keys for client authentication
const std::string kHasheousAPIKeyProduction =
    "JNoFBA-jEh4HbxuxEHM6MVzydKoAXs9eCcp2dvcg5LRCnpp312voiWmjuaIssSzS";
const std::string kHasheousAPIKeyDev =
    "UUvh9ef_CddMM4xXO1iqxl9FqEt764v33LU-UiGFc0P34odXjMP9M6MTeE4JZRxZ";

/// API URLs
const std::string kHasheousProductionURL = "https://hasheous.org/api/v1";
const std::string kHasheousBetaURL = "https://beta.hasheous.org/api/v1";

/// Helper function to get string from JSON
std::string get_string(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key) && j[key].is_string()) {
        return j[key].get<std::string>();
    }
    if (j.contains(key) && j[key].is_number()) {
        return std::to_string(j[key].get<double>());
    }
    return "";
}

/// Helper function to get int from JSON
int get_int(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key)) {
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
    }
    return 0;
}

/// Helper function to get double from JSON
double get_double(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key) && j[key].is_number()) {
        return j[key].get<double>();
    }
    return 0.0;
}

/// Helper function to get first non-empty string
std::string coalesce(const std::string& a, const std::string& b) {
    return !a.empty() ? a : b;
}

/// Clean filename by removing extension and tags
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

/// Normalize IGDB cover URL - add https prefix and change size
std::string normalize_igdb_cover_url(const std::string& url, const std::string& size) {
    if (url.empty()) return "";
    std::string result = url;
    // Add https: prefix if needed
    if (result.substr(0, 2) == "//") {
        result = "https:" + result;
    }
    // Replace t_thumb with requested size
    size_t pos = result.find("t_thumb");
    if (pos != std::string::npos) {
        result.replace(pos, 7, size);
    }
    return result;
}

}  // namespace

/// @brief Hasheous metadata provider - hash-based ROM identification service
class HasheousProvider : public HashProvider {
public:
    HasheousProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache, bool dev_mode = false)
        : config_(config), cache_(std::move(cache)), dev_mode_(dev_mode) {
        if (dev_mode_) {
            base_url_ = kHasheousBetaURL;
            api_key_ = kHasheousAPIKeyDev;
        } else {
            base_url_ = kHasheousProductionURL;
            api_key_ = kHasheousAPIKeyProduction;
        }
    }

    std::string name() const override { return "hasheous"; }

    /// @brief Search for games by name
    /// Note: Hasheous primarily works with hashes, not name searches.
    std::vector<SearchResult> search(const std::string& query, const SearchOptions& opts) override {
        if (!config_.enabled) return {};

        std::map<std::string, std::string> params;
        params["q"] = query;
        if (opts.platform_id) {
            params["platform"] = std::to_string(*opts.platform_id);
        }

        auto result = request("GET", "/search", params, {});
        if (result.is_null() || !result.is_array()) {
            return {};
        }

        int limit = opts.limit > 0 ? opts.limit : 20;
        std::vector<SearchResult> search_results;

        for (size_t i = 0; i < result.size() && static_cast<int>(i) < limit; ++i) {
            const auto& game = result[i];
            if (!game.is_object()) continue;

            std::string game_id = get_string(game, "id");
            if (game_id.empty()) continue;

            SearchResult sr;
            sr.provider = name();
            sr.provider_id = get_int(game, "id");
            sr.name = get_string(game, "name");
            sr.cover_url = get_string(game, "cover_url");

            if (game.contains("platforms") && game["platforms"].is_array()) {
                for (const auto& pl : game["platforms"]) {
                    if (pl.is_string()) {
                        sr.platforms.push_back(pl.get<std::string>());
                    }
                }
            }

            search_results.push_back(std::move(sr));
        }

        return search_results;
    }

    /// @brief Get game details by Hasheous ID
    std::unique_ptr<GameResult> get_by_id(int game_id) override {
        if (!config_.enabled) return nullptr;

        auto result = request("GET", "/games/" + std::to_string(game_id), {}, {});
        if (result.is_null() || !result.is_object()) {
            return nullptr;
        }

        return build_game_result(result);
    }

    /// @brief Identify a game from a ROM filename
    /// Note: Hasheous works best with hash lookups rather than filename matching.
    std::unique_ptr<GameResult> identify(
        const std::string& filename, const IdentifyOptions& opts) override {
        if (!config_.enabled) return nullptr;

        // Check for Hasheous ID tag in filename
        std::smatch match;
        if (std::regex_search(filename, match, kHasheousTagRegex) && match.size() > 1) {
            try {
                int id = std::stoi(match[1].str());
                auto result = get_by_id(id);
                if (result) return result;
            } catch (...) {}
        }

        // Hasheous primarily works with hashes, so try a search
        std::string search_term = clean_filename(filename);
        search_term = normalization::normalize_search_term_default(search_term);

        SearchOptions search_opts;
        search_opts.platform_id = opts.platform_id;
        search_opts.limit = 10;

        auto results = search(search_term, search_opts);
        if (results.empty()) return nullptr;

        // Find best match
        std::map<std::string, SearchResult> games_by_name;
        std::vector<std::string> names;
        for (const auto& r : results) {
            games_by_name[r.name] = r;
            names.push_back(r.name);
        }

        matching::FindBestMatchOptions match_opts;
        match_opts.min_similarity_score = 0.6;
        auto best = matching::find_best_match(search_term, names, match_opts);
        if (!best.found()) return nullptr;

        auto it = games_by_name.find(best.match);
        if (it == games_by_name.end()) return nullptr;

        auto full_result = get_by_id(it->second.provider_id);
        if (full_result) {
            full_result->match_score = best.score;
        }
        return full_result;
    }

    /// @brief Identify a game using file hashes
    std::unique_ptr<GameResult> identify_by_hash(
        const FileHashes& hashes, const IdentifyOptions& /*opts*/) override {
        auto result = lookup_by_hash(hashes.md5, hashes.sha1, hashes.crc32, true);
        if (result.is_null()) return nullptr;

        // Try to get IGDB game data
        auto igdb_game = get_igdb_game(result);
        if (!igdb_game.is_null() && igdb_game.is_object()) {
            return build_game_result_from_igdb(igdb_game);
        }

        // Fall back to basic result
        return build_game_result_from_hash_lookup(result);
    }

    /// @brief Core hash lookup method - POST /Lookup/ByHash
    nlohmann::json lookup_by_hash(
        const std::string& md5, const std::string& sha1, const std::string& crc,
        bool return_all_sources = false) {
        if (!config_.enabled) return nullptr;

        if (md5.empty() && sha1.empty() && crc.empty()) {
            return nullptr;
        }

        // Build request data with Hasheous's expected field names (note casing)
        nlohmann::json hashes;
        if (!md5.empty()) {
            hashes["mD5"] = md5;
        }
        if (!sha1.empty()) {
            hashes["shA1"] = sha1;
        }
        if (!crc.empty()) {
            hashes["crc"] = crc;
        }

        std::map<std::string, std::string> params;
        params["returnAllSources"] = return_all_sources ? "true" : "false";
        params["returnFields"] = "Signatures, Metadata, Attributes";

        return request("POST", "/Lookup/ByHash", params, hashes);
    }

    /// @brief Get IGDB game data through Hasheous proxy
    nlohmann::json get_igdb_game(const nlohmann::json& hasheous_result) {
        if (!config_.enabled) return nullptr;

        int igdb_id = 0;

        // Look in metadata list
        if (hasheous_result.contains("metadata") && hasheous_result["metadata"].is_array()) {
            for (const auto& meta : hasheous_result["metadata"]) {
                if (meta.is_object() && get_string(meta, "source") == "IGDB") {
                    igdb_id = get_int(meta, "immutableId");
                    break;
                }
            }
        }

        // Also check direct igdb_id fields
        if (igdb_id == 0) {
            igdb_id = get_int(hasheous_result, "igdb_id");
        }
        if (igdb_id == 0) {
            igdb_id = get_int(hasheous_result, "igdbId");
        }

        if (igdb_id == 0) return nullptr;

        // Fetch IGDB data through Hasheous proxy
        std::map<std::string, std::string> params;
        params["Id"] = std::to_string(igdb_id);
        params["expandColumns"] = "age_ratings, alternative_names, collections, cover, dlcs, "
                                  "expanded_games, franchise, franchises, game_modes, genres, "
                                  "involved_companies, platforms, ports, remakes, screenshots, "
                                  "similar_games, videos";

        return request("GET", "/MetadataProxy/IGDB/Game", params, {});
    }

    /// @brief Get RetroAchievements game data through Hasheous proxy
    nlohmann::json get_ra_game(const nlohmann::json& hasheous_result) {
        if (!config_.enabled) return nullptr;

        int ra_id = 0;

        // Look in metadata list
        if (hasheous_result.contains("metadata") && hasheous_result["metadata"].is_array()) {
            for (const auto& meta : hasheous_result["metadata"]) {
                if (meta.is_object() && get_string(meta, "source") == "RetroAchievements") {
                    ra_id = get_int(meta, "immutableId");
                    break;
                }
            }
        }

        // Also check direct ra_id fields
        if (ra_id == 0) {
            ra_id = get_int(hasheous_result, "ra_id");
        }
        if (ra_id == 0) {
            ra_id = get_int(hasheous_result, "retroAchievementsId");
        }

        if (ra_id == 0) return nullptr;

        // Fetch RA data through Hasheous proxy
        std::map<std::string, std::string> params;
        params["Id"] = std::to_string(ra_id);

        return request("GET", "/MetadataProxy/RA/Game", params, {});
    }

    /// @brief Extract signature matching flags from Hasheous lookup result
    std::map<std::string, bool> get_signature_matches(const nlohmann::json& hasheous_result) {
        std::map<std::string, bool> matches = {
            {"tosec_match", false},
            {"nointro_match", false},
            {"redump_match", false},
            {"mame_arcade_match", false},
            {"mame_mess_match", false},
            {"whdload_match", false},
            {"ra_match", false},
            {"fbneo_match", false},
            {"puredos_match", false}
        };

        if (!hasheous_result.contains("signatures") ||
            !hasheous_result["signatures"].is_object()) {
            return matches;
        }

        const auto& signatures = hasheous_result["signatures"];
        matches["tosec_match"] = signatures.contains("TOSEC");
        matches["nointro_match"] = signatures.contains("NoIntros");
        matches["redump_match"] = signatures.contains("Redump");
        matches["mame_arcade_match"] = signatures.contains("MAMEArcade");
        matches["mame_mess_match"] = signatures.contains("MAMEMess");
        matches["whdload_match"] = signatures.contains("WHDLoad");
        matches["ra_match"] = signatures.contains("RetroAchievements");
        matches["fbneo_match"] = signatures.contains("FBNeo");
        matches["puredos_match"] = signatures.contains("PureDOS");

        return matches;
    }

    void heartbeat() override {
        std::map<std::string, std::string> params;
        params["q"] = "test";
        request("GET", "/search", params, {});
    }

    void close() override {}

private:
    /// @brief Make an HTTP request to the Hasheous API
    nlohmann::json request(
        const std::string& method,
        const std::string& endpoint,
        const std::map<std::string, std::string>& params,
        const nlohmann::json& body) {
        std::string url = base_url_ + endpoint;

        cpr::Parameters cpr_params;
        for (const auto& [key, value] : params) {
            cpr_params.Add({key, value});
        }

        cpr::Header headers{
            {"Accept", "application/json"},
            {"Content-Type", "application/json-patch+json"},
            {"User-Agent", "retro-metadata/1.0"},
            {"X-Client-API-Key", api_key_}
        };

        cpr::Response r;
        if (method == "POST") {
            r = cpr::Post(
                cpr::Url{url},
                cpr_params,
                headers,
                cpr::Body{body.dump()}
            );
        } else {
            r = cpr::Get(
                cpr::Url{url},
                cpr_params,
                headers
            );
        }

        if (r.status_code == 429) {
            throw RateLimitError(name());
        }

        if (r.status_code == 404) {
            return nullptr;
        }

        if (r.status_code != 200) {
            throw ConnectionError(name(), "HTTP " + std::to_string(r.status_code));
        }

        try {
            return nlohmann::json::parse(r.text);
        } catch (...) {
            throw ConnectionError(name(), "Failed to parse JSON response");
        }
    }

    /// @brief Build a GameResult from Hasheous game data
    std::unique_ptr<GameResult> build_game_result(const nlohmann::json& game) {
        auto result = std::make_unique<GameResult>();
        int provider_id = get_int(game, "id");

        result->provider = name();
        result->provider_id = provider_id;
        result->provider_ids = {{"hasheous", provider_id}};
        result->name = coalesce(get_string(game, "name"), get_string(game, "title"));
        result->summary = coalesce(get_string(game, "description"), get_string(game, "overview"));
        result->artwork.cover_url = coalesce(
            get_string(game, "cover_url"), get_string(game, "boxart"));

        if (game.contains("screenshots") && game["screenshots"].is_array()) {
            for (const auto& s : game["screenshots"]) {
                if (s.is_string()) {
                    result->artwork.screenshot_urls.push_back(s.get<std::string>());
                }
            }
        }

        result->metadata = extract_metadata(game);
        result->raw_response = game;
        return result;
    }

    /// @brief Build a GameResult from hash lookup result
    std::unique_ptr<GameResult> build_game_result_from_hash_lookup(const nlohmann::json& result) {
        auto game_result = std::make_unique<GameResult>();
        game_result->provider = name();
        game_result->raw_response = result;

        // Extract basic info from signatures if available
        if (result.contains("signatures") && result["signatures"].is_object()) {
            for (const auto& [source, data] : result["signatures"].items()) {
                if (data.is_object()) {
                    if (game_result->name.empty()) {
                        game_result->name = get_string(data, "name");
                    }
                    if (game_result->summary.empty()) {
                        game_result->summary = get_string(data, "description");
                    }
                    // Mark signature source in provider IDs
                    game_result->provider_ids[source] = 1;
                }
            }
        }

        return game_result;
    }

    /// @brief Build a GameResult from IGDB data fetched through Hasheous proxy
    std::unique_ptr<GameResult> build_game_result_from_igdb(const nlohmann::json& game) {
        auto result = std::make_unique<GameResult>();
        int provider_id = get_int(game, "id");

        result->provider = "igdb";
        result->provider_id = provider_id;
        result->provider_ids = {{"igdb", provider_id}};
        result->name = get_string(game, "name");
        result->summary = get_string(game, "summary");
        result->slug = get_string(game, "slug");

        // Extract cover with URL normalization
        if (game.contains("cover") && game["cover"].is_object()) {
            std::string url = get_string(game["cover"], "url");
            result->artwork.cover_url = normalize_igdb_cover_url(url, "t_1080p");
        }

        // Extract screenshots with URL normalization
        if (game.contains("screenshots") && game["screenshots"].is_array()) {
            for (const auto& s : game["screenshots"]) {
                if (s.is_object()) {
                    std::string url = get_string(s, "url");
                    if (!url.empty()) {
                        result->artwork.screenshot_urls.push_back(
                            normalize_igdb_cover_url(url, "t_720p"));
                    }
                }
            }
        }

        result->metadata = extract_igdb_metadata(game);
        result->raw_response = game;
        return result;
    }

    /// @brief Extract metadata from Hasheous game data
    GameMetadata extract_metadata(const nlohmann::json& game) {
        GameMetadata metadata;
        metadata.raw_data = game;

        // Genres
        if (game.contains("genres") && game["genres"].is_array()) {
            for (const auto& g : game["genres"]) {
                if (g.is_string()) {
                    metadata.genres.push_back(g.get<std::string>());
                }
            }
        } else {
            std::string genre_str = get_string(game, "genres");
            if (!genre_str.empty()) {
                // Split by comma
                size_t pos = 0;
                while ((pos = genre_str.find(',')) != std::string::npos) {
                    std::string g = genre_str.substr(0, pos);
                    // Trim
                    auto start = g.find_first_not_of(" \t");
                    auto end = g.find_last_not_of(" \t");
                    if (start != std::string::npos) {
                        metadata.genres.push_back(g.substr(start, end - start + 1));
                    }
                    genre_str.erase(0, pos + 1);
                }
                auto start = genre_str.find_first_not_of(" \t");
                auto end = genre_str.find_last_not_of(" \t");
                if (start != std::string::npos) {
                    metadata.genres.push_back(genre_str.substr(start, end - start + 1));
                }
            }
        }

        // Companies
        std::string publisher = get_string(game, "publisher");
        if (!publisher.empty()) {
            metadata.companies.push_back(publisher);
            metadata.publisher = publisher;
        }
        std::string developer = get_string(game, "developer");
        if (!developer.empty()) {
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

        // Player count
        int players = get_int(game, "players");
        if (players > 0) {
            metadata.player_count = std::to_string(players);
        }

        // Release year
        std::string release_date = get_string(game, "release_date");
        if (release_date.empty()) {
            release_date = get_string(game, "year");
        }
        if (!release_date.empty() && release_date.length() >= 4) {
            try {
                int year = std::stoi(release_date.substr(0, 4));
                metadata.release_year = year;
            } catch (...) {}
        }

        return metadata;
    }

    /// @brief Extract metadata from IGDB game data
    GameMetadata extract_igdb_metadata(const nlohmann::json& game) {
        GameMetadata metadata;
        metadata.raw_data = game;

        // Genres
        if (game.contains("genres") && game["genres"].is_array()) {
            for (const auto& g : game["genres"]) {
                if (g.is_object()) {
                    std::string name = get_string(g, "name");
                    if (!name.empty()) {
                        metadata.genres.push_back(name);
                    }
                }
            }
        }

        // Franchises
        if (game.contains("franchise") && game["franchise"].is_object()) {
            std::string name = get_string(game["franchise"], "name");
            if (!name.empty()) {
                metadata.franchises.push_back(name);
            }
        }
        if (game.contains("franchises") && game["franchises"].is_array()) {
            for (const auto& f : game["franchises"]) {
                if (f.is_object()) {
                    std::string name = get_string(f, "name");
                    if (!name.empty()) {
                        metadata.franchises.push_back(name);
                    }
                }
            }
        }

        // Collections
        if (game.contains("collections") && game["collections"].is_array()) {
            for (const auto& c : game["collections"]) {
                if (c.is_object()) {
                    std::string name = get_string(c, "name");
                    if (!name.empty()) {
                        metadata.collections.push_back(name);
                    }
                }
            }
        }

        // Companies
        if (game.contains("involved_companies") && game["involved_companies"].is_array()) {
            for (const auto& ic : game["involved_companies"]) {
                if (ic.is_object() && ic.contains("company") && ic["company"].is_object()) {
                    std::string name = get_string(ic["company"], "name");
                    if (!name.empty()) {
                        metadata.companies.push_back(name);
                    }
                }
            }
        }

        // Rating
        double rating = get_double(game, "total_rating");
        if (rating > 0) {
            metadata.total_rating = rating;
        }

        // First release date
        double timestamp = get_double(game, "first_release_date");
        if (timestamp > 0) {
            metadata.first_release_date = static_cast<int64_t>(timestamp);
        }

        return metadata;
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
    std::string base_url_;
    std::string api_key_;
    bool dev_mode_;
};

namespace {
[[maybe_unused]] ProviderRegistrar hasheous_registrar(
    "hasheous",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<HasheousProvider>(config, std::move(cache));
    });
}

}  // namespace retro_metadata
