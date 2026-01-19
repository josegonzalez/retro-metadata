#include <retro_metadata/types.hpp>

namespace retro_metadata {

// Platform serialization
void to_json(nlohmann::json& j, const Platform& p) {
    j = nlohmann::json{{"slug", p.slug}, {"name", p.name}};
    if (!p.provider_ids.empty()) {
        j["provider_ids"] = p.provider_ids;
    }
}

void from_json(const nlohmann::json& j, Platform& p) {
    j.at("slug").get_to(p.slug);
    j.at("name").get_to(p.name);
    if (j.contains("provider_ids")) {
        j.at("provider_ids").get_to(p.provider_ids);
    }
}

// AgeRating serialization
void to_json(nlohmann::json& j, const AgeRating& a) {
    j = nlohmann::json{{"rating", a.rating}, {"category", a.category}};
    if (!a.cover_url.empty()) {
        j["cover_url"] = a.cover_url;
    }
}

void from_json(const nlohmann::json& j, AgeRating& a) {
    j.at("rating").get_to(a.rating);
    j.at("category").get_to(a.category);
    if (j.contains("cover_url")) {
        j.at("cover_url").get_to(a.cover_url);
    }
}

// MultiplayerMode serialization
void to_json(nlohmann::json& j, const MultiplayerMode& m) {
    j = nlohmann::json{
        {"campaign_coop", m.campaign_coop},
        {"drop_in", m.drop_in},
        {"lan_coop", m.lan_coop},
        {"offline_coop", m.offline_coop},
        {"offline_coop_max", m.offline_coop_max},
        {"offline_max", m.offline_max},
        {"online_coop", m.online_coop},
        {"online_coop_max", m.online_coop_max},
        {"online_max", m.online_max},
        {"split_screen", m.split_screen},
        {"split_screen_online", m.split_screen_online}};
    if (m.platform) {
        j["platform"] = *m.platform;
    }
}

void from_json(const nlohmann::json& j, MultiplayerMode& m) {
    if (j.contains("platform") && !j.at("platform").is_null()) {
        m.platform = j.at("platform").get<Platform>();
    }
    if (j.contains("campaign_coop")) j.at("campaign_coop").get_to(m.campaign_coop);
    if (j.contains("drop_in")) j.at("drop_in").get_to(m.drop_in);
    if (j.contains("lan_coop")) j.at("lan_coop").get_to(m.lan_coop);
    if (j.contains("offline_coop")) j.at("offline_coop").get_to(m.offline_coop);
    if (j.contains("offline_coop_max")) j.at("offline_coop_max").get_to(m.offline_coop_max);
    if (j.contains("offline_max")) j.at("offline_max").get_to(m.offline_max);
    if (j.contains("online_coop")) j.at("online_coop").get_to(m.online_coop);
    if (j.contains("online_coop_max")) j.at("online_coop_max").get_to(m.online_coop_max);
    if (j.contains("online_max")) j.at("online_max").get_to(m.online_max);
    if (j.contains("split_screen")) j.at("split_screen").get_to(m.split_screen);
    if (j.contains("split_screen_online")) j.at("split_screen_online").get_to(m.split_screen_online);
}

// RelatedGame serialization
void to_json(nlohmann::json& j, const RelatedGame& r) {
    j = nlohmann::json{{"id", r.id}, {"name", r.name}};
    if (!r.slug.empty()) j["slug"] = r.slug;
    if (!r.relation_type.empty()) j["relation_type"] = r.relation_type;
    if (!r.cover_url.empty()) j["cover_url"] = r.cover_url;
    if (!r.provider.empty()) j["provider"] = r.provider;
}

void from_json(const nlohmann::json& j, RelatedGame& r) {
    j.at("id").get_to(r.id);
    j.at("name").get_to(r.name);
    if (j.contains("slug")) j.at("slug").get_to(r.slug);
    if (j.contains("relation_type")) j.at("relation_type").get_to(r.relation_type);
    if (j.contains("cover_url")) j.at("cover_url").get_to(r.cover_url);
    if (j.contains("provider")) j.at("provider").get_to(r.provider);
}

// Artwork serialization
void to_json(nlohmann::json& j, const Artwork& a) {
    j = nlohmann::json::object();
    if (!a.cover_url.empty()) j["cover_url"] = a.cover_url;
    if (!a.screenshot_urls.empty()) j["screenshot_urls"] = a.screenshot_urls;
    if (!a.banner_url.empty()) j["banner_url"] = a.banner_url;
    if (!a.icon_url.empty()) j["icon_url"] = a.icon_url;
    if (!a.logo_url.empty()) j["logo_url"] = a.logo_url;
    if (!a.background_url.empty()) j["background_url"] = a.background_url;
}

void from_json(const nlohmann::json& j, Artwork& a) {
    if (j.contains("cover_url")) j.at("cover_url").get_to(a.cover_url);
    if (j.contains("screenshot_urls")) j.at("screenshot_urls").get_to(a.screenshot_urls);
    if (j.contains("banner_url")) j.at("banner_url").get_to(a.banner_url);
    if (j.contains("icon_url")) j.at("icon_url").get_to(a.icon_url);
    if (j.contains("logo_url")) j.at("logo_url").get_to(a.logo_url);
    if (j.contains("background_url")) j.at("background_url").get_to(a.background_url);
}

// GameMetadata serialization
void to_json(nlohmann::json& j, const GameMetadata& m) {
    j = nlohmann::json::object();
    if (m.total_rating) j["total_rating"] = *m.total_rating;
    if (m.aggregated_rating) j["aggregated_rating"] = *m.aggregated_rating;
    if (m.first_release_date) j["first_release_date"] = *m.first_release_date;
    if (!m.youtube_video_id.empty()) j["youtube_video_id"] = m.youtube_video_id;
    if (!m.genres.empty()) j["genres"] = m.genres;
    if (!m.franchises.empty()) j["franchises"] = m.franchises;
    if (!m.alternative_names.empty()) j["alternative_names"] = m.alternative_names;
    if (!m.collections.empty()) j["collections"] = m.collections;
    if (!m.companies.empty()) j["companies"] = m.companies;
    if (!m.game_modes.empty()) j["game_modes"] = m.game_modes;
    if (!m.age_ratings.empty()) j["age_ratings"] = m.age_ratings;
    if (!m.platforms.empty()) j["platforms"] = m.platforms;
    if (!m.multiplayer_modes.empty()) j["multiplayer_modes"] = m.multiplayer_modes;
    if (!m.player_count.empty()) j["player_count"] = m.player_count;
    if (!m.expansions.empty()) j["expansions"] = m.expansions;
    if (!m.dlcs.empty()) j["dlcs"] = m.dlcs;
    if (!m.remasters.empty()) j["remasters"] = m.remasters;
    if (!m.remakes.empty()) j["remakes"] = m.remakes;
    if (!m.expanded_games.empty()) j["expanded_games"] = m.expanded_games;
    if (!m.ports.empty()) j["ports"] = m.ports;
    if (!m.similar_games.empty()) j["similar_games"] = m.similar_games;
    if (!m.developer.empty()) j["developer"] = m.developer;
    if (!m.publisher.empty()) j["publisher"] = m.publisher;
    if (m.release_year) j["release_year"] = *m.release_year;
    if (!m.raw_data.is_null()) j["raw_data"] = m.raw_data;
}

void from_json(const nlohmann::json& j, GameMetadata& m) {
    if (j.contains("total_rating")) m.total_rating = j.at("total_rating").get<double>();
    if (j.contains("aggregated_rating"))
        m.aggregated_rating = j.at("aggregated_rating").get<double>();
    if (j.contains("first_release_date"))
        m.first_release_date = j.at("first_release_date").get<int64_t>();
    if (j.contains("youtube_video_id")) j.at("youtube_video_id").get_to(m.youtube_video_id);
    if (j.contains("genres")) j.at("genres").get_to(m.genres);
    if (j.contains("franchises")) j.at("franchises").get_to(m.franchises);
    if (j.contains("alternative_names")) j.at("alternative_names").get_to(m.alternative_names);
    if (j.contains("collections")) j.at("collections").get_to(m.collections);
    if (j.contains("companies")) j.at("companies").get_to(m.companies);
    if (j.contains("game_modes")) j.at("game_modes").get_to(m.game_modes);
    if (j.contains("age_ratings")) j.at("age_ratings").get_to(m.age_ratings);
    if (j.contains("platforms")) j.at("platforms").get_to(m.platforms);
    if (j.contains("multiplayer_modes")) j.at("multiplayer_modes").get_to(m.multiplayer_modes);
    if (j.contains("player_count")) j.at("player_count").get_to(m.player_count);
    if (j.contains("expansions")) j.at("expansions").get_to(m.expansions);
    if (j.contains("dlcs")) j.at("dlcs").get_to(m.dlcs);
    if (j.contains("remasters")) j.at("remasters").get_to(m.remasters);
    if (j.contains("remakes")) j.at("remakes").get_to(m.remakes);
    if (j.contains("expanded_games")) j.at("expanded_games").get_to(m.expanded_games);
    if (j.contains("ports")) j.at("ports").get_to(m.ports);
    if (j.contains("similar_games")) j.at("similar_games").get_to(m.similar_games);
    if (j.contains("developer")) j.at("developer").get_to(m.developer);
    if (j.contains("publisher")) j.at("publisher").get_to(m.publisher);
    if (j.contains("release_year")) m.release_year = j.at("release_year").get<int>();
    if (j.contains("raw_data")) m.raw_data = j.at("raw_data");
}

// GameResult serialization
void to_json(nlohmann::json& j, const GameResult& g) {
    j = nlohmann::json{{"name", g.name}, {"artwork", g.artwork}, {"metadata", g.metadata}};
    if (!g.summary.empty()) j["summary"] = g.summary;
    if (!g.provider.empty()) j["provider"] = g.provider;
    if (g.provider_id) j["provider_id"] = *g.provider_id;
    if (!g.provider_ids.empty()) j["provider_ids"] = g.provider_ids;
    if (!g.slug.empty()) j["slug"] = g.slug;
    if (g.match_score > 0) j["match_score"] = g.match_score;
    if (!g.match_type.empty()) j["match_type"] = g.match_type;
    if (!g.raw_response.is_null()) j["raw_response"] = g.raw_response;
}

void from_json(const nlohmann::json& j, GameResult& g) {
    j.at("name").get_to(g.name);
    if (j.contains("summary")) j.at("summary").get_to(g.summary);
    if (j.contains("provider")) j.at("provider").get_to(g.provider);
    if (j.contains("provider_id")) g.provider_id = j.at("provider_id").get<int>();
    if (j.contains("provider_ids")) j.at("provider_ids").get_to(g.provider_ids);
    if (j.contains("slug")) j.at("slug").get_to(g.slug);
    if (j.contains("artwork")) j.at("artwork").get_to(g.artwork);
    if (j.contains("metadata")) j.at("metadata").get_to(g.metadata);
    if (j.contains("match_score")) j.at("match_score").get_to(g.match_score);
    if (j.contains("match_type")) j.at("match_type").get_to(g.match_type);
    if (j.contains("raw_response")) g.raw_response = j.at("raw_response");
}

// SearchResult serialization
void to_json(nlohmann::json& j, const SearchResult& s) {
    j = nlohmann::json{{"name", s.name}, {"provider", s.provider}, {"provider_id", s.provider_id}};
    if (!s.slug.empty()) j["slug"] = s.slug;
    if (!s.cover_url.empty()) j["cover_url"] = s.cover_url;
    if (!s.platforms.empty()) j["platforms"] = s.platforms;
    if (s.release_year) j["release_year"] = *s.release_year;
    if (s.match_score > 0) j["match_score"] = s.match_score;
}

void from_json(const nlohmann::json& j, SearchResult& s) {
    j.at("name").get_to(s.name);
    j.at("provider").get_to(s.provider);
    j.at("provider_id").get_to(s.provider_id);
    if (j.contains("slug")) j.at("slug").get_to(s.slug);
    if (j.contains("cover_url")) j.at("cover_url").get_to(s.cover_url);
    if (j.contains("platforms")) j.at("platforms").get_to(s.platforms);
    if (j.contains("release_year")) s.release_year = j.at("release_year").get<int>();
    if (j.contains("match_score")) j.at("match_score").get_to(s.match_score);
}

// FileHashes serialization
void to_json(nlohmann::json& j, const FileHashes& h) {
    j = nlohmann::json::object();
    if (!h.md5.empty()) j["md5"] = h.md5;
    if (!h.sha1.empty()) j["sha1"] = h.sha1;
    if (!h.crc32.empty()) j["crc32"] = h.crc32;
    if (!h.sha256.empty()) j["sha256"] = h.sha256;
}

void from_json(const nlohmann::json& j, FileHashes& h) {
    if (j.contains("md5")) j.at("md5").get_to(h.md5);
    if (j.contains("sha1")) j.at("sha1").get_to(h.sha1);
    if (j.contains("crc32")) j.at("crc32").get_to(h.crc32);
    if (j.contains("sha256")) j.at("sha256").get_to(h.sha256);
}

// ProviderStatus serialization
void to_json(nlohmann::json& j, const ProviderStatus& s) {
    j = nlohmann::json{
        {"name", s.name},
        {"available", s.available},
        {"last_check", std::chrono::duration_cast<std::chrono::seconds>(
                           s.last_check.time_since_epoch())
                           .count()}};
    if (!s.error.empty()) j["error"] = s.error;
}

void from_json(const nlohmann::json& j, ProviderStatus& s) {
    j.at("name").get_to(s.name);
    j.at("available").get_to(s.available);
    auto ts = j.at("last_check").get<int64_t>();
    s.last_check = std::chrono::system_clock::time_point(std::chrono::seconds(ts));
    if (j.contains("error")) j.at("error").get_to(s.error);
}

SearchOptions default_search_options() {
    return SearchOptions{.platform_id = std::nullopt, .limit = 10, .min_score = 0.75};
}

}  // namespace retro_metadata
