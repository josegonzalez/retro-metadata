#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/errors.hpp>
#include <retro_metadata/internal/matching.hpp>
#include <retro_metadata/provider/base.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>

#include <cpr/cpr.h>
#include <nlohmann/json.hpp>

#include <regex>

namespace retro_metadata {

namespace {

const std::string kHltbImageUrl = "https://howlongtobeat.com/games/";
const std::string kGithubHltbApiUrl =
    "https://raw.githubusercontent.com/rommapp/romm/refs/heads/master/backend/handler/metadata/"
    "fixtures/hltb_api_url";
const std::string kDefaultSearchEndpoint = "search";

const std::regex kHltbTagRegex(R"(\(hltb-(\d+)\))", std::regex::icase);

// Helper to safely get string from JSON
std::string get_string(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key) && j[key].is_string()) {
        return j[key].get<std::string>();
    }
    return "";
}

// Helper to safely get number from JSON
double get_number(const nlohmann::json& j, const std::string& key) {
    if (j.contains(key) && j[key].is_number()) {
        return j[key].get<double>();
    }
    return 0.0;
}

// Clean filename for search
std::string clean_filename(const std::string& filename) {
    static const std::regex ext_pattern(R"(\.[^.]+$)");
    static const std::regex tag_pattern(R"(\s*[\(\[][^\)\]]*[\)\]])");

    std::string name = std::regex_replace(filename, ext_pattern, "");
    name = std::regex_replace(name, tag_pattern, "");

    // Trim
    auto start = name.find_first_not_of(" \t\n\r");
    if (start == std::string::npos) return "";
    auto end = name.find_last_not_of(" \t\n\r");
    return name.substr(start, end - start + 1);
}

}  // namespace

/// @brief HowLongToBeat metadata provider
class HLTBProvider : public Provider {
public:
    HLTBProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache)
        : config_(config), cache_(std::move(cache)) {}

    std::string name() const override { return "hltb"; }

    std::vector<SearchResult> search(const std::string& query, const SearchOptions& opts) override {
        if (!config_.enabled) {
            return {};
        }

        int limit = opts.limit > 0 ? opts.limit : 20;
        auto result = request("search", build_search_data(query, limit));

        if (!result.contains("data") || !result["data"].is_array()) {
            return {};
        }

        std::vector<SearchResult> results;
        for (const auto& item : result["data"]) {
            if (!item.is_object()) continue;

            int game_id = static_cast<int>(get_number(item, "game_id"));
            if (game_id == 0) continue;

            SearchResult sr;
            sr.name = get_string(item, "game_name");
            sr.provider = name();
            sr.provider_id = game_id;

            std::string img = get_string(item, "game_image");
            if (!img.empty()) {
                sr.cover_url = kHltbImageUrl + img;
            }

            int year = static_cast<int>(get_number(item, "release_world"));
            if (year > 0) {
                sr.release_year = year;
            }

            std::string platform = get_string(item, "profile_platform");
            if (!platform.empty()) {
                // Split by comma
                size_t pos = 0;
                while (pos < platform.size()) {
                    size_t comma = platform.find(", ", pos);
                    if (comma == std::string::npos) {
                        sr.platforms.push_back(platform.substr(pos));
                        break;
                    }
                    sr.platforms.push_back(platform.substr(pos, comma - pos));
                    pos = comma + 2;
                }
            }

            results.push_back(std::move(sr));
        }

        return results;
    }

    std::unique_ptr<GameResult> get_by_id(int game_id) override {
        if (!config_.enabled) {
            return nullptr;
        }

        auto search_data = build_search_data("", 1);
        search_data["gameId"] = game_id;

        auto result = request("search", search_data);

        if (!result.contains("data") || !result["data"].is_array() ||
            result["data"].empty()) {
            return nullptr;
        }

        return build_game_result(result["data"][0]);
    }

    std::unique_ptr<GameResult> identify(
        const std::string& filename, const IdentifyOptions& opts) override {
        if (!config_.enabled) {
            return nullptr;
        }

        // Check for HLTB ID tag in filename
        std::smatch match;
        if (std::regex_search(filename, match, kHltbTagRegex) && match.size() > 1) {
            try {
                int tagged_id = std::stoi(match[1].str());
                auto result = get_by_id(tagged_id);
                if (result) {
                    return result;
                }
            } catch (...) {
                // Ignore parse errors
            }
        }

        // Clean the filename and search
        std::string search_term = clean_filename(filename);
        auto result = request("search", build_search_data(search_term, 20));

        if (!result.contains("data") || !result["data"].is_array() ||
            result["data"].empty()) {
            return nullptr;
        }

        // Build name to game map
        std::map<std::string, nlohmann::json> games_by_name;
        std::vector<std::string> names;
        for (const auto& item : result["data"]) {
            std::string game_name = get_string(item, "game_name");
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

        auto game_result = build_game_result(games_by_name[best.match]);
        game_result->match_score = best.score;
        return game_result;
    }

    void heartbeat() override {
        if (!config_.enabled) {
            throw ConnectionError(name(), "provider is disabled");
        }

        // Try to fetch the security token to check connectivity
        std::string token = fetch_security_token();
        if (token.empty()) {
            throw ConnectionError(name(), "failed to get security token");
        }
    }

    void close() override {
        // No resources to clean up
    }

private:
    nlohmann::json build_search_data(const std::string& query, int limit) {
        nlohmann::json search_terms = nlohmann::json::array();
        if (!query.empty()) {
            // Split by space
            std::istringstream iss(query);
            std::string word;
            while (iss >> word) {
                search_terms.push_back(word);
            }
        }

        return {
            {"searchType", "games"},
            {"searchTerms", search_terms},
            {"searchPage", 1},
            {"size", limit},
            {"searchOptions",
             {{"games",
               {{"userId", 0},
                {"platform", ""},
                {"sortCategory", "popular"},
                {"rangeCategory", "main"},
                {"rangeTime", {{"min", 0}, {"max", 0}}},
                {"gameplay", {{"perspective", ""}, {"flow", ""}, {"genre", ""}}},
                {"modifier", ""}}},
              {"users", {{"sortCategory", "postcount"}}},
              {"filter", ""},
              {"sort", 0},
              {"randomizer", 0}}}};
    }

    std::string fetch_search_endpoint() {
        if (!search_endpoint_.empty()) {
            return search_endpoint_;
        }

        cpr::Response r = cpr::Get(cpr::Url{kGithubHltbApiUrl});
        if (r.status_code == 200 && !r.text.empty()) {
            // Trim
            search_endpoint_ = r.text;
            auto start = search_endpoint_.find_first_not_of(" \t\n\r");
            auto end = search_endpoint_.find_last_not_of(" \t\n\r");
            if (start != std::string::npos) {
                search_endpoint_ = search_endpoint_.substr(start, end - start + 1);
            }
        }

        if (search_endpoint_.empty()) {
            search_endpoint_ = kDefaultSearchEndpoint;
        }

        return search_endpoint_;
    }

    std::string fetch_security_token() {
        if (!security_token_.empty()) {
            return security_token_;
        }

        cpr::Response r = cpr::Get(
            cpr::Url{base_url_ + "/search/init"},
            cpr::Header{{"User-Agent", user_agent_}});

        if (r.status_code == 200) {
            try {
                auto json = nlohmann::json::parse(r.text);
                if (json.contains("token") && json["token"].is_string()) {
                    security_token_ = json["token"].get<std::string>();
                }
            } catch (...) {
                // Ignore parse errors
            }
        }

        return security_token_;
    }

    nlohmann::json request(const std::string& endpoint, const nlohmann::json& data) {
        std::string actual_endpoint = endpoint;
        if (endpoint == "search") {
            actual_endpoint = fetch_search_endpoint();
        }

        std::string url = base_url_ + "/" + actual_endpoint;
        std::string body = data.dump();

        cpr::Header headers = {
            {"User-Agent", user_agent_},
            {"Content-Type", "application/json"},
            {"Origin", "https://howlongtobeat.com"},
            {"Referer", "https://howlongtobeat.com"}};

        std::string token = fetch_security_token();
        if (!token.empty()) {
            headers["X-Auth-Token"] = token;
        }

        cpr::Response r = cpr::Post(cpr::Url{url}, headers, cpr::Body{body});

        if (r.status_code != 200) {
            throw ConnectionError(name(), "HTTP " + std::to_string(r.status_code));
        }

        try {
            return nlohmann::json::parse(r.text);
        } catch (const std::exception& e) {
            throw ConnectionError(name(), std::string("JSON parse error: ") + e.what());
        }
    }

    std::unique_ptr<GameResult> build_game_result(const nlohmann::json& game) {
        auto result = std::make_unique<GameResult>();

        int game_id = static_cast<int>(get_number(game, "game_id"));
        result->name = get_string(game, "game_name");
        result->provider = name();
        result->provider_id = game_id;
        result->provider_ids = {{"hltb", game_id}};

        std::string img = get_string(game, "game_image");
        if (!img.empty()) {
            result->artwork.cover_url = kHltbImageUrl + img;
        }

        // Metadata
        int year = static_cast<int>(get_number(game, "release_world"));
        if (year > 0) {
            result->metadata.release_year = year;
        }

        double score = get_number(game, "review_score");
        if (score > 0) {
            result->metadata.total_rating = score;
        }

        if (get_number(game, "comp_main") > 0) {
            result->metadata.game_modes.push_back("Single Player");
        }
        if (get_number(game, "comp_plus") > 0) {
            result->metadata.game_modes.push_back("Completionist");
        }

        result->metadata.developer = get_string(game, "profile_dev");

        // Raw data
        result->metadata.raw_data = {
            {"main_story", get_number(game, "comp_main")},
            {"main_plus_extras", get_number(game, "comp_plus")},
            {"completionist", get_number(game, "comp_100")},
            {"all_styles", get_number(game, "comp_all")},
            {"profile_popular", get_number(game, "profile_popular")},
            {"count_comp", get_number(game, "count_comp")},
            {"count_playing", get_number(game, "count_playing")},
            {"count_backlog", get_number(game, "count_backlog")},
            {"count_replay", get_number(game, "count_replay")},
            {"count_retired", get_number(game, "count_retired")},
            {"review_score", get_number(game, "review_score")}};

        result->raw_response = game;

        return result;
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
    std::string base_url_ = "https://howlongtobeat.com/api";
    std::string user_agent_ = "retro-metadata/1.0";
    std::string search_endpoint_;
    std::string security_token_;
};

// Auto-register the provider
namespace {
[[maybe_unused]] ProviderRegistrar hltb_registrar(
    "hltb",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<HLTBProvider>(config, std::move(cache));
    });
}  // namespace

}  // namespace retro_metadata
