#include <retro_metadata/config.hpp>

#include <algorithm>

namespace retro_metadata {

ProviderConfig default_provider_config() {
    return ProviderConfig{.enabled = false, .priority = 100, .timeout = 30};
}

CacheConfig default_cache_config() {
    return CacheConfig{.backend = "memory", .ttl = 3600, .max_size = 10000};
}

Config default_config() {
    Config config;
    config.igdb = default_provider_config();
    config.mobygames = default_provider_config();
    config.screenscraper = default_provider_config();
    config.retroachievements = default_provider_config();
    config.steamgriddb = default_provider_config();
    config.hltb = default_provider_config();
    config.launchbox = default_provider_config();
    config.hasheous = default_provider_config();
    config.thegamesdb = default_provider_config();
    config.flashpoint = default_provider_config();
    config.playmatch = default_provider_config();
    config.gamelist = default_provider_config();
    config.cache = default_cache_config();
    config.default_timeout = 30;
    config.max_concurrent_requests = 10;
    config.user_agent = "retro-metadata/1.0";
    config.region_priority = {"us", "wor", "eu", "jp"};
    return config;
}

std::vector<std::string> Config::get_enabled_providers() const {
    struct ProviderPriority {
        std::string name;
        int priority;
    };

    std::vector<ProviderPriority> providers;

    auto add_if_enabled = [&providers](const std::string& name, const ProviderConfig& config) {
        if (config.enabled) {
            providers.push_back({name, config.priority});
        }
    };

    add_if_enabled("igdb", igdb);
    add_if_enabled("mobygames", mobygames);
    add_if_enabled("screenscraper", screenscraper);
    add_if_enabled("retroachievements", retroachievements);
    add_if_enabled("steamgriddb", steamgriddb);
    add_if_enabled("hltb", hltb);
    add_if_enabled("launchbox", launchbox);
    add_if_enabled("hasheous", hasheous);
    add_if_enabled("thegamesdb", thegamesdb);
    add_if_enabled("flashpoint", flashpoint);
    add_if_enabled("playmatch", playmatch);
    add_if_enabled("gamelist", gamelist);

    // Sort by priority (lower = higher priority)
    std::sort(providers.begin(), providers.end(),
              [](const ProviderPriority& a, const ProviderPriority& b) {
                  return a.priority < b.priority;
              });

    std::vector<std::string> result;
    result.reserve(providers.size());
    for (const auto& p : providers) {
        result.push_back(p.name);
    }
    return result;
}

ProviderConfig* Config::get_provider_config(const std::string& name) {
    if (name == "igdb") return &igdb;
    if (name == "mobygames") return &mobygames;
    if (name == "screenscraper") return &screenscraper;
    if (name == "retroachievements") return &retroachievements;
    if (name == "steamgriddb") return &steamgriddb;
    if (name == "hltb") return &hltb;
    if (name == "launchbox") return &launchbox;
    if (name == "hasheous") return &hasheous;
    if (name == "thegamesdb") return &thegamesdb;
    if (name == "flashpoint") return &flashpoint;
    if (name == "playmatch") return &playmatch;
    if (name == "gamelist") return &gamelist;
    return nullptr;
}

const ProviderConfig* Config::get_provider_config(const std::string& name) const {
    return const_cast<Config*>(this)->get_provider_config(name);
}

ConfigOption with_igdb(const std::string& client_id, const std::string& client_secret) {
    return [client_id, client_secret](Config& c) {
        c.igdb.enabled = true;
        c.igdb.credentials = {{"client_id", client_id}, {"client_secret", client_secret}};
        c.igdb.priority = 1;
    };
}

ConfigOption with_mobygames(const std::string& api_key) {
    return [api_key](Config& c) {
        c.mobygames.enabled = true;
        c.mobygames.credentials = {{"api_key", api_key}};
        c.mobygames.priority = 2;
    };
}

ConfigOption with_screenscraper(
    const std::string& dev_id,
    const std::string& dev_password,
    const std::string& ss_id,
    const std::string& ss_password) {
    return [=](Config& c) {
        c.screenscraper.enabled = true;
        c.screenscraper.credentials = {
            {"devid", dev_id},
            {"devpassword", dev_password},
            {"ssid", ss_id},
            {"sspassword", ss_password}};
        c.screenscraper.priority = 3;
    };
}

ConfigOption with_retroachievements(const std::string& username, const std::string& api_key) {
    return [username, api_key](Config& c) {
        c.retroachievements.enabled = true;
        c.retroachievements.credentials = {{"username", username}, {"api_key", api_key}};
        c.retroachievements.priority = 4;
    };
}

ConfigOption with_steamgriddb(const std::string& api_key) {
    return [api_key](Config& c) {
        c.steamgriddb.enabled = true;
        c.steamgriddb.credentials = {{"api_key", api_key}};
        c.steamgriddb.priority = 5;
    };
}

ConfigOption with_hltb() {
    return [](Config& c) {
        c.hltb.enabled = true;
        c.hltb.priority = 10;
    };
}

ConfigOption with_cache(const std::string& backend, int ttl, int max_size) {
    return [backend, ttl, max_size](Config& c) {
        c.cache.backend = backend;
        c.cache.ttl = ttl;
        c.cache.max_size = max_size;
    };
}

ConfigOption with_redis_cache(const std::string& connection_string, int ttl) {
    return [connection_string, ttl](Config& c) {
        c.cache.backend = "redis";
        c.cache.connection_string = connection_string;
        c.cache.ttl = ttl;
    };
}

ConfigOption with_sqlite_cache(const std::string& db_path, int ttl) {
    return [db_path, ttl](Config& c) {
        c.cache.backend = "sqlite";
        c.cache.connection_string = db_path;
        c.cache.ttl = ttl;
    };
}

ConfigOption with_user_agent(const std::string& user_agent) {
    return [user_agent](Config& c) { c.user_agent = user_agent; };
}

ConfigOption with_timeout(int seconds) {
    return [seconds](Config& c) { c.default_timeout = seconds; };
}

ConfigOption with_max_concurrent_requests(int max_requests) {
    return [max_requests](Config& c) { c.max_concurrent_requests = max_requests; };
}

ConfigOption with_preferred_locale(const std::string& locale) {
    return [locale](Config& c) { c.preferred_locale = locale; };
}

ConfigOption with_region_priority(const std::vector<std::string>& regions) {
    return [regions](Config& c) { c.region_priority = regions; };
}

}  // namespace retro_metadata
