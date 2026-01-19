#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/errors.hpp>
#include <retro_metadata/internal/matching.hpp>
#include <retro_metadata/internal/normalization.hpp>
#include <retro_metadata/platform/mapping.hpp>
#include <retro_metadata/provider/base.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>

#include <cpr/cpr.h>
#include <nlohmann/json.hpp>

#include <mutex>
#include <regex>

namespace retro_metadata {

namespace {

const std::regex kIgdbTagRegex(R"(\(igdb-(\d+)\))", std::regex::icase);

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

}  // namespace

/// @brief IGDB metadata provider
class IGDBProvider : public Provider {
public:
    IGDBProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache)
        : config_(config), cache_(std::move(cache)) {}

    std::string name() const override { return "igdb"; }

    std::vector<SearchResult> search(const std::string& query, const SearchOptions& opts) override {
        if (!config_.is_configured()) return {};

        std::string token = get_oauth_token();
        if (token.empty()) return {};

        std::string where;
        if (opts.platform_id) {
            where = "platforms=[" + std::to_string(*opts.platform_id) + "]";
        }

        int limit = opts.limit > 0 ? opts.limit : 10;
        auto results = request("games", query, {"id", "name", "slug", "cover.url", "platforms.name", "first_release_date"}, where, limit);

        std::vector<SearchResult> search_results;
        for (const auto& game : results) {
            SearchResult sr;
            sr.provider = name();
            sr.provider_id = static_cast<int>(get_number(game, "id"));
            sr.name = get_string(game, "name");
            sr.slug = get_string(game, "slug");

            if (game.contains("cover") && game["cover"].is_object()) {
                std::string url = get_string(game["cover"], "url");
                sr.cover_url = normalize_cover_url(url, "t_cover_big");
            }

            if (game.contains("platforms") && game["platforms"].is_array()) {
                for (const auto& p : game["platforms"]) {
                    sr.platforms.push_back(get_string(p, "name"));
                }
            }

            double ts = get_number(game, "first_release_date");
            if (ts > 0) {
                time_t timestamp = static_cast<time_t>(ts);
                struct tm* tm_info = gmtime(&timestamp);
                sr.release_year = 1900 + tm_info->tm_year;
            }

            search_results.push_back(std::move(sr));
        }

        return search_results;
    }

    std::unique_ptr<GameResult> get_by_id(int game_id) override {
        if (!config_.is_configured()) return nullptr;

        std::string token = get_oauth_token();
        if (token.empty()) return nullptr;

        auto results = request("games", "", get_game_fields(), "id=" + std::to_string(game_id), 1);
        if (results.empty()) return nullptr;

        return build_game_result(results[0]);
    }

    std::unique_ptr<GameResult> identify(const std::string& filename, const IdentifyOptions& opts) override {
        if (!config_.is_configured()) return nullptr;

        // Check for IGDB ID tag
        std::smatch match;
        if (std::regex_search(filename, match, kIgdbTagRegex) && match.size() > 1) {
            try {
                int id = std::stoi(match[1].str());
                auto result = get_by_id(id);
                if (result) return result;
            } catch (...) {}
        }

        std::string search_term = clean_filename(filename);
        search_term = normalization::normalize_search_term_default(search_term);

        if (!opts.platform_id) return nullptr;

        std::string where = "platforms=[" + std::to_string(*opts.platform_id) + "]";
        auto results = request("games", search_term, get_game_fields(), where, 200);

        if (results.empty()) return nullptr;

        std::map<std::string, nlohmann::json> games_by_name;
        std::vector<std::string> names;
        for (const auto& g : results) {
            std::string game_name = get_string(g, "name");
            if (!game_name.empty()) {
                games_by_name[game_name] = g;
                names.push_back(game_name);
            }
        }

        auto best = matching::find_best_match_simple(search_term, names);
        if (!best.found()) return nullptr;

        auto result = build_game_result(games_by_name[best.match]);
        result->match_score = best.score;
        return result;
    }

    void heartbeat() override {
        std::string token = get_oauth_token();
        if (token.empty()) {
            throw AuthError(name(), "failed to get OAuth token");
        }
    }

    void close() override {}

private:
    std::vector<std::string> get_game_fields() {
        return {
            "id", "name", "slug", "summary", "total_rating", "aggregated_rating",
            "first_release_date", "cover.url", "screenshots.url", "platforms.id",
            "platforms.name", "alternative_names.name", "genres.name", "franchise.name",
            "franchises.name", "collections.name", "game_modes.name",
            "involved_companies.company.name", "videos.video_id"
        };
    }

    std::string get_oauth_token() {
        std::lock_guard lock(token_mutex_);
        if (!oauth_token_.empty()) return oauth_token_;

        std::string client_id = config_.get_credential("client_id");
        std::string client_secret = config_.get_credential("client_secret");

        cpr::Response r = cpr::Post(
            cpr::Url{"https://id.twitch.tv/oauth2/token"},
            cpr::Parameters{
                {"client_id", client_id},
                {"client_secret", client_secret},
                {"grant_type", "client_credentials"}
            }
        );

        if (r.status_code == 400) {
            throw AuthError(name());
        }

        if (r.status_code != 200) {
            throw ConnectionError(name(), "OAuth request failed");
        }

        try {
            auto json = nlohmann::json::parse(r.text);
            oauth_token_ = get_string(json, "access_token");
        } catch (...) {
            throw ConnectionError(name(), "Failed to parse OAuth response");
        }

        return oauth_token_;
    }

    nlohmann::json request(const std::string& endpoint, const std::string& search_term,
                           const std::vector<std::string>& fields, const std::string& where, int limit) {
        std::string token = get_oauth_token();
        std::string client_id = config_.get_credential("client_id");

        std::string query;
        if (!search_term.empty()) {
            query += "search \"" + search_term + "\"; ";
        }
        if (!fields.empty()) {
            query += "fields ";
            for (size_t i = 0; i < fields.size(); ++i) {
                if (i > 0) query += ",";
                query += fields[i];
            }
            query += "; ";
        }
        if (!where.empty()) {
            query += "where " + where + "; ";
        }
        if (limit > 0) {
            query += "limit " + std::to_string(limit) + ";";
        }

        cpr::Response r = cpr::Post(
            cpr::Url{"https://api.igdb.com/v4/" + endpoint},
            cpr::Header{
                {"Accept", "application/json"},
                {"Authorization", "Bearer " + token},
                {"Client-ID", client_id}
            },
            cpr::Body{query}
        );

        if (r.status_code == 401) {
            std::lock_guard lock(token_mutex_);
            oauth_token_.clear();
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

    std::string normalize_cover_url(const std::string& url, const std::string& size) {
        if (url.empty()) return "";
        std::string result = normalization::normalize_cover_url(url);
        size_t pos = result.find("t_thumb");
        if (pos != std::string::npos) {
            result.replace(pos, 7, size);
        }
        return result;
    }

    std::unique_ptr<GameResult> build_game_result(const nlohmann::json& game) {
        auto result = std::make_unique<GameResult>();
        int game_id = static_cast<int>(get_number(game, "id"));

        result->provider = name();
        result->provider_id = game_id;
        result->provider_ids = {{"igdb", game_id}};
        result->name = get_string(game, "name");
        result->slug = get_string(game, "slug");
        result->summary = get_string(game, "summary");

        if (game.contains("cover") && game["cover"].is_object()) {
            result->artwork.cover_url = normalize_cover_url(get_string(game["cover"], "url"), "t_1080p");
        }

        if (game.contains("screenshots") && game["screenshots"].is_array()) {
            for (const auto& ss : game["screenshots"]) {
                result->artwork.screenshot_urls.push_back(
                    normalize_cover_url(get_string(ss, "url"), "t_720p"));
            }
        }

        // Metadata
        double rating = get_number(game, "total_rating");
        if (rating > 0) result->metadata.total_rating = rating;

        double agg_rating = get_number(game, "aggregated_rating");
        if (agg_rating > 0) result->metadata.aggregated_rating = agg_rating;

        double ts = get_number(game, "first_release_date");
        if (ts > 0) result->metadata.first_release_date = static_cast<int64_t>(ts);

        if (game.contains("genres") && game["genres"].is_array()) {
            for (const auto& g : game["genres"]) {
                result->metadata.genres.push_back(get_string(g, "name"));
            }
        }

        if (game.contains("game_modes") && game["game_modes"].is_array()) {
            for (const auto& m : game["game_modes"]) {
                result->metadata.game_modes.push_back(get_string(m, "name"));
            }
        }

        if (game.contains("videos") && game["videos"].is_array() && !game["videos"].empty()) {
            result->metadata.youtube_video_id = get_string(game["videos"][0], "video_id");
        }

        result->raw_response = game;
        return result;
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
    std::string oauth_token_;
    std::mutex token_mutex_;
};

namespace {
[[maybe_unused]] ProviderRegistrar igdb_registrar(
    "igdb",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<IGDBProvider>(config, std::move(cache));
    });
}

}  // namespace retro_metadata
