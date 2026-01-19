/// @file screenscraper.cpp
/// @brief ScreenScraper metadata provider implementation

#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/errors.hpp>
#include <retro_metadata/internal/matching.hpp>
#include <retro_metadata/internal/normalization.hpp>
#include <retro_metadata/provider/base.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>

#include <cpr/cpr.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <ctime>
#include <iomanip>
#include <map>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

namespace retro_metadata {

namespace {

/// ScreenScraper ID tag regex: matches (ssfr-12345) in filenames
const std::regex kScreenScraperTagRegex(R"(\(ssfr-(\d+)\))", std::regex::icase);

/// Default developer credentials (from romm project, base64 decoded)
const std::string kDefaultDevId = "zurdi15";
const std::string kDefaultDevPassword = "xTJwoOFjOQG";

/// Default region priority for media selection
const std::vector<std::string> kDefaultRegions = {"us", "wor", "ss", "eu", "jp", "unk"};

/// Default language priority for descriptions
const std::vector<std::string> kDefaultLanguages = {"en", "fr"};

/// Sensitive keys to strip from URLs
const std::map<std::string, bool> kSensitiveKeys = {
    {"ssid", true},
    {"sspassword", true},
    {"devid", true},
    {"devpassword", true}
};

/// Get string value from JSON, handling different types
std::string get_string(const nlohmann::json& j, const std::string& key) {
    if (!j.contains(key) || j[key].is_null()) {
        return "";
    }
    if (j[key].is_string()) {
        return j[key].get<std::string>();
    }
    if (j[key].is_number()) {
        return std::to_string(j[key].get<int>());
    }
    return "";
}

/// Get integer value from JSON
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

/// Get double value from JSON
double get_double(const nlohmann::json& j, const std::string& key) {
    if (!j.contains(key) || j[key].is_null()) {
        return 0.0;
    }
    if (j[key].is_number()) {
        return j[key].get<double>();
    }
    if (j[key].is_string()) {
        try {
            return std::stod(j[key].get<std::string>());
        } catch (...) {
            return 0.0;
        }
    }
    return 0.0;
}

/// Strip sensitive query parameters from a URL
std::string strip_sensitive_params(const std::string& url) {
    auto pos = url.find('?');
    if (pos == std::string::npos) {
        return url;
    }

    std::string base = url.substr(0, pos);
    std::string query = url.substr(pos + 1);

    std::vector<std::string> new_params;
    std::istringstream iss(query);
    std::string param;
    while (std::getline(iss, param, '&')) {
        auto eq_pos = param.find('=');
        if (eq_pos != std::string::npos) {
            std::string key = param.substr(0, eq_pos);
            // Convert key to lowercase for comparison
            std::string key_lower = key;
            std::transform(key_lower.begin(), key_lower.end(), key_lower.begin(), ::tolower);
            if (kSensitiveKeys.find(key_lower) == kSensitiveKeys.end()) {
                new_params.push_back(param);
            }
        } else {
            new_params.push_back(param);
        }
    }

    if (new_params.empty()) {
        return base;
    }

    std::ostringstream oss;
    oss << base << "?";
    for (size_t i = 0; i < new_params.size(); ++i) {
        if (i > 0) oss << "&";
        oss << new_params[i];
    }
    return oss.str();
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

/// URL encode a string
std::string url_encode(const std::string& str) {
    std::ostringstream encoded;
    encoded.fill('0');
    encoded << std::hex;

    for (char c : str) {
        // Keep alphanumeric and safe characters unchanged
        if (isalnum(static_cast<unsigned char>(c)) || c == '-' || c == '_' || c == '.' || c == '~' || c == ' ' || c == '/') {
            if (c == ' ') {
                encoded << '+';
            } else {
                encoded << c;
            }
        } else {
            encoded << '%' << std::setw(2) << static_cast<int>(static_cast<unsigned char>(c));
        }
    }

    return encoded.str();
}

}  // namespace

/// @brief ScreenScraper metadata provider
///
/// Implements the HashProvider interface for hash-based ROM identification.
/// Supports search by name, lookup by ID, and identification by filename or hash.
class ScreenScraperProvider : public HashProvider {
public:
    ScreenScraperProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache)
        : config_(config),
          cache_(std::move(cache)),
          base_url_("https://api.screenscraper.fr/api2"),
          user_agent_("retro-metadata/1.0"),
          dev_id_(kDefaultDevId),
          dev_password_(kDefaultDevPassword),
          region_priority_(kDefaultRegions),
          language_priority_(kDefaultLanguages),
          min_similarity_score_(0.6) {}

    std::string name() const override { return "screenscraper"; }

    std::vector<SearchResult> search(const std::string& query, const SearchOptions& opts) override {
        if (!is_enabled()) return {};

        cpr::Parameters params = build_auth_params();
        params.Add({{"recherche", query}});

        if (opts.platform_id) {
            params.Add({{"systemeid", std::to_string(*opts.platform_id)}});
        }

        auto result = request("jeuRecherche.php", params);
        if (result.is_null()) return {};

        auto response = result.value("response", nlohmann::json::object());
        auto games = response.value("jeux", nlohmann::json::array());

        // SS returns [{}] when no results
        if (games.size() == 1 && games[0].empty()) {
            return {};
        }

        int limit = opts.limit > 0 ? opts.limit : 30;
        std::vector<SearchResult> search_results;

        for (size_t i = 0; i < games.size() && static_cast<int>(i) < limit; ++i) {
            const auto& game = games[i];
            std::string game_id = get_string(game, "id");
            if (game_id.empty()) continue;

            auto names = game.value("noms", nlohmann::json::array());
            auto medias = game.value("medias", nlohmann::json::array());

            SearchResult sr;
            sr.provider = name();
            sr.provider_id = get_int(game, "id");
            sr.name = get_preferred_name(names);
            // Replace " : " with ": " for consistency
            size_t pos = 0;
            while ((pos = sr.name.find(" : ", pos)) != std::string::npos) {
                sr.name.replace(pos, 3, ": ");
                pos += 2;
            }
            sr.cover_url = get_media_url(medias, "box-2D");

            // Extract platform
            if (game.contains("systeme") && game["systeme"].is_object()) {
                sr.platforms.push_back(get_string(game["systeme"], "text"));
            }

            // Extract release year from dates
            if (game.contains("dates") && game["dates"].is_array() && !game["dates"].empty()) {
                std::string date_text = get_string(game["dates"][0], "text");
                if (date_text.length() >= 4) {
                    try {
                        sr.release_year = std::stoi(date_text.substr(0, 4));
                    } catch (...) {}
                }
            }

            search_results.push_back(std::move(sr));
        }

        return search_results;
    }

    std::unique_ptr<GameResult> get_by_id(int game_id) override {
        if (!is_enabled()) return nullptr;

        cpr::Parameters params = build_auth_params();
        params.Add({{"gameid", std::to_string(game_id)}});

        auto result = request("jeuInfos.php", params);
        if (result.is_null()) return nullptr;

        auto response = result.value("response", nlohmann::json::object());
        auto game = response.value("jeu", nlohmann::json::object());

        if (game.empty() || get_string(game, "id").empty()) {
            return nullptr;
        }

        return build_game_result(game);
    }

    std::unique_ptr<GameResult> identify(const std::string& filename, const IdentifyOptions& opts) override {
        if (!is_enabled()) return nullptr;

        // Check for ScreenScraper ID tag in filename
        std::smatch match;
        if (std::regex_search(filename, match, kScreenScraperTagRegex) && match.size() > 1) {
            try {
                int id = std::stoi(match[1].str());
                auto result = get_by_id(id);
                if (result) return result;
            } catch (...) {}
        }

        if (!opts.platform_id) return nullptr;

        // Clean the filename
        std::string search_term = clean_filename(filename);
        search_term = normalization::normalize_search_term_default(search_term);

        // Search for the game
        cpr::Parameters params = build_auth_params();
        params.Add({{"recherche", url_encode(search_term)}});
        params.Add({{"systemeid", std::to_string(*opts.platform_id)}});

        auto result = request("jeuRecherche.php", params);
        if (result.is_null()) return nullptr;

        auto response = result.value("response", nlohmann::json::object());
        auto games = response.value("jeux", nlohmann::json::array());

        // SS returns [{}] when no results
        if (games.size() == 1 && games[0].empty()) {
            games = nlohmann::json::array();
        }

        // If no results, try splitting by special characters
        if (games.empty()) {
            auto terms = normalization::split_search_term(search_term);
            if (terms.size() > 1) {
                params = build_auth_params();
                params.Add({{"recherche", url_encode(terms.back())}});
                params.Add({{"systemeid", std::to_string(*opts.platform_id)}});

                result = request("jeuRecherche.php", params);
                if (!result.is_null()) {
                    response = result.value("response", nlohmann::json::object());
                    games = response.value("jeux", nlohmann::json::array());
                    if (games.size() == 1 && games[0].empty()) {
                        games = nlohmann::json::array();
                    }
                }
            }
        }

        if (games.empty()) return nullptr;

        // Build name mapping - keep game with lowest ID for duplicate names
        std::map<std::string, nlohmann::json> games_by_name;
        std::vector<std::string> names;

        for (const auto& game : games) {
            std::string game_id = get_string(game, "id");
            if (game_id.empty()) continue;

            auto game_noms = game.value("noms", nlohmann::json::array());
            for (const auto& n : game_noms) {
                std::string name_text = get_string(n, "text");
                if (!name_text.empty()) {
                    auto it = games_by_name.find(name_text);
                    if (it != games_by_name.end()) {
                        int existing_id = get_int(it->second, "id");
                        int new_id = get_int(game, "id");
                        if (new_id < existing_id) {
                            games_by_name[name_text] = game;
                        }
                    } else {
                        games_by_name[name_text] = game;
                        names.push_back(name_text);
                    }
                }
            }
        }

        // Find best match
        matching::FindBestMatchOptions match_opts;
        match_opts.min_similarity_score = min_similarity_score_;
        auto best = matching::find_best_match(search_term, names, match_opts);

        if (best.found()) {
            auto it = games_by_name.find(best.match);
            if (it != games_by_name.end()) {
                auto game_result = build_game_result(it->second);
                game_result->match_score = best.score;
                return game_result;
            }
        }

        return nullptr;
    }

    std::unique_ptr<GameResult> identify_by_hash(const FileHashes& hashes, const IdentifyOptions& opts) override {
        if (!is_enabled()) return nullptr;
        if (!opts.platform_id) return nullptr;
        if (!hashes.has_any()) return nullptr;

        return lookup_by_hash(*opts.platform_id, hashes.md5, hashes.sha1, hashes.crc32, 0);
    }

    void heartbeat() override {
        cpr::Parameters params = build_auth_params();
        params.Add({{"recherche", "test"}});
        request("jeuRecherche.php", params);
    }

    void close() override {}

private:
    /// Check if provider is enabled and configured
    bool is_enabled() const {
        return config_.enabled;
    }

    /// Get username credential
    std::string username() const {
        return config_.get_credential("username");
    }

    /// Get password credential
    std::string password() const {
        return config_.get_credential("password");
    }

    /// Build authentication parameters for API requests
    cpr::Parameters build_auth_params() const {
        cpr::Parameters params{
            {"output", "json"},
            {"softname", "retro-metadata"},
            {"ssid", username()},
            {"sspassword", password()}
        };
        if (!dev_id_.empty()) {
            params.Add({{"devid", dev_id_}});
        }
        if (!dev_password_.empty()) {
            params.Add({{"devpassword", dev_password_}});
        }
        return params;
    }

    /// Make an API request
    nlohmann::json request(const std::string& endpoint, const cpr::Parameters& params) {
        std::string url = base_url_ + "/" + endpoint;

        cpr::Response r = cpr::Get(
            cpr::Url{url},
            params,
            cpr::Header{{"User-Agent", user_agent_}},
            cpr::Timeout{config_.timeout * 1000}
        );

        // Check for login error in response text
        if (r.text.find("Erreur de login") != std::string::npos) {
            throw AuthError(name(), "Invalid credentials");
        }

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
            throw ConnectionError(name(), "Failed to parse response: " + std::string(e.what()));
        }
    }

    /// Lookup a game by ROM hash
    std::unique_ptr<GameResult> lookup_by_hash(int platform_id, const std::string& md5,
                                                const std::string& sha1, const std::string& crc,
                                                int64_t rom_size) {
        if (md5.empty() && sha1.empty() && crc.empty()) {
            return nullptr;
        }

        cpr::Parameters params = build_auth_params();
        params.Add({{"systemeid", std::to_string(platform_id)}});

        if (!md5.empty()) {
            params.Add({{"md5", md5}});
        }
        if (!sha1.empty()) {
            params.Add({{"sha1", sha1}});
        }
        if (!crc.empty()) {
            params.Add({{"crc", crc}});
        }
        if (rom_size > 0) {
            params.Add({{"romtaille", std::to_string(rom_size)}});
        }

        auto result = request("jeuInfos.php", params);
        if (result.is_null()) return nullptr;

        auto response = result.value("response", nlohmann::json::object());
        auto game = response.value("jeu", nlohmann::json::object());

        if (game.empty() || get_string(game, "id").empty()) {
            return nullptr;
        }

        return build_game_result(game);
    }

    /// Get preferred name based on region priority
    std::string get_preferred_name(const nlohmann::json& names) const {
        for (const auto& region : region_priority_) {
            for (const auto& n : names) {
                if (get_string(n, "region") == region) {
                    return get_string(n, "text");
                }
            }
        }
        // Fallback to first name
        if (!names.empty()) {
            return get_string(names[0], "text");
        }
        return "";
    }

    /// Get preferred text based on language priority
    std::string get_preferred_text(const nlohmann::json& items, const std::string& lang_key) const {
        for (const auto& lang : language_priority_) {
            for (const auto& item : items) {
                if (get_string(item, lang_key) == lang) {
                    return get_string(item, "text");
                }
            }
        }
        if (!items.empty()) {
            return get_string(items[0], "text");
        }
        return "";
    }

    /// Get media URL for a specific type with region preference
    std::string get_media_url(const nlohmann::json& medias, const std::string& media_type) const {
        // First try with region preference
        for (const auto& region : region_priority_) {
            for (const auto& m : medias) {
                if (get_string(m, "type") == media_type &&
                    get_string(m, "region") == region &&
                    get_string(m, "parent") == "jeu") {
                    return strip_sensitive_params(get_string(m, "url"));
                }
            }
        }
        // Fallback without region
        for (const auto& m : medias) {
            if (get_string(m, "type") == media_type && get_string(m, "parent") == "jeu") {
                return strip_sensitive_params(get_string(m, "url"));
            }
        }
        return "";
    }

    /// Build a GameResult from ScreenScraper game data
    std::unique_ptr<GameResult> build_game_result(const nlohmann::json& game) {
        auto result = std::make_unique<GameResult>();
        int game_id = get_int(game, "id");

        auto names = game.value("noms", nlohmann::json::array());
        auto synopsis = game.value("synopsis", nlohmann::json::array());
        auto medias = game.value("medias", nlohmann::json::array());

        result->provider = name();
        result->provider_id = game_id;
        result->provider_ids = {{"screenscraper", game_id}};

        std::string game_name = get_preferred_name(names);
        // Replace " : " with ": " for consistency
        size_t pos = 0;
        while ((pos = game_name.find(" : ", pos)) != std::string::npos) {
            game_name.replace(pos, 3, ": ");
            pos += 2;
        }
        result->name = game_name;
        result->summary = get_preferred_text(synopsis, "langue");

        // Extract artwork
        result->artwork.cover_url = get_media_url(medias, "box-2D");

        std::string screenshot = get_media_url(medias, "ss");
        if (!screenshot.empty()) {
            result->artwork.screenshot_urls.push_back(screenshot);
        }

        std::string title_screen = get_media_url(medias, "sstitle");
        if (!title_screen.empty()) {
            result->artwork.screenshot_urls.push_back(title_screen);
        }

        std::string fanart = get_media_url(medias, "fanart");
        if (!fanart.empty()) {
            result->artwork.screenshot_urls.push_back(fanart);
        }

        result->artwork.logo_url = get_media_url(medias, "wheel-hd");
        if (result->artwork.logo_url.empty()) {
            result->artwork.logo_url = get_media_url(medias, "wheel");
        }
        result->artwork.banner_url = get_media_url(medias, "screenmarquee");

        // Extract metadata
        result->metadata = extract_metadata(game);
        result->raw_response = game;

        return result;
    }

    /// Extract metadata from ScreenScraper game data
    GameMetadata extract_metadata(const nlohmann::json& game) {
        GameMetadata metadata;
        metadata.raw_data = game;

        // Genres (English names)
        if (game.contains("genres") && game["genres"].is_array()) {
            for (const auto& g : game["genres"]) {
                if (g.contains("noms") && g["noms"].is_array()) {
                    for (const auto& n : g["noms"]) {
                        if (get_string(n, "langue") == "en") {
                            std::string genre_name = get_string(n, "text");
                            if (!genre_name.empty()) {
                                metadata.genres.push_back(genre_name);
                            }
                            break;
                        }
                    }
                }
            }
        }

        // Franchises (from familles)
        if (game.contains("familles") && game["familles"].is_array()) {
            for (const auto& f : game["familles"]) {
                if (f.contains("noms") && f["noms"].is_array()) {
                    std::string text = get_preferred_text(f["noms"], "langue");
                    if (!text.empty()) {
                        metadata.franchises.push_back(text);
                    }
                }
            }
        }

        // Game modes
        if (game.contains("modes") && game["modes"].is_array()) {
            for (const auto& m : game["modes"]) {
                if (m.contains("noms") && m["noms"].is_array()) {
                    std::string text = get_preferred_text(m["noms"], "langue");
                    if (!text.empty()) {
                        metadata.game_modes.push_back(text);
                    }
                }
            }
        }

        // Alternative names
        if (game.contains("noms") && game["noms"].is_array()) {
            for (const auto& n : game["noms"]) {
                std::string text = get_string(n, "text");
                if (!text.empty()) {
                    metadata.alternative_names.push_back(text);
                }
            }
        }

        // Companies - publisher
        if (game.contains("editeur") && game["editeur"].is_object()) {
            std::string publisher = get_string(game["editeur"], "text");
            if (!publisher.empty()) {
                metadata.companies.push_back(publisher);
                metadata.publisher = publisher;
            }
        }

        // Companies - developer
        if (game.contains("developpeur") && game["developpeur"].is_object()) {
            std::string developer = get_string(game["developpeur"], "text");
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
        }

        // Rating (SS scores are out of 20, normalize to 100)
        if (game.contains("note") && game["note"].is_object()) {
            double note_val = get_double(game["note"], "text");
            if (note_val > 0) {
                metadata.total_rating = note_val * 5;
            }
        }

        // Player count
        if (game.contains("joueurs") && game["joueurs"].is_object()) {
            std::string player_text = get_string(game["joueurs"], "text");
            if (!player_text.empty() && player_text != "null" && player_text != "none") {
                metadata.player_count = player_text;
            } else {
                metadata.player_count = "1";
            }
        } else {
            metadata.player_count = "1";
        }

        // Release date
        if (game.contains("dates") && game["dates"].is_array() && !game["dates"].empty()) {
            // Find earliest date
            std::string earliest;
            for (const auto& d : game["dates"]) {
                std::string date_text = get_string(d, "text");
                if (earliest.empty() || date_text < earliest) {
                    earliest = date_text;
                }
            }

            if (!earliest.empty()) {
                // Try parsing as YYYY-MM-DD
                if (earliest.length() >= 10) {
                    std::tm tm = {};
                    std::istringstream ss(earliest);
                    ss >> std::get_time(&tm, "%Y-%m-%d");
                    if (!ss.fail()) {
                        metadata.first_release_date = std::mktime(&tm);
                        metadata.release_year = 1900 + tm.tm_year;
                    }
                }
                // Fallback: try just year
                if (!metadata.first_release_date && earliest.length() >= 4) {
                    try {
                        int year = std::stoi(earliest.substr(0, 4));
                        std::tm tm = {};
                        tm.tm_year = year - 1900;
                        tm.tm_mon = 0;
                        tm.tm_mday = 1;
                        metadata.first_release_date = std::mktime(&tm);
                        metadata.release_year = year;
                    } catch (...) {}
                }
            }
        }

        return metadata;
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
    std::string base_url_;
    std::string user_agent_;
    std::string dev_id_;
    std::string dev_password_;
    std::vector<std::string> region_priority_;
    std::vector<std::string> language_priority_;
    double min_similarity_score_;
};

namespace {
[[maybe_unused]] ProviderRegistrar screenscraper_registrar(
    "screenscraper",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<ScreenScraperProvider>(config, std::move(cache));
    });
}

}  // namespace retro_metadata
