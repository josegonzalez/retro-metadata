/// @file launchbox.cpp
/// @brief LaunchBox local XML file metadata provider

#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/errors.hpp>
#include <retro_metadata/internal/matching.hpp>
#include <retro_metadata/internal/normalization.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cctype>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <map>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

namespace retro_metadata {

namespace {

/// LaunchBox image base URL
const std::string kLaunchboxImageURL = "https://images.launchbox-app.com";

/// Regex to detect LaunchBox ID tags in filenames like (launchbox-12345)
const std::regex kLaunchboxTagRegex(R"(\(launchbox-(\d+)\))", std::regex::icase);

/// Cover image type priority for selecting the best cover
const std::vector<std::string> kCoverPriority = {
    "Box - Front",
    "Box - 3D",
    "Fanart - Box - Front",
    "Cart - Front",
    "Cart - 3D"
};

/// Platform name to ID mapping
const std::map<std::string, int> kPlatformMap = {
    {"3DO Interactive Multiplayer", 1},
    {"Nintendo 3DS", 24},
    {"Amstrad CPC", 3},
    {"Commodore Amiga", 2},
    {"Android", 4},
    {"Arcade", 5},
    {"Atari 2600", 6},
    {"Atari 5200", 7},
    {"Atari 7800", 8},
    {"Nintendo Game Boy", 17},
    {"Nintendo Game Boy Advance", 18},
    {"Nintendo Game Boy Color", 19},
    {"Sega Game Gear", 47},
    {"Sega Genesis", 49},
    {"Sega Dreamcast", 52},
    {"Nintendo 64", 25},
    {"Nintendo DS", 26},
    {"Nintendo Entertainment System", 27},
    {"Nintendo GameCube", 20},
    {"Nintendo Wii", 29},
    {"Nintendo Wii U", 30},
    {"Nintendo Switch", 61},
    {"Sony Playstation", 55},
    {"Sony Playstation 2", 56},
    {"Sony Playstation 3", 57},
    {"Sony PSP", 58},
    {"Sony Playstation Vita", 59},
    {"Microsoft Xbox", 31},
    {"Microsoft Xbox 360", 32},
    {"Super Nintendo Entertainment System", 60}
};

/// Get platform ID from platform name
int get_platform_id_by_name(const std::string& platform_name) {
    auto it = kPlatformMap.find(platform_name);
    return it != kPlatformMap.end() ? it->second : 0;
}

/// Convert string to lowercase
std::string to_lower(const std::string& s) {
    std::string result = s;
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

/// Trim whitespace from string
std::string trim(const std::string& s) {
    auto start = s.find_first_not_of(" \t\n\r");
    if (start == std::string::npos) return "";
    auto end = s.find_last_not_of(" \t\n\r");
    return s.substr(start, end - start + 1);
}

/// Clean a filename for matching
std::string clean_filename(const std::string& filename) {
    static const std::regex ext_pattern(R"(\.[^.]+$)");
    static const std::regex tag_pattern(R"(\s*[\(\[][^\)\]]*[\)\]])");
    std::string name = std::regex_replace(filename, ext_pattern, "");
    name = std::regex_replace(name, tag_pattern, "");
    return trim(name);
}

/// Extract YouTube video ID from a URL
std::string extract_video_id(const std::string& url) {
    if (url.empty()) return "";

    // Handle youtube.com/watch?v= format
    if (url.find("youtube.com/watch?v=") != std::string::npos) {
        size_t pos = url.find("v=");
        if (pos != std::string::npos) {
            std::string id = url.substr(pos + 2);
            size_t amp = id.find('&');
            if (amp != std::string::npos) {
                id = id.substr(0, amp);
            }
            return id;
        }
    }

    // Handle youtu.be/ format
    if (url.find("youtu.be/") != std::string::npos) {
        size_t pos = url.rfind('/');
        if (pos != std::string::npos) {
            std::string id = url.substr(pos + 1);
            size_t query = id.find('?');
            if (query != std::string::npos) {
                id = id.substr(0, query);
            }
            return id;
        }
    }

    return "";
}

/// Simple XML element parser state
struct XmlElement {
    std::string name;
    std::map<std::string, std::string> children;
};

/// Simple streaming XML parser for LaunchBox format
/// Parses elements like <Game>...</Game> or <GameImage>...</GameImage>
class SimpleXmlParser {
public:
    explicit SimpleXmlParser(std::istream& stream) : stream_(stream) {}

    /// Parse the next element with the given tag name
    /// Returns true if an element was found, false if EOF
    bool next_element(const std::string& tag_name, std::map<std::string, std::string>& data) {
        data.clear();
        std::string line;
        std::string open_tag = "<" + tag_name + ">";
        std::string close_tag = "</" + tag_name + ">";

        // Find opening tag
        while (std::getline(stream_, line)) {
            if (line.find(open_tag) != std::string::npos) {
                // Found opening tag, now parse children until closing tag
                while (std::getline(stream_, line)) {
                    if (line.find(close_tag) != std::string::npos) {
                        return true;
                    }

                    // Parse child element: <FieldName>Value</FieldName>
                    size_t tag_start = line.find('<');
                    if (tag_start == std::string::npos) continue;

                    size_t tag_end = line.find('>', tag_start);
                    if (tag_end == std::string::npos) continue;

                    std::string child_tag = line.substr(tag_start + 1, tag_end - tag_start - 1);
                    if (child_tag.empty() || child_tag[0] == '/') continue;

                    std::string close_child = "</" + child_tag + ">";
                    size_t value_start = tag_end + 1;
                    size_t value_end = line.find(close_child, value_start);

                    if (value_end != std::string::npos) {
                        std::string value = line.substr(value_start, value_end - value_start);
                        // Decode basic XML entities
                        value = decode_xml_entities(value);
                        data[child_tag] = value;
                    }
                }
            }
        }
        return false;
    }

private:
    std::string decode_xml_entities(const std::string& s) {
        std::string result = s;
        size_t pos = 0;

        // Decode &amp;
        while ((pos = result.find("&amp;", pos)) != std::string::npos) {
            result.replace(pos, 5, "&");
            pos += 1;
        }

        // Decode &lt;
        pos = 0;
        while ((pos = result.find("&lt;", pos)) != std::string::npos) {
            result.replace(pos, 4, "<");
            pos += 1;
        }

        // Decode &gt;
        pos = 0;
        while ((pos = result.find("&gt;", pos)) != std::string::npos) {
            result.replace(pos, 4, ">");
            pos += 1;
        }

        // Decode &quot;
        pos = 0;
        while ((pos = result.find("&quot;", pos)) != std::string::npos) {
            result.replace(pos, 6, "\"");
            pos += 1;
        }

        // Decode &apos;
        pos = 0;
        while ((pos = result.find("&apos;", pos)) != std::string::npos) {
            result.replace(pos, 6, "'");
            pos += 1;
        }

        return result;
    }

    std::istream& stream_;
};

}  // namespace

/// @brief LaunchBox local XML file metadata provider
class LaunchBoxProvider : public Provider {
public:
    LaunchBoxProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache)
        : config_(config), cache_(std::move(cache)), loaded_(false) {
        // Get metadata_path from options
        if (auto it = config_.options.find("metadata_path"); it != config_.options.end()) {
            try {
                metadata_path_ = std::any_cast<std::string>(it->second);
            } catch (const std::bad_any_cast&) {
                // Try const char*
                try {
                    metadata_path_ = std::any_cast<const char*>(it->second);
                } catch (const std::bad_any_cast&) {
                    // Ignore
                }
            }
        }
    }

    std::string name() const override { return "launchbox"; }

    std::vector<SearchResult> search(const std::string& query, const SearchOptions& opts) override {
        if (!config_.enabled) return {};

        if (!loaded_) {
            load_metadata(metadata_path_);
        }

        std::string query_lower = to_lower(query);
        int limit = opts.limit > 0 ? opts.limit : 20;

        std::vector<SearchResult> results;

        for (const auto& [name_lower, platforms] : games_by_name_) {
            if (name_lower.find(query_lower) == std::string::npos) {
                continue;
            }

            for (const auto& [platform_id, game] : platforms) {
                if (opts.platform_id && platform_id != *opts.platform_id) {
                    continue;
                }

                int db_id = 0;
                auto id_it = game.find("DatabaseID");
                if (id_it != game.end()) {
                    try {
                        db_id = std::stoi(id_it->second);
                    } catch (...) {}
                }

                std::string cover_url = get_best_cover(db_id);

                SearchResult sr;
                sr.provider = name();
                sr.provider_id = db_id;

                auto name_it = game.find("Name");
                sr.name = name_it != game.end() ? name_it->second : "";

                sr.cover_url = cover_url;

                auto platform_it = game.find("Platform");
                if (platform_it != game.end()) {
                    sr.platforms.push_back(platform_it->second);
                }

                auto date_it = game.find("ReleaseDate");
                if (date_it != game.end() && date_it->second.length() >= 4) {
                    try {
                        sr.release_year = std::stoi(date_it->second.substr(0, 4));
                    } catch (...) {}
                }

                results.push_back(std::move(sr));

                if (static_cast<int>(results.size()) >= limit) {
                    break;
                }
            }

            if (static_cast<int>(results.size()) >= limit) {
                break;
            }
        }

        return results;
    }

    std::unique_ptr<GameResult> get_by_id(int game_id) override {
        if (!config_.enabled) return nullptr;

        if (!loaded_) {
            load_metadata(metadata_path_);
        }

        auto it = games_by_id_.find(game_id);
        if (it == games_by_id_.end()) {
            return nullptr;
        }

        return build_game_result(it->second);
    }

    std::unique_ptr<GameResult> identify(const std::string& filename, const IdentifyOptions& opts) override {
        if (!config_.enabled) return nullptr;

        // Check for LaunchBox ID tag in filename
        std::smatch match;
        if (std::regex_search(filename, match, kLaunchboxTagRegex) && match.size() > 1) {
            try {
                int id = std::stoi(match[1].str());
                auto result = get_by_id(id);
                if (result) {
                    result->match_type = "tag";
                    return result;
                }
            } catch (...) {}
        }

        if (!loaded_) {
            load_metadata(metadata_path_);
        }

        // Clean the filename for matching
        std::string search_term = clean_filename(filename);
        // LaunchBox uses ": " instead of " - "
        static const std::regex dash_pattern(R"(\s?-\s)");
        search_term = std::regex_replace(search_term, dash_pattern, ": ");
        std::string search_term_lower = to_lower(search_term);

        // Look for exact match first
        auto exact_it = games_by_name_.find(search_term_lower);
        if (exact_it != games_by_name_.end()) {
            const auto& platforms = exact_it->second;
            if (opts.platform_id) {
                auto plat_it = platforms.find(*opts.platform_id);
                if (plat_it != platforms.end()) {
                    auto result = build_game_result(plat_it->second);
                    result->match_score = 1.0;
                    result->match_type = "exact";
                    return result;
                }
            }
            // Return first match if no platform specified
            if (!platforms.empty()) {
                auto result = build_game_result(platforms.begin()->second);
                result->match_score = 1.0;
                result->match_type = "exact";
                return result;
            }
        }

        // Build list of candidate names for fuzzy matching
        std::vector<std::string> names;
        names.reserve(games_by_name_.size());
        for (const auto& [name_key, _] : games_by_name_) {
            names.push_back(name_key);
        }

        auto best = matching::find_best_match_simple(search_term_lower, names);
        if (!best.found()) {
            return nullptr;
        }

        const auto& platforms = games_by_name_[best.match];
        const std::map<std::string, std::string>* game = nullptr;

        if (opts.platform_id) {
            auto plat_it = platforms.find(*opts.platform_id);
            if (plat_it != platforms.end()) {
                game = &plat_it->second;
            }
        }

        if (!game && !platforms.empty()) {
            game = &platforms.begin()->second;
        }

        if (!game) {
            return nullptr;
        }

        auto result = build_game_result(*game);
        result->match_score = best.score;
        result->match_type = "fuzzy";
        return result;
    }

    void heartbeat() override {
        if (!config_.enabled) {
            throw ConfigError("launchbox", "provider is disabled");
        }

        if (metadata_path_.empty()) {
            throw ConfigError("launchbox", "no metadata path configured");
        }

        if (!std::filesystem::exists(metadata_path_)) {
            throw ConnectionError(name(), "metadata file not found: " + metadata_path_);
        }
    }

    void close() override {
        games_by_id_.clear();
        games_by_name_.clear();
        images_by_id_.clear();
        loaded_ = false;
    }

    /// @brief Load metadata from LaunchBox XML file
    void load_metadata(const std::string& path) {
        std::string metadata_file = path;
        if (metadata_file.empty()) {
            metadata_file = metadata_path_;
        }
        if (metadata_file.empty()) {
            throw ConfigError("launchbox", "no metadata path provided");
        }

        std::ifstream file(metadata_file);
        if (!file.is_open()) {
            throw ConnectionError(name(), "failed to open metadata file: " + metadata_file);
        }

        SimpleXmlParser parser(file);
        std::map<std::string, std::string> game_data;

        while (parser.next_element("Game", game_data)) {
            auto db_id_it = game_data.find("DatabaseID");
            if (db_id_it == game_data.end() || db_id_it->second.empty()) {
                continue;
            }

            int db_id = 0;
            try {
                db_id = std::stoi(db_id_it->second);
            } catch (...) {
                continue;
            }

            games_by_id_[db_id] = game_data;

            // Index by name and platform
            auto name_it = game_data.find("Name");
            if (name_it != game_data.end() && !name_it->second.empty()) {
                std::string name_lower = to_lower(name_it->second);

                auto platform_it = game_data.find("Platform");
                int platform_id = 0;
                if (platform_it != game_data.end()) {
                    platform_id = get_platform_id_by_name(platform_it->second);
                }

                if (platform_id > 0) {
                    games_by_name_[name_lower][platform_id] = game_data;
                }
            }
        }

        // Try to load images from Images.xml
        load_images(metadata_file);

        loaded_ = true;
    }

private:
    void load_images(const std::string& metadata_path) {
        // Images.xml is typically in the parent directory
        std::filesystem::path meta_path(metadata_path);
        std::filesystem::path images_path = meta_path.parent_path().parent_path() / "Images.xml";

        if (!std::filesystem::exists(images_path)) {
            // Also try same directory
            images_path = meta_path.parent_path() / "Images.xml";
            if (!std::filesystem::exists(images_path)) {
                return;
            }
        }

        std::ifstream file(images_path);
        if (!file.is_open()) {
            return;
        }

        SimpleXmlParser parser(file);
        std::map<std::string, std::string> image_data;

        while (parser.next_element("GameImage", image_data)) {
            auto db_id_it = image_data.find("DatabaseID");
            if (db_id_it == image_data.end() || db_id_it->second.empty()) {
                continue;
            }

            int db_id = 0;
            try {
                db_id = std::stoi(db_id_it->second);
            } catch (...) {
                continue;
            }

            images_by_id_[db_id].push_back(image_data);
        }
    }

    std::string get_best_cover(int game_id) {
        auto it = images_by_id_.find(game_id);
        if (it == images_by_id_.end()) {
            return "";
        }

        for (const auto& cover_type : kCoverPriority) {
            for (const auto& image : it->second) {
                auto type_it = image.find("Type");
                if (type_it != image.end() && type_it->second == cover_type) {
                    auto filename_it = image.find("FileName");
                    if (filename_it != image.end() && !filename_it->second.empty()) {
                        return kLaunchboxImageURL + "/" + filename_it->second;
                    }
                }
            }
        }

        return "";
    }

    std::vector<std::string> get_screenshots(int game_id) {
        std::vector<std::string> screenshots;

        auto it = images_by_id_.find(game_id);
        if (it == images_by_id_.end()) {
            return screenshots;
        }

        for (const auto& image : it->second) {
            auto type_it = image.find("Type");
            if (type_it != image.end() && type_it->second.find("Screenshot") != std::string::npos) {
                auto filename_it = image.find("FileName");
                if (filename_it != image.end() && !filename_it->second.empty()) {
                    screenshots.push_back(kLaunchboxImageURL + "/" + filename_it->second);
                }
            }
        }

        return screenshots;
    }

    std::unique_ptr<GameResult> build_game_result(const std::map<std::string, std::string>& game) {
        auto result = std::make_unique<GameResult>();

        int db_id = 0;
        auto id_it = game.find("DatabaseID");
        if (id_it != game.end()) {
            try {
                db_id = std::stoi(id_it->second);
            } catch (...) {}
        }

        result->provider = name();
        result->provider_id = db_id;
        result->provider_ids = {{"launchbox", db_id}};

        auto name_it = game.find("Name");
        result->name = name_it != game.end() ? name_it->second : "";

        auto overview_it = game.find("Overview");
        result->summary = overview_it != game.end() ? overview_it->second : "";

        result->artwork.cover_url = get_best_cover(db_id);
        result->artwork.screenshot_urls = get_screenshots(db_id);

        // Extract metadata
        extract_metadata(game, result->metadata);

        // Store raw response
        nlohmann::json raw;
        for (const auto& [key, value] : game) {
            raw[key] = value;
        }
        result->raw_response = raw;
        result->metadata.raw_data = raw;

        return result;
    }

    void extract_metadata(const std::map<std::string, std::string>& game, GameMetadata& metadata) {
        // Release date
        auto date_it = game.find("ReleaseDate");
        if (date_it != game.end() && !date_it->second.empty()) {
            // Parse date in format "2006-01-02T15:04:05-07:00" or similar
            std::string date_str = date_it->second;
            if (date_str.length() >= 10) {
                try {
                    int year = std::stoi(date_str.substr(0, 4));
                    int month = std::stoi(date_str.substr(5, 2));
                    int day = std::stoi(date_str.substr(8, 2));

                    struct tm tm_info = {};
                    tm_info.tm_year = year - 1900;
                    tm_info.tm_mon = month - 1;
                    tm_info.tm_mday = day;
                    tm_info.tm_isdst = -1;

                    time_t timestamp = mktime(&tm_info);
                    if (timestamp != -1) {
                        metadata.first_release_date = static_cast<int64_t>(timestamp);
                    }
                    metadata.release_year = year;
                } catch (...) {}
            }
        }

        // Genres (semicolon-separated)
        auto genres_it = game.find("Genres");
        if (genres_it != game.end() && !genres_it->second.empty()) {
            std::istringstream iss(genres_it->second);
            std::string genre;
            while (std::getline(iss, genre, ';')) {
                genre = trim(genre);
                if (!genre.empty()) {
                    metadata.genres.push_back(genre);
                }
            }
        }

        // Companies
        auto publisher_it = game.find("Publisher");
        if (publisher_it != game.end() && !publisher_it->second.empty()) {
            metadata.publisher = publisher_it->second;
            metadata.companies.push_back(publisher_it->second);
        }

        auto developer_it = game.find("Developer");
        if (developer_it != game.end() && !developer_it->second.empty()) {
            metadata.developer = developer_it->second;
            if (developer_it->second != metadata.publisher) {
                metadata.companies.push_back(developer_it->second);
            }
        }

        // Age rating (ESRB)
        auto esrb_it = game.find("ESRB");
        if (esrb_it != game.end() && !esrb_it->second.empty()) {
            AgeRating rating;
            rating.category = "ESRB";
            // Parse "E - Everyone" format
            std::string esrb = esrb_it->second;
            size_t dash_pos = esrb.find(" - ");
            if (dash_pos != std::string::npos) {
                rating.rating = trim(esrb.substr(0, dash_pos));
            } else {
                rating.rating = trim(esrb);
            }
            metadata.age_ratings.push_back(std::move(rating));
        }

        // Player count
        auto max_players_it = game.find("MaxPlayers");
        if (max_players_it != game.end() && !max_players_it->second.empty()) {
            metadata.player_count = max_players_it->second;
        } else {
            metadata.player_count = "1";
        }

        // YouTube video
        auto video_it = game.find("VideoURL");
        if (video_it != game.end()) {
            metadata.youtube_video_id = extract_video_id(video_it->second);
        }

        // Community rating (convert from 0-5 to 0-100)
        auto rating_it = game.find("CommunityRating");
        if (rating_it != game.end() && !rating_it->second.empty()) {
            try {
                double rating = std::stod(rating_it->second);
                metadata.total_rating = rating * 20.0;  // Scale to 0-100
            } catch (...) {}
        }

        // Game modes
        if (max_players_it != game.end() && !max_players_it->second.empty()) {
            try {
                int max_players = std::stoi(max_players_it->second);
                if (max_players == 1) {
                    metadata.game_modes.push_back("Single player");
                }
                if (max_players > 1) {
                    metadata.game_modes.push_back("Multiplayer");
                }
            } catch (...) {}
        }

        auto coop_it = game.find("Cooperative");
        if (coop_it != game.end() && to_lower(coop_it->second) == "true") {
            metadata.game_modes.push_back("Co-op");
        }

        // Platforms
        auto platform_it = game.find("Platform");
        if (platform_it != game.end() && !platform_it->second.empty()) {
            Platform plat;
            plat.name = platform_it->second;
            int plat_id = get_platform_id_by_name(platform_it->second);
            if (plat_id > 0) {
                plat.provider_ids["launchbox"] = plat_id;
            }
            metadata.platforms.push_back(std::move(plat));
        }
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
    std::string metadata_path_;

    /// Games indexed by database ID
    std::map<int, std::map<std::string, std::string>> games_by_id_;

    /// Games indexed by lowercase name -> platform ID -> game data
    std::map<std::string, std::map<int, std::map<std::string, std::string>>> games_by_name_;

    /// Images indexed by database ID
    std::map<int, std::vector<std::map<std::string, std::string>>> images_by_id_;

    /// Whether metadata has been loaded
    bool loaded_;
};

namespace {
[[maybe_unused]] ProviderRegistrar launchbox_registrar(
    "launchbox",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<LaunchBoxProvider>(config, std::move(cache));
    });
}

}  // namespace retro_metadata
