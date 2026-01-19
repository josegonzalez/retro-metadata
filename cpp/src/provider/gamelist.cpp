/// @file gamelist.cpp
/// @brief Gamelist provider for local gamelist.xml files (EmulationStation format)

#include <retro_metadata/cache/cache.hpp>
#include <retro_metadata/config.hpp>
#include <retro_metadata/errors.hpp>
#include <retro_metadata/internal/matching.hpp>
#include <retro_metadata/provider/provider.hpp>
#include <retro_metadata/provider/registry.hpp>

#include <algorithm>
#include <any>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace retro_metadata {

namespace {

/// XML tag to media URL key mapping
const std::map<std::string, std::string> kXmlTagMap = {
    {"image", "image_url"},
    {"cover", "box2d_url"},
    {"backcover", "box2d_back_url"},
    {"box3d", "box3d_url"},
    {"fanart", "fanart_url"},
    {"manual", "manual_url"},
    {"marquee", "marquee_url"},
    {"miximage", "miximage_url"},
    {"physicalmedia", "physical_url"},
    {"screenshot", "screenshot_url"},
    {"title_screen", "title_screen_url"},
    {"thumbnail", "thumbnail_url"},
    {"video", "video_url"},
};

/// ES-DE media folder mapping
const std::map<std::string, std::string> kEsdeMediaMap = {
    {"image_url", "images"},
    {"box2d_url", "covers"},
    {"box2d_back_url", "backcovers"},
    {"box3d_url", "3dboxes"},
    {"fanart_url", "fanart"},
    {"manual_url", "manuals"},
    {"marquee_url", "marquees"},
    {"miximage_url", "miximages"},
    {"physical_url", "physicalmedia"},
    {"screenshot_url", "screenshots"},
    {"title_screen_url", "titlescreens"},
    {"thumbnail_url", "thumbnails"},
    {"video_url", "videos"},
};

/// Core fields to extract from game elements
const std::vector<std::string> kCoreFields = {
    "path", "name", "desc", "rating", "releasedate", "developer",
    "publisher", "genre", "players", "md5", "lang", "region", "family"};

/// FNV-1a hash for generating integer IDs from filenames
uint32_t fnv_hash(const std::string& str) {
    constexpr uint32_t kFnvPrime = 16777619;
    constexpr uint32_t kFnvOffsetBasis = 2166136261;

    uint32_t hash = kFnvOffsetBasis;
    for (char c : str) {
        hash ^= static_cast<uint32_t>(static_cast<unsigned char>(c));
        hash *= kFnvPrime;
    }
    return hash;
}

/// Converts a string to lowercase
std::string to_lower(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

/// Trims leading "./" from a path
std::string trim_dot_slash(const std::string& path) {
    if (path.size() >= 2 && path[0] == '.' && path[1] == '/') {
        return path.substr(2);
    }
    return path;
}

/// Resolves a relative path to an absolute file:// URL
std::string resolve_path(const std::string& path, const std::string& platform_dir) {
    std::string trimmed = trim_dot_slash(path);

    if (!platform_dir.empty()) {
        std::filesystem::path full_path = std::filesystem::path(platform_dir) / trimmed;
        std::error_code ec;
        if (std::filesystem::exists(full_path, ec)) {
            return "file://" + std::filesystem::absolute(full_path).string();
        }
    }

    return path;
}

/// Finds a media file in ES-DE folder structure
std::string find_media_file(const std::string& rom_stem, const std::string& folder_name,
                            const std::string& platform_dir) {
    if (platform_dir.empty()) {
        return "";
    }

    std::filesystem::path media_dir = std::filesystem::path(platform_dir) / folder_name;
    std::error_code ec;

    if (!std::filesystem::exists(media_dir, ec)) {
        return "";
    }

    // Search for files matching rom_stem.*
    for (const auto& entry : std::filesystem::directory_iterator(media_dir, ec)) {
        if (!entry.is_regular_file()) {
            continue;
        }
        std::string filename = entry.path().stem().string();
        if (filename == rom_stem) {
            return "file://" + std::filesystem::absolute(entry.path()).string();
        }
    }

    return "";
}

/// Simple XML parser state
enum class XmlState { Outside, InTag, InContent };

/// Extracts the tag name from an XML element like "<tagname>" or "</tagname>"
std::string extract_tag_name(const std::string& tag) {
    size_t start = 0;
    if (tag.size() > 0 && tag[0] == '<') start = 1;
    if (tag.size() > start && tag[start] == '/') start++;

    size_t end = tag.find_first_of(" \t\n\r/>", start);
    if (end == std::string::npos) {
        end = tag.size();
    }
    return tag.substr(start, end - start);
}

/// Checks if a tag is a self-closing tag
bool is_self_closing(const std::string& tag) {
    return tag.size() >= 2 && tag[tag.size() - 2] == '/';
}

/// Checks if a tag is a closing tag
bool is_closing_tag(const std::string& tag) {
    return tag.size() > 1 && tag[1] == '/';
}

/// Decodes basic XML entities
std::string decode_xml_entities(const std::string& str) {
    std::string result;
    result.reserve(str.size());

    for (size_t i = 0; i < str.size(); ++i) {
        if (str[i] == '&') {
            if (str.compare(i, 4, "&lt;") == 0) {
                result += '<';
                i += 3;
            } else if (str.compare(i, 4, "&gt;") == 0) {
                result += '>';
                i += 3;
            } else if (str.compare(i, 5, "&amp;") == 0) {
                result += '&';
                i += 4;
            } else if (str.compare(i, 6, "&quot;") == 0) {
                result += '"';
                i += 5;
            } else if (str.compare(i, 6, "&apos;") == 0) {
                result += '\'';
                i += 5;
            } else {
                result += str[i];
            }
        } else {
            result += str[i];
        }
    }

    return result;
}

/// Trims whitespace from both ends of a string
std::string trim(const std::string& str) {
    auto start = str.find_first_not_of(" \t\n\r");
    if (start == std::string::npos) return "";
    auto end = str.find_last_not_of(" \t\n\r");
    return str.substr(start, end - start + 1);
}

}  // namespace

/// @brief Gamelist metadata provider for local gamelist.xml files
class GamelistProvider : public Provider {
public:
    GamelistProvider(const ProviderConfig& config, std::shared_ptr<Cache> cache)
        : config_(config), cache_(std::move(cache)) {
        // Extract roms_path from options
        auto it = config_.options.find("roms_path");
        if (it != config_.options.end()) {
            try {
                roms_path_ = std::any_cast<std::string>(it->second);
            } catch (const std::bad_any_cast&) {
                // Ignore if not a string
            }
        }
    }

    std::string name() const override { return "gamelist"; }

    /// @brief Loads games from a gamelist.xml file
    /// @param gamelist_path Path to the gamelist.xml file
    /// @param platform_dir Optional platform directory for media resolution
    void load_gamelist(const std::string& gamelist_path, const std::string& platform_dir = "") {
        if (gamelist_path.empty()) {
            throw ConfigError("gamelist_path", "no gamelist path provided");
        }

        std::ifstream file(gamelist_path);
        if (!file.is_open()) {
            throw ConnectionError(name(), "failed to open gamelist file: " + gamelist_path);
        }

        // Set platform directory
        if (!platform_dir.empty()) {
            platform_dir_ = platform_dir;
        } else {
            platform_dir_ = std::filesystem::path(gamelist_path).parent_path().string();
        }

        // Read entire file
        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string content = buffer.str();
        file.close();

        // Parse XML
        parse_gamelist_xml(content);
        loaded_ = true;
    }

    std::vector<SearchResult> search(const std::string& query, const SearchOptions& opts) override {
        if (!config_.enabled || !loaded_) {
            return {};
        }

        std::string query_lower = to_lower(query);
        int limit = opts.limit > 0 ? opts.limit : 20;

        std::vector<SearchResult> results;
        for (const auto& [filename, game] : games_by_filename_) {
            auto name_it = game.find("name");
            std::string game_name = name_it != game.end() ? name_it->second : "";

            // Check if query matches name or filename
            if (to_lower(game_name).find(query_lower) == std::string::npos &&
                to_lower(filename).find(query_lower) == std::string::npos) {
                continue;
            }

            // Get cover URL
            std::string cover_url;
            auto cover_it = game.find("box2d_url");
            if (cover_it != game.end()) {
                cover_url = cover_it->second;
            } else {
                auto image_it = game.find("image_url");
                if (image_it != game.end()) {
                    cover_url = image_it->second;
                }
            }

            SearchResult sr;
            sr.name = game_name;
            sr.provider = name();
            sr.provider_id = static_cast<int>(fnv_hash(filename));
            sr.cover_url = cover_url;
            sr.platforms = {};

            results.push_back(std::move(sr));

            if (static_cast<int>(results.size()) >= limit) {
                break;
            }
        }

        return results;
    }

    std::unique_ptr<GameResult> get_by_id(int game_id) override {
        if (!config_.enabled || !loaded_) {
            return nullptr;
        }

        // Find by matching hash
        for (const auto& [filename, game] : games_by_filename_) {
            if (static_cast<int>(fnv_hash(filename)) == game_id) {
                return build_game_result(game, filename);
            }
        }

        return nullptr;
    }

    std::unique_ptr<GameResult> identify(const std::string& filename,
                                         const IdentifyOptions& /*opts*/) override {
        if (!config_.enabled || !loaded_) {
            return nullptr;
        }

        // Try exact match first
        auto it = games_by_filename_.find(filename);
        if (it != games_by_filename_.end()) {
            auto result = build_game_result(it->second, filename);
            result->match_score = 1.0;
            result->match_type = "exact";
            return result;
        }

        // Try fuzzy match
        std::vector<std::string> names;
        names.reserve(games_by_filename_.size());
        for (const auto& [name, _] : games_by_filename_) {
            names.push_back(name);
        }

        auto best = matching::find_best_match_simple(filename, names);
        if (!best.found()) {
            return nullptr;
        }

        auto game_it = games_by_filename_.find(best.match);
        if (game_it == games_by_filename_.end()) {
            return nullptr;
        }

        auto result = build_game_result(game_it->second, best.match);
        result->match_score = best.score;
        result->match_type = "fuzzy";
        return result;
    }

    void heartbeat() override {
        if (!config_.enabled) {
            throw ConnectionError(name(), "provider is disabled");
        }
        // Gamelist is a local file provider, just check if enabled
    }

    void close() override { clear_cache(); }

    /// @brief Clears the loaded gamelist data
    void clear_cache() {
        games_by_filename_.clear();
        games_by_path_.clear();
        platform_dir_.clear();
        loaded_ = false;
    }

private:
    /// Parses the gamelist.xml content
    void parse_gamelist_xml(const std::string& content) {
        size_t pos = 0;
        while (pos < content.size()) {
            // Find next '<'
            size_t tag_start = content.find('<', pos);
            if (tag_start == std::string::npos) {
                break;
            }

            // Find closing '>'
            size_t tag_end = content.find('>', tag_start);
            if (tag_end == std::string::npos) {
                break;
            }

            std::string tag = content.substr(tag_start, tag_end - tag_start + 1);
            std::string tag_name = extract_tag_name(tag);

            if (tag_name == "game" && !is_closing_tag(tag)) {
                // Parse game element
                pos = parse_game_element(content, tag_end + 1);
            } else {
                pos = tag_end + 1;
            }
        }
    }

    /// Parses a single game element and returns position after </game>
    size_t parse_game_element(const std::string& content, size_t start) {
        std::map<std::string, std::string> game;
        size_t pos = start;

        while (pos < content.size()) {
            // Find next '<'
            size_t tag_start = content.find('<', pos);
            if (tag_start == std::string::npos) {
                break;
            }

            // Find closing '>'
            size_t tag_end = content.find('>', tag_start);
            if (tag_end == std::string::npos) {
                break;
            }

            std::string tag = content.substr(tag_start, tag_end - tag_start + 1);
            std::string tag_name = extract_tag_name(tag);

            // Check for end of game element
            if (tag_name == "game" && is_closing_tag(tag)) {
                // Finalize game and add to maps
                finalize_game(game);
                return tag_end + 1;
            }

            // Skip closing tags and self-closing tags
            if (is_closing_tag(tag) || is_self_closing(tag)) {
                pos = tag_end + 1;
                continue;
            }

            // Find the closing tag for this element
            std::string close_tag = "</" + tag_name + ">";
            size_t close_pos = content.find(close_tag, tag_end + 1);
            if (close_pos == std::string::npos) {
                pos = tag_end + 1;
                continue;
            }

            // Extract content between tags
            std::string element_content = content.substr(tag_end + 1, close_pos - tag_end - 1);
            element_content = trim(decode_xml_entities(element_content));

            // Store core fields
            for (const auto& field : kCoreFields) {
                if (tag_name == field) {
                    game[tag_name] = element_content;
                    break;
                }
            }

            // Store media fields with resolved paths
            auto media_it = kXmlTagMap.find(tag_name);
            if (media_it != kXmlTagMap.end()) {
                game[media_it->second] = resolve_path(element_content, platform_dir_);
            }

            pos = close_pos + close_tag.size();
        }

        return pos;
    }

    /// Finalizes a game entry and adds it to the maps
    void finalize_game(std::map<std::string, std::string>& game) {
        auto path_it = game.find("path");
        if (path_it == game.end() || path_it->second.empty()) {
            return;
        }

        std::string game_path = path_it->second;
        std::filesystem::path p(game_path);
        std::string filename = p.filename().string();
        std::string rom_stem = p.stem().string();

        // Try to find media in ES-DE folder structure
        for (const auto& [media_key, folder_name] : kEsdeMediaMap) {
            if (game.find(media_key) == game.end()) {
                std::string media_path = find_media_file(rom_stem, folder_name, platform_dir_);
                if (!media_path.empty()) {
                    game[media_key] = media_path;
                }
            }
        }

        // Index by filename and path
        games_by_filename_[filename] = game;
        games_by_path_[game_path] = game;
    }

    /// Builds a GameResult from a game map
    std::unique_ptr<GameResult> build_game_result(const std::map<std::string, std::string>& game,
                                                  const std::string& filename) {
        auto result = std::make_unique<GameResult>();

        auto name_it = game.find("name");
        result->name = name_it != game.end() ? name_it->second : "";

        auto desc_it = game.find("desc");
        result->summary = desc_it != game.end() ? desc_it->second : "";

        result->provider = name();

        int provider_id = static_cast<int>(fnv_hash(filename));
        result->provider_id = provider_id;
        result->provider_ids = {{"gamelist", provider_id}};

        // Artwork
        result->artwork = build_artwork(game);

        // Metadata
        result->metadata = build_metadata(game);

        // Raw response
        result->raw_response = nlohmann::json(game);

        return result;
    }

    /// Builds artwork from a game map
    Artwork build_artwork(const std::map<std::string, std::string>& game) {
        Artwork artwork;

        // Cover URL (prefer box2d, fall back to image)
        auto cover_it = game.find("box2d_url");
        if (cover_it != game.end()) {
            artwork.cover_url = cover_it->second;
        } else {
            auto image_it = game.find("image_url");
            if (image_it != game.end()) {
                artwork.cover_url = image_it->second;
            }
        }

        // Screenshot URLs
        for (const auto& key : {"screenshot_url", "title_screen_url", "fanart_url"}) {
            auto it = game.find(key);
            if (it != game.end() && !it->second.empty()) {
                artwork.screenshot_urls.push_back(it->second);
            }
        }

        // Logo (marquee)
        auto marquee_it = game.find("marquee_url");
        if (marquee_it != game.end()) {
            artwork.logo_url = marquee_it->second;
        }

        // Background (fanart)
        auto fanart_it = game.find("fanart_url");
        if (fanart_it != game.end()) {
            artwork.background_url = fanart_it->second;
        }

        return artwork;
    }

    /// Builds metadata from a game map
    GameMetadata build_metadata(const std::map<std::string, std::string>& game) {
        GameMetadata metadata;

        // Rating (gamelist uses 0-1 scale, convert to 0-100)
        auto rating_it = game.find("rating");
        if (rating_it != game.end() && !rating_it->second.empty()) {
            try {
                double rating = std::stod(rating_it->second);
                metadata.total_rating = rating * 100.0;
            } catch (...) {
                // Ignore parse errors
            }
        }

        // Release year (from releasedate, format: YYYYMMDD)
        auto release_it = game.find("releasedate");
        if (release_it != game.end() && release_it->second.size() >= 4) {
            try {
                int year = std::stoi(release_it->second.substr(0, 4));
                if (year > 1900 && year < 2100) {
                    metadata.release_year = year;
                }
            } catch (...) {
                // Ignore parse errors
            }
        }

        // Genres (comma-separated)
        auto genre_it = game.find("genre");
        if (genre_it != game.end() && !genre_it->second.empty()) {
            std::string genre = genre_it->second;
            size_t pos = 0;
            while (pos < genre.size()) {
                size_t comma = genre.find(',', pos);
                if (comma == std::string::npos) {
                    metadata.genres.push_back(trim(genre.substr(pos)));
                    break;
                }
                metadata.genres.push_back(trim(genre.substr(pos, comma - pos)));
                pos = comma + 1;
            }
        }

        // Developer
        auto dev_it = game.find("developer");
        if (dev_it != game.end()) {
            metadata.developer = dev_it->second;
        }

        // Publisher
        auto pub_it = game.find("publisher");
        if (pub_it != game.end()) {
            metadata.publisher = pub_it->second;
        }

        // Companies
        if (!metadata.developer.empty()) {
            metadata.companies.push_back(metadata.developer);
        }
        if (!metadata.publisher.empty() && metadata.publisher != metadata.developer) {
            metadata.companies.push_back(metadata.publisher);
        }

        // Franchises (from family field)
        auto family_it = game.find("family");
        if (family_it != game.end() && !family_it->second.empty()) {
            metadata.franchises.push_back(family_it->second);
        }

        // Player count
        auto players_it = game.find("players");
        if (players_it != game.end() && !players_it->second.empty()) {
            metadata.player_count = players_it->second;
        } else {
            metadata.player_count = "1";
        }

        // Raw data
        metadata.raw_data = nlohmann::json(game);

        return metadata;
    }

    ProviderConfig config_;
    std::shared_ptr<Cache> cache_;
    std::string roms_path_;
    std::string platform_dir_;
    std::map<std::string, std::map<std::string, std::string>> games_by_filename_;
    std::map<std::string, std::map<std::string, std::string>> games_by_path_;
    bool loaded_ = false;
};

// Auto-register the provider
namespace {
[[maybe_unused]] ProviderRegistrar gamelist_registrar(
    "gamelist",
    [](const ProviderConfig& config, std::shared_ptr<Cache> cache) {
        return std::make_unique<GamelistProvider>(config, std::move(cache));
    });
}  // namespace

}  // namespace retro_metadata
